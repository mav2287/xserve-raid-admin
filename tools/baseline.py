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

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SHA256 = '5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
PATCH_CLASSES = {
    'Launcher.class', 'com/apple/eio/FileManager.class',
    'com/apple/mrj/MRJApplicationUtils.class',
    'com/apple/mrj/MRJApplicationUtils$1.class',
    'com/apple/mrj/MRJApplicationUtils$2.class', 'sun/io/MalformedInputException.class',
}
VERSION = '1.5.1-modern.audit.1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(Path(path).rglob('*')) if p.is_file()}


def tree_hash(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


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
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    jdk = args.jdk.resolve()
    lock = json.loads((ROOT / 'audit/jdk-lock.json').read_text())
    if tree(jdk) != lock['files']:
        raise ValueError('JDK differs from audit/jdk-lock.json; explicit toolchain review required')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Output exists; choose a new directory')
    with tempfile.TemporaryDirectory(prefix='raid-baseline-') as tmp:
        classes = Path(tmp) / 'classes'
        classes.mkdir()
        sources = sorted((ROOT / 'patches').rglob('*.java'))
        subprocess.run([str(jdk / 'bin/javac'), '-source', '8', '-target', '8', '-encoding', 'UTF-8',
                        '-cp', str(original), '-d', str(classes)] + [str(p) for p in sources], check=True)
        patches = {str(p.relative_to(classes)): p.read_bytes() for p in classes.rglob('*.class')}
        if set(patches) != PATCH_CLASSES:
            raise ValueError('Compiled patch class allowlist mismatch')
        with zipfile.ZipFile(original) as z:
            names = z.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Duplicate original JAR entries')
            entries = {n: z.read(n) for n in names if not n.endswith('/')}
        before = {n: hashlib.sha256(v).hexdigest() for n, v in entries.items()}
        entries.update(patches)
        entries['META-INF/MANIFEST.MF'] = b'Manifest-Version: 1.0\r\nMain-Class: Launcher\r\n\r\n'
        output.mkdir(parents=True)
        app = output / 'RAID Admin.app'
        resources = app / 'Contents/Resources'
        resources.mkdir(parents=True)
        (app / 'Contents/MacOS').mkdir()
        write_jar(resources / 'RAID_Admin.jar', entries)
        # Reuse reviewed upstream bundle templates; no execution of build.sh.
        script = (ROOT / 'build.sh').read_text()
        plist = re.search(r"<< 'PLIST'\n(.*?)\nPLIST", script, re.S).group(1)
        metadata = plistlib.loads(plist.encode())
        metadata.update(CFBundleIdentifier='org.xserve-raid-admin.audit',
                        CFBundleShortVersionString=VERSION, CFBundleVersion='3')
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(metadata, sort_keys=True))
        launcher = re.search(r"<< 'LAUNCHER'\n(.*?)\nLAUNCHER", script, re.S).group(1) + '\n'
        launchpath = app / 'Contents/MacOS/RAIDAdmin'
        launchpath.write_text(launcher)
        launchpath.chmod(0o755)
        for src, dst in [('RAIDAdmin.icns', 'AppIcon.icns'), ('RAIDAdminFirmware.icns', 'RAIDAdminFirmware.icns')]:
            (resources / dst).write_bytes((ROOT / 'original' / src).read_bytes())
        files = tree(app)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        inputs = {str(p.relative_to(ROOT)): sha(p) for p in [ROOT / 'build.sh', Path(__file__).resolve(), ROOT / 'audit/jdk-lock.json'] + sources}
        provenance = {
            'schema': 1, 'purpose': 'unsigned offline audit build; not a qualified release',
            'apple_version': '1.5.1', 'compatibility_version': VERSION,
            'source_commit': commit,
            'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
            'build_timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'builder': {'python': platform.python_version(), 'macos': platform.mac_ver()[0], 'architecture': platform.machine()},
            'input_hashes': inputs, 'original_jar_sha256': ORIGINAL_SHA256,
            'jdk': {k: v for k, v in lock.items() if k != 'files'},
            'bundled_jre': None, 'native_helpers': [], 'signing_identity': None, 'notarization': 'not performed',
            'files': files, 'bundle_tree_sha256': tree_hash(files),
            'hash_definition': 'SHA256 of canonical JSON relative-file-path to SHA256; excludes timestamps, modes and xattrs',
            'entry_changes': sorted(n for n, v in entries.items() if before.get(n) != hashlib.sha256(v).hexdigest()),
        }
        (output / 'provenance.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'bundle_tree_sha256': provenance['bundle_tree_sha256'], 'jar_sha256': sha(resources / 'RAID_Admin.jar')}))


if __name__ == '__main__':
    main()
