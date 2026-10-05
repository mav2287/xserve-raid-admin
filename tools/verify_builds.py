#!/usr/bin/env python3
"""Verify deterministic artifacts against original bytes and reviewed expected output."""
import argparse
import json
from pathlib import Path
import zipfile
from baseline import ROOT, PATCH_CLASSES, verify_original
from audit_support import tree, modes, digest, sha, verify_python

EXPECTED = ROOT / 'audit/expected-build.json'


def entries(jar):
    with zipfile.ZipFile(jar) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries')
        return {n: archive.read(n) for n in names if not n.endswith('/')}


def check_artifact(output):
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    app = output / 'RAID Admin.app'
    files, file_modes = tree(app), modes(app)
    manifest = json.loads((output / 'provenance.json').read_text())
    identity = {'files': files, 'file_modes': file_modes}
    if files != manifest['files'] or file_modes != manifest['file_modes'] or digest(identity) != manifest['bundle_tree_sha256']:
        raise ValueError('Build manifest does not match artifact contents or modes')
    if file_modes.get('Contents/MacOS/RAIDAdmin') != 0o755:
        raise ValueError('Launcher executable mode mismatch')
    reference = entries(original)
    actual = entries(app / 'Contents/Resources/RAID_Admin.jar')
    changed = {n for n in reference.keys() | actual.keys() if reference.get(n) != actual.get(n)}
    if changed != PATCH_CLASSES | {'META-INF/MANIFEST.MF'}:
        raise ValueError('Unexpected JAR change outside exact allowlist')
    for name, expected in manifest['input_hashes'].items():
        if name.startswith('/') or '..' in Path(name).parts or sha(ROOT / name) != expected:
            raise ValueError('Current input differs from recorded build input')
    identity.update(input_hashes=manifest['input_hashes'], original_jar_sha256=manifest['original_jar_sha256'],
                    jdk=manifest['jdk'], builder=manifest['builder'])
    return identity, manifest


def verify(a, b, *, expected_path=EXPECTED, update_reason=None):
    first, manifest = check_artifact(a)
    second, _ = check_artifact(b)
    if first != second:
        raise ValueError('Builds or inputs differ')
    if update_reason is not None:
        if not update_reason.strip():
            raise ValueError('Expected-build update requires a reason')
        previous = sha(expected_path) if expected_path.exists() else None
        record = {'schema': 1, 'expected': first, 'source_commit': manifest['source_commit'],
                  'source_dirty': manifest['source_dirty'], 'previous_record_sha256': previous, 'reason': update_reason}
        expected_path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    else:
        if not expected_path.exists():
            raise ValueError('No reviewed expected-build record')
        if first != json.loads(expected_path.read_text())['expected']:
            raise ValueError('Build differs from reviewed expected inputs or outputs')
    print('PASS: manifests, modes, immutable entries, two builds and expected output verified')


if __name__ == '__main__':
    verify_python()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build1', type=Path)
    p.add_argument('build2', type=Path)
    p.add_argument('--update-expected', action='store_true')
    p.add_argument('--reason')
    args = p.parse_args()
    if args.update_expected and not args.reason:
        p.error('--update-expected requires --reason')
    if args.reason and not args.update_expected:
        p.error('--reason requires --update-expected')
    verify(args.build1, args.build2, update_reason=args.reason if args.update_expected else None)
