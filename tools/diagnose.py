#!/usr/bin/env python3
"""Allowlisted local diagnostics. Never launches Java or reads app preferences."""
import argparse
import json
import os
import platform
import plistlib
import re
import socket
import stat
from pathlib import Path
from baseline import tree, ROOT, VERSION, BUNDLE_VERSION
from audit_support import modes, digest, sha
from runtime import directory_modes, runtime_manifest


AUDIT_VERSIONS=frozenset('1.5.1-modern.audit.'+str(number) for number in range(1,int(BUNDLE_VERSION)+1))


def safe_compatibility_version(value):
    return value if isinstance(value,str) and value in AUDIT_VERSIONS else 'unrecognized'


def safe_event(event):
    """Emit enumerated metadata only; discard arbitrary messages, headers and bodies."""
    allowed = {
        'operation': {'build', 'diagnose', 'fixture'},
        'result': {'pass', 'fail', 'not-run'},
        'error_code': {'INPUT_HASH', 'TOOLCHAIN_HASH', 'ARTIFACT_CHANGED', 'NONE'},
    }
    return {key: value for key, value in event.items()
            if key in allowed and isinstance(value, str) and value in allowed[key]}


def diagnose_checked(output):
    fd = os.open(output / 'provenance.json', os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise ValueError('Manifest is not regular')
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024: raise ValueError('Manifest exceeds bound')
    provenance = json.loads(raw)
    schema = provenance.get('schema')
    if type(schema) is not int or schema not in (2, 3): raise ValueError('Unknown schema')
    app = output / 'RAID Admin.app'
    files = tree(app)  # Reject links before directory traversal.
    file_modes = modes(app)
    expected_jdk = json.loads((Path(__file__).resolve().parents[1] / 'audit/jdk-lock.json').read_text())
    jdk_matches = provenance.get('jdk', {}) == {k: v for k, v in expected_jdk.items() if k != 'files'}
    measured = {'files':files, 'file_modes':file_modes}
    if schema == 3: measured['directory_modes'] = directory_modes(app)
    matches = all(value == provenance.get(key) for key,value in measured.items()) and digest(measured) == provenance.get('bundle_tree_sha256')
    expected = json.loads((ROOT / 'audit/expected-build.json').read_text())['expected']
    reviewed = files == expected['files'] and file_modes == expected['file_modes']
    bundled = 'absent'
    if schema == 3:
        bundled = 'unrecognized'
        lock = runtime_manifest()
        prefix = 'Contents/PlugIns/Runtime.jdk/'
        runtime_files = {k[len(prefix):]:v for k,v in files.items() if k.startswith(prefix)}
        runtime_modes = {k[len(prefix):]:v for k,v in file_modes.items() if k.startswith(prefix)}
        runtime_dirs = {('.' if k == prefix[:-1] else k[len(prefix):]):v for k,v in measured['directory_modes'].items() if k == prefix[:-1] or k.startswith(prefix)}
        reviewed = False
        for arch in ('aarch64', 'x64'):
            record = lock['architectures'][arch]
            if (runtime_files != record['files'] or runtime_modes != record['file_modes'] or
                    runtime_dirs != record['directory_modes'] or
                    digest({'files':runtime_files,'file_modes':runtime_modes}) != record['tree_sha256']):
                continue
            bundled = {k:lock[k] for k in ('vendor','version')}
            bundled.update(architecture=arch, tree_sha256=record['tree_sha256'])
            wanted_files = dict(expected['files']); wanted_modes = dict(expected['file_modes'])
            metadata = plistlib.loads((ROOT/'packaging/audit-Info.plist').read_bytes())
            metadata.update(CFBundleIdentifier='org.xserve-raid-admin.audit', CFBundleShortVersionString=VERSION, CFBundleVersion=BUNDLE_VERSION)
            import hashlib
            if hashlib.sha256(plistlib.dumps(metadata,sort_keys=True)).hexdigest() != wanted_files['Contents/Info.plist']:
                raise ValueError('Reviewed plist template differs')
            metadata['LSMinimumSystemVersion'] = '11.0'
            wanted_files['Contents/Info.plist'] = hashlib.sha256(plistlib.dumps(metadata,sort_keys=True)).hexdigest()
            wanted_files['Contents/MacOS/RAIDAdmin'] = sha(ROOT/'packaging/RAIDAdmin')
            wanted_files['Contents/Resources/AppIcon.png'] = sha(ROOT/'packaging/AppIcon.png')
            wanted_modes['Contents/Resources/AppIcon.png'] = 0o644
            wanted_files.update({prefix+k:v for k,v in record['files'].items()})
            wanted_modes.update({prefix+k:v for k,v in record['file_modes'].items()})
            wanted_dirs = {str(p):0o755 for name in wanted_files for p in Path(name).parents}
            wanted_dirs.update({prefix[:-1] if k == '.' else prefix+k:v for k,v in record['directory_modes'].items()})
            reviewed = files == wanted_files and file_modes == wanted_modes and measured['directory_modes'] == wanted_dirs
            break
    commit = provenance.get('source_commit')
    # Do not relay arbitrary strings from manifests, environment, or preference stores.
    return {
        'apple_version': '1.5.1', 'compatibility_version': safe_compatibility_version(provenance.get('compatibility_version')),
        'compatibility_version_matches_reviewed_artifact': reviewed and provenance.get('compatibility_version')==VERSION,
        'source_commit': commit if isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit) else 'unknown',
        'architecture': platform.machine() if platform.machine() in ('arm64','x86_64') else 'unrecognized',
        'macos': platform.mac_ver()[0] if re.fullmatch(r'[0-9]+(?:\.[0-9]+)*',platform.mac_ver()[0]) else 'unrecognized',
        'bundle_tree_sha256': digest(measured), 'matches_build_manifest': matches,
        'matches_reviewed_artifact': reviewed,
        'bundled_jre': bundled, 'runtime_selected': 'not evaluated; application not launched',
        'runtime_signature': 'not-evaluated',
        'build_jdk': {k: expected_jdk[k] for k in ('vendor', 'version', 'architecture', 'tree_sha256')} if jdk_matches else ('not recorded in bundled manifest' if schema == 3 else 'unrecognized build JDK'),
        'interfaces': [name for _, name in socket.if_nameindex() if re.fullmatch('[a-z]+[0-9]*',name)],
        'controller_discovery': 'not run; no controller traffic generated', 'discovered_controllers': [],
        'event': safe_event({'operation': 'diagnose', 'result': 'pass' if matches and reviewed and (jdk_matches or schema == 3) else 'fail'}),
    }


def diagnose(output):
    try:
        return diagnose_checked(output)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return {'matches_build_manifest':False, 'matches_reviewed_artifact':False,
                'compatibility_version_matches_reviewed_artifact':False,
                'event':safe_event({'operation':'diagnose','result':'fail','error_code':'ARTIFACT_CHANGED'})}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    print(json.dumps(diagnose(parser.parse_args().build_directory), indent=2))
