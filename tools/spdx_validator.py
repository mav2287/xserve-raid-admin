#!/usr/bin/env python3
"""Materialize hash-locked QA validator wheels; never modifies Python or the app."""
import argparse,hashlib,json,sys,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
from audit_support import ROOT,tree,digest,sha,verify_python

def verify(cache):
    lock=json.loads((ROOT/'audit/spdx-validator-lock.json').read_text())
    if tree(cache)!=lock['files'] or digest(lock['files'])!=lock['tree_sha256'] or sha(ROOT/'audit/spdx-2.3.1-schema.json')!=lock['schema_sha256']:raise ValueError('QA validator/schema differs')
    return lock

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',required=True,type=Path);p.add_argument('--fetch',action='store_true');a=p.parse_args();verify_python()
    if a.cache.exists():verify(a.cache)
    else:
        if not a.fetch:raise ValueError('Explicit --fetch required for missing QA validator')
        lock=json.loads((ROOT/'audit/spdx-validator-lock.json').read_text());a.cache.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='raid-spdx-validator-',dir=a.cache.parent) as t:
            tmp=Path(t);target=tmp/'modules';target.mkdir()
            for wheel in lock['wheels']:
                if not wheel['url'].startswith('https://files.pythonhosted.org/'):raise ValueError('Unexpected validator origin')
                with urllib.request.urlopen(wheel['url'],timeout=30) as response:
                    if not response.url.startswith('https://files.pythonhosted.org/'):raise ValueError('Unexpected validator redirect')
                    data=response.read()
                if hashlib.sha256(data).hexdigest()!=wheel['sha256']:raise ValueError('Validator wheel differs')
                archive=tmp/wheel['filename'];archive.write_bytes(data)
                with zipfile.ZipFile(archive) as z:
                    for item in z.infolist():
                        path=PurePosixPath(item.filename)
                        if path.is_absolute() or '..' in path.parts or '\\' in item.filename or (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe validator wheel path')
                        if item.is_dir():continue
                        dest=target/item.filename;dest.parent.mkdir(parents=True,exist_ok=True)
                        with dest.open('xb') as out:out.write(z.read(item))
                        dest.chmod(0o644)
            verify(target);target.rename(a.cache)
    print('PASS pinned QA-only SPDX validator/schema; no application dependency added')
if __name__=='__main__':main()
