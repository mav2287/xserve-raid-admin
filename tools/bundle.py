#!/usr/bin/env python3
"""Package an audited clean build with a pinned vendor runtime. No signing/install/launch."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess

from audit_support import ROOT, digest, modes, sha, tree, verify_python
from runtime import obtain_runtime, runtime_manifest, verify_runtime
from verify_builds import check_artifact, EXPECTED


def copy_verified(source, destination, files, permissions):
    for name, expected in sorted(files.items()):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe manifest path')
        src = source / relative
        if src.is_symlink() or not src.is_file():
            raise ValueError('Unexpected source entry')
        data = src.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Source bytes changed while packaging')
        dst = destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open('xb') as out:
            out.write(data)
        dst.chmod(permissions[name])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--architecture', required=True, choices=['aarch64','x64'])
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    verify_python()
    identity, provenance = check_artifact(args.build)
    if identity != json.loads(EXPECTED.read_text())['expected']:
        raise ValueError('Source build differs from reviewed expected output')
    if provenance['source_dirty']:
        raise ValueError('Packaging requires a build from a clean implementation commit')
    runtime = obtain_runtime(args.cache, args.architecture, fetch=args.fetch)
    lock = runtime_manifest(); record = lock['architectures'][args.architecture]
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    app = output / 'RAID Admin.app'
    copy_verified(args.build / 'RAID Admin.app', app, provenance['files'], provenance['file_modes'])
    runtime_destination = app / 'Contents/PlugIns/Runtime.jdk'
    copy_verified(runtime, runtime_destination, record['files'], record['file_modes'])
    verify_runtime(runtime_destination, record)
    launch = app / 'Contents/MacOS/RAIDAdmin'
    launch.write_bytes((ROOT / 'packaging/RAIDAdmin').read_bytes()); launch.chmod(0o755)
    icon = app / 'Contents/Resources/AppIcon.png'
    icon.write_bytes((ROOT / 'packaging/AppIcon.png').read_bytes()); icon.chmod(0o644)
    plist = app / 'Contents/Info.plist'
    metadata = plistlib.loads(plist.read_bytes())
    # Both pinned runtime java binaries have LC_BUILD_VERSION minos 11.0.
    # This is a binary floor, not qualification of every OS version above it.
    metadata['LSMinimumSystemVersion'] = '11.0'
    plist.write_bytes(plistlib.dumps(metadata, sort_keys=True))
    files, permissions = tree(app), modes(app)
    changed = {name for name, value in provenance['files'].items() if files.get(name) != value}
    if changed != {'Contents/MacOS/RAIDAdmin','Contents/Info.plist'}:
        raise ValueError('Unexpected source bundle change')
    additions = set(files) - set(provenance['files'])
    allowed = {'Contents/Resources/AppIcon.png'} | {'Contents/PlugIns/Runtime.jdk/' + n for n in record['files']}
    if additions != allowed:
        raise ValueError('Unexpected bundle additions')
    for name, permission in provenance['file_modes'].items():
        if permissions[name] != permission:
            raise ValueError('Source bundle file mode changed')
    inputs = [ROOT / p for p in ('tools/bundle.py','tools/runtime.py','tools/audit_support.py',
              'tools/verify_builds.py','tools/baseline.py','audit/runtime-lock.json','audit/expected-build.json',
              'packaging/RAIDAdmin','packaging/AppIcon.png')]
    manifest = {'schema':3,'purpose':'unsigned pinned-runtime compatibility candidate; not a qualified release',
                'apple_version':provenance['apple_version'],'compatibility_version':provenance['compatibility_version'],
                'source_commit':provenance['source_commit'],'source_dirty':False,
                'packager_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'packager_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)),
                'source_provenance_sha256':sha(args.build / 'provenance.json'),
                'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
                'original_jar_sha256':provenance['original_jar_sha256'],
                'bundled_runtime':{'vendor':lock['vendor'],'version':lock['version'],'architecture':args.architecture,
                    'archive_url':record['archive_url'],'archive_sha256':record['archive_sha256'],
                    'tree_sha256':record['tree_sha256'],'signature_team':record['signature_team'],
                    'signature_verification':'vendor signature verified after byte-only copy; never re-signed'},
                'application_signing':None,'application_notarization':'not performed',
                'files':files,'file_modes':permissions,'bundle_tree_sha256':digest({'files':files,'file_modes':permissions})}
    (output / 'provenance.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'architecture':args.architecture,'bundle_tree_sha256':manifest['bundle_tree_sha256'],
                      'jar_sha256':sha(app / 'Contents/Resources/RAID_Admin.jar')}))

if __name__ == '__main__': main()
