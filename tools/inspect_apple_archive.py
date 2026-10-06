#!/usr/bin/env python3
"""Opt-in bounded acquisition and read-only inspection of Apple's legacy distribution."""
import argparse
import os
# Fail before importing TLS modules; host interpreter/OpenSSL remain trusted prerequisites.
if any(name in os.environ for name in ('OPENSSL_CONF','OPENSSL_MODULES','SSLKEYLOGFILE')):
    raise ValueError('Unsupported TLS environment override')
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import platform
import re
import ssl
import subprocess
import sys
import tarfile
import unicodedata
import urllib.parse
import urllib.request
from audit_support import ROOT, sha, isolated_env, verify_python
from baseline import verify_original

URL = 'https://download.info.apple.com/Mac_OS_X/061-2942.20070123.xRaTg/RAIDAdmin1.5.1.tar.gz'
DOWNLOAD_LIMIT = 16 * 1024 * 1024
TAR_LIMIT = 64 * 1024 * 1024
MEMBER_LIMIT = 16 * 1024 * 1024


def approved_url(url):
    value = urllib.parse.urlsplit(url)
    host = value.hostname or ''
    if (value.scheme != 'https' or value.port not in (None,443) or value.username or value.password or
            not (host == 'apple.com' or host.endswith('.apple.com'))):
        raise ValueError('Download origin rejected')


class AppleRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        approved_url(newurl)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def inspect(data, cache):
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
        decompressed = compressed.read(TAR_LIMIT+1)
    if len(decompressed) > TAR_LIMIT: raise ValueError('Decompressed archive exceeds bound')
    entries, selected, seen = [], {}, set()
    with tarfile.open(fileobj=io.BytesIO(decompressed),mode='r:') as archive:
        for index, member in enumerate(archive):
            if index >= 4096: raise ValueError('Archive member count exceeds bound')
            path = PurePosixPath(member.name)
            key = unicodedata.normalize('NFC',str(path)).casefold()
            if (path.is_absolute() or '..' in path.parts or '\\' in member.name or '\x00' in member.name or
                    len(member.name) > 1024 or key in seen or member.pax_headers or member.issparse() or
                    not (member.isfile() or member.isdir()) or not 0 <= member.size <= MEMBER_LIMIT):
                raise ValueError('Unsafe archive member')
            seen.add(key)
            record = {'name':member.name,'size':member.size,'type':'file' if member.isfile() else 'directory'}
            if member.isfile():
                stream = archive.extractfile(member)
                if stream is None: raise ValueError('Missing member stream')
                with stream: payload = stream.read(MEMBER_LIMIT+1)
                if len(payload) != member.size or len(payload) > MEMBER_LIMIT: raise ValueError('Member exceeds bound')
                record['sha256'] = hashlib.sha256(payload).hexdigest()
                if path.suffix.lower() in ('.jar','.xfb'):
                    # Flat hash-derived names; never write an archive-supplied filesystem path.
                    name = record['sha256'] + path.suffix.lower()
                    target = cache/name
                    if target.exists() or target.is_symlink():
                        if target.is_symlink() or not target.is_file() or sha(target) != record['sha256']:
                            raise ValueError('Cached member collision')
                    else:
                        with target.open('xb') as output: output.write(payload)
                        target.chmod(0o444)
                    selected[member.name] = {'cache_file':name,'sha256':record['sha256'],'size':len(payload)}
            entries.append(record)
    return entries,selected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch',action='store_true',help='Explicitly download the public Apple archive')
    parser.add_argument('--output',required=True,type=Path,help='New directory under ignored build/')
    args=parser.parse_args(); verify_python()
    dependencies={}
    for name in ('audit_support','baseline','class_patch'):
        loaded=Path(sys.modules[name].__file__).resolve()
        if loaded != ROOT/'tools'/ (name+'.py'): raise ValueError('Unexpected imported module location')
        dependencies[str(loaded.relative_to(ROOT))]=sha(loaded)
    tool_hash=sha(Path(__file__))
    def source_state():
        return (subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),
                bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
    commit,dirty=source_state()
    if not args.fetch: raise ValueError('Network acquisition requires --fetch')
    output=args.output.absolute()
    build=(ROOT/'build').resolve()
    if output.is_symlink() or output.exists() or not output.resolve().is_relative_to(build):
        raise ValueError('Choose a new ignored build directory')
    subprocess.run(['/usr/bin/git','check-ignore','--quiet',str(output/'archive.tar.gz')],cwd=ROOT,env=isolated_env(),check=True)
    approved_url(URL)
    # Use the compiled OpenSSL CA bundle explicitly: no SSL_CERT_* or key-log environment hooks.
    ca_path=Path(ssl.get_default_verify_paths().openssl_cafile)
    with ca_path.open('rb') as stream: ca_data=stream.read(4*1024*1024+1)
    if len(ca_data) > 4*1024*1024: raise ValueError('CA bundle exceeds bound')
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    certificates=re.findall(rb'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----',ca_data)
    if not certificates: raise ValueError('CA bundle has no supported certificate blocks')
    context.load_verify_locations(cadata=b'\n'.join(certificates).decode('ascii'))
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),AppleRedirect(),urllib.request.HTTPSHandler(context=context))
    output.mkdir(parents=True)
    with opener.open(urllib.request.Request(URL),timeout=30) as response:
        approved_url(response.url)
        data=response.read(DOWNLOAD_LIMIT+1)
        retrieved_utc=datetime.now(timezone.utc).isoformat()
        if len(data) > DOWNLOAD_LIMIT: raise ValueError('Download exceeds bound')
        length=response.headers.get('Content-Length')
        if length is not None and (not length.isdecimal() or int(length) != len(data)):
            raise ValueError('Download length differs from server declaration')
        response_metadata={k:response.headers[k] for k in ('Content-Length','ETag','Last-Modified') if k in response.headers}
        final_url=response.url
    archive=output/'archive.tar.gz'; partial=output/'archive.part'
    with partial.open('xb') as stream: stream.write(data)
    partial.rename(archive); archive.chmod(0o444)
    digest=hashlib.sha256(data).hexdigest()
    if sha(archive) != digest: raise ValueError('Cached archive changed')
    entries,selected=inspect(data,output)
    original=ROOT/'original/RAID_Admin_original.jar'; verify_original(original)
    if (source_state() != (commit,dirty) or sha(Path(__file__)) != tool_hash or
            any(sha(ROOT/name) != expected for name,expected in dependencies.items())):
        raise ValueError('Acquisition source changed during run')
    record={'url':URL,'final_url':final_url,'retrieved_utc':retrieved_utc,
        'inspection_completed_utc':datetime.now(timezone.utc).isoformat(),
        'response_headers':response_metadata,'archive_size':len(data),
        'archive_sha256':digest,'archive_sha1':hashlib.sha1(data).hexdigest(),'archive_md5':hashlib.md5(data).hexdigest(),
        'python':platform.python_version(),'tool_sha256':tool_hash,
        'source_commit':commit,'source_dirty':dirty,'dependency_hashes':dependencies,
        'tls':{'openssl':ssl.OPENSSL_VERSION,'ca_bundle_sha256':hashlib.sha256(ca_data).hexdigest(),
               'host_trust_prerequisite':True,'explicit_ca_and_no_proxy':True,'openssl_config_module_and_keylog_overrides':'rejected'},
        'reference_jar_sha256':sha(original),
        'matching_reference_entries':[name for name,row in selected.items() if row['sha256']==sha(original)],
        'entries':entries,'selected':selected,
        'limits':'Bytes served today over verified HTTPS by Apple; no independent historical digest or package-signature assertion. Read-only tar inspection, no mount/exec/install/application launch/firmware transmission. Any DMG/PKG remains an unparsed hashed member. Selected binaries stay in ignored local cache; not redistributed.'}
    (output/'acquisition.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'archive_sha256':digest,'entry_count':len(entries),'selected_count':len(selected),
                      'reference_matches':record['matching_reference_entries']}))


if __name__ == '__main__': main()
