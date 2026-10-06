#!/usr/bin/env python3
"""Offline, deterministic audit build. Does not sign, install, or launch the app."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from audit_support import sha, tree, modes, digest, verify_jdk, verify_python, run_jdk, isolated_env

from class_patch import TARGETS, transform, embedded_dtd

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SHA256 = '5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
PATCH_CLASSES = {
    'Launcher.class', 'com/apple/eio/FileManager.class',
    'com/apple/mrj/MRJApplicationUtils.class',
    'com/apple/mrj/MRJApplicationUtils$Adapter.class',
    'com/apple/mrj/MRJApplicationUtils$RuntimeApi.class', 'sun/io/MalformedInputException.class',
    'com/apple/mrj/MRJFileUtils.class', 'compat/SafePlistResolver.class',
}
ALLOWED_JAR_CHANGES = PATCH_CLASSES | set(TARGETS) | {'compat/PropertyList.dtd'}
VERSION = '1.5.1-modern.audit.4'


def tree_hash(files):
    return digest(files)


def verify_original(path):
    if sha(path) != ORIGINAL_SHA256:
        raise ValueError('Original JAR hash mismatch; refusing transformation')


def write_jar(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as z:
        for name, data in sorted(entries.items()):
            if name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Unsafe JAR entry')
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='New directory; must not exist')
    args = parser.parse_args()
    verify_python()
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    jdk = args.jdk.absolute()
    lock = verify_jdk(jdk)
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output exists; choose a new directory')
    with tempfile.TemporaryDirectory(prefix='raid-baseline-') as tmp:
        classes = Path(tmp) / 'classes'
        classes.mkdir()
        sources = sorted((ROOT / 'patches').rglob('*.java'))
        run_jdk(jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(original),
                             '-d', str(classes)] + [str(p) for p in sources])
        patches = {str(p.relative_to(classes)): p.read_bytes() for p in classes.rglob('*.class')}
        if set(patches) != PATCH_CLASSES:
            raise ValueError('Compiled patch class allowlist mismatch')
        with zipfile.ZipFile(original) as z:
            names = z.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Duplicate original JAR entries')
            entries = {n: z.read(n) for n in names if not n.endswith('/')}
        before = {n: hashlib.sha256(v).hexdigest() for n, v in entries.items()}
        security_lock = json.loads((ROOT / 'audit/security-patches.json').read_text())
        entries['compat/PropertyList.dtd'] = embedded_dtd(entries['com/apple/util/plist/PropertyListUtilities$Handler.class'])
        if hashlib.sha256(entries['compat/PropertyList.dtd']).hexdigest() != security_lock['compat/PropertyList.dtd']['sha256']:
            raise ValueError('Embedded original DTD changed')
        for name in TARGETS:
            if TARGETS[name][0] != security_lock[name]['original_sha256']:
                raise ValueError('Original class pins disagree')
            entries[name] = transform(name, entries[name])
            if hashlib.sha256(entries[name]).hexdigest() != security_lock[name]['patched_sha256']:
                raise ValueError('Transformed method differs from reviewed golden bytes')
        entries.update(patches)
        entries['META-INF/MANIFEST.MF'] = b'Manifest-Version: 1.0\r\nMain-Class: Launcher\r\n\r\n'
        changes = {n for n, v in entries.items() if before.get(n) != hashlib.sha256(v).hexdigest()}
        if changes != ALLOWED_JAR_CHANGES | {'META-INF/MANIFEST.MF'} or set(before) - set(entries):
            raise ValueError('Build changed entries outside reviewed allowlist')
        output.mkdir(parents=True)
        app = output / 'RAID Admin.app'
        resources = app / 'Contents/Resources'
        resources.mkdir(parents=True)
        (app / 'Contents/MacOS').mkdir()
        write_jar(resources / 'RAID_Admin.jar', entries)
        # Reviewed historical audit templates are separate from the bundled-runtime launcher.
        plist = (ROOT / 'packaging/audit-Info.plist').read_text()
        metadata = plistlib.loads(plist.encode())
        metadata.update(CFBundleIdentifier='org.xserve-raid-admin.audit',
                        CFBundleShortVersionString=VERSION, CFBundleVersion='4')
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(metadata, sort_keys=True))
        launcher = (ROOT / 'packaging/audit-launcher').read_text()
        launchpath = app / 'Contents/MacOS/RAIDAdmin'
        launchpath.write_text(launcher)
        launchpath.chmod(0o755)
        for src, dst in [('RAIDAdmin.icns', 'AppIcon.icns'), ('RAIDAdminFirmware.icns', 'RAIDAdminFirmware.icns')]:
            (resources / dst).write_bytes((ROOT / 'original' / src).read_bytes())
        for file in app.rglob('*'):
            if file.is_file():
                file.chmod(0o755 if file == launchpath else 0o644)
        files = tree(app)
        file_modes = modes(app)
        commit = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=ROOT, env=isolated_env(), text=True).strip()
        inputs = {str(p.relative_to(ROOT)): sha(p) for p in [ROOT / 'build.sh', Path(__file__).resolve(), ROOT / 'audit/jdk-lock.json', ROOT / 'audit/python-lock.json', ROOT / 'tools/audit_support.py', ROOT / 'tools/class_patch.py', ROOT / 'audit/security-patches.json', ROOT / 'packaging/audit-Info.plist', ROOT / 'packaging/audit-launcher'] + sources + sorted((ROOT / 'original').glob('*.icns'))}
        provenance = {
            'schema': 2, 'purpose': 'unsigned offline audit build; not a qualified release',
            'apple_version': '1.5.1', 'compatibility_version': VERSION,
            'source_commit': commit,
            'source_dirty': bool(subprocess.check_output(['/usr/bin/git', 'status', '--porcelain'], cwd=ROOT, env=isolated_env())),
            'build_timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'builder': {'python': platform.python_version(), 'macos': platform.mac_ver()[0], 'architecture': platform.machine()},
            'input_hashes': inputs, 'original_jar_sha256': ORIGINAL_SHA256,
            'jdk': {k: v for k, v in lock.items() if k != 'files'},
            'bundled_jre': None, 'native_helpers': [], 'signing_identity': None, 'notarization': 'not performed',
            'files': files, 'file_modes': file_modes,
            'content_tree_sha256': tree_hash(files),
            'bundle_tree_sha256': digest({'files': files, 'file_modes': file_modes}),
            'hash_definition': 'SHA256 of canonical JSON {files: relative-path to SHA256, file_modes: relative-path to integer mode}; excludes timestamps and xattrs',
            'entry_changes': sorted(n for n, v in entries.items() if before.get(n) != hashlib.sha256(v).hexdigest()),
        }
        (output / 'provenance.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'bundle_tree_sha256': provenance['bundle_tree_sha256'], 'jar_sha256': sha(resources / 'RAID_Admin.jar')}))


if __name__ == '__main__':
    main()
