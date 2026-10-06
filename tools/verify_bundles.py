#!/usr/bin/env python3
"""Verify two pinned-runtime bundles against source build and current packaging inputs."""
import argparse
import json
from pathlib import Path
import plistlib

from audit_support import ROOT, digest, tree, modes, sha
from runtime import directory_modes, runtime_manifest, verify_runtime
from verify_builds import check_artifact, EXPECTED


def check_bundle(output, source):
    identity, source_manifest = check_artifact(source)
    if identity != json.loads(EXPECTED.read_text())['expected']:
        raise ValueError('Source build differs from reviewed expected output')
    manifest = json.loads((output / 'provenance.json').read_text())
    app = output / 'RAID Admin.app'
    measured = {'files':tree(app),'file_modes':modes(app),'directory_modes':directory_modes(app)}
    if any(measured[k] != manifest[k] for k in measured) or digest(measured) != manifest['bundle_tree_sha256']:
        raise ValueError('Bundle differs from manifest')
    for name, expected in manifest['input_hashes'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or sha(ROOT / name) != expected:
            raise ValueError('Packaging inputs differ')
    arch = manifest['bundled_runtime']['architecture']
    runtime = runtime_manifest()['architectures'][arch]
    verify_runtime(app / 'Contents/PlugIns/Runtime.jdk', runtime)
    expected = dict(source_manifest['files'])
    expected['Contents/MacOS/RAIDAdmin'] = sha(ROOT / 'packaging/RAIDAdmin')
    expected['Contents/Resources/AppIcon.png'] = sha(ROOT / 'packaging/AppIcon.png')
    source_plist = source / 'RAID Admin.app/Contents/Info.plist'
    metadata = plistlib.loads(source_plist.read_bytes()); metadata['LSMinimumSystemVersion'] = '11.0'
    import hashlib
    expected['Contents/Info.plist'] = hashlib.sha256(plistlib.dumps(metadata,sort_keys=True)).hexdigest()
    expected.update({'Contents/PlugIns/Runtime.jdk/' + name:value for name,value in runtime['files'].items()})
    if measured['files'] != expected:
        raise ValueError('Unexpected source/runtime/packaging content')
    permissions = dict(source_manifest['file_modes']); permissions['Contents/Resources/AppIcon.png'] = 0o644
    permissions.update({'Contents/PlugIns/Runtime.jdk/' + name:value for name,value in runtime['file_modes'].items()})
    if measured['file_modes'] != permissions or any(m != 0o755 for m in measured['directory_modes'].values()):
        raise ValueError('Unexpected bundle permissions')
    return measured


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('first', type=Path); parser.add_argument('second', type=Path)
    args = parser.parse_args()
    first = check_bundle(args.first, args.source); second = check_bundle(args.second, args.source)
    if first != second: raise ValueError('Repeated bundles differ')
    print('PASS source preservation, packaging inputs, vendor signature, file/directory modes and repeated bundle digest ' + digest(first))
