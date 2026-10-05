#!/usr/bin/env python3
"""Verify two audit builds and preservation of non-allowlisted original bytes."""
import argparse
import json
from pathlib import Path
import zipfile
from baseline import ROOT, PATCH_CLASSES, verify_original, tree, tree_hash


def entries(jar):
    with zipfile.ZipFile(jar) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries')
        return {n: archive.read(n) for n in names if not n.endswith('/')}


def verify(a, b):
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    reference = entries(original)
    maps = []
    for output in (a, b):
        app = output / 'RAID Admin.app'
        files = tree(app)
        manifest = json.loads((output / 'provenance.json').read_text())
        if files != manifest['files'] or tree_hash(files) != manifest['bundle_tree_sha256']:
            raise ValueError('Build manifest does not match artifact')
        actual = entries(app / 'Contents/Resources/RAID_Admin.jar')
        changed = {n for n in reference.keys() | actual.keys() if reference.get(n) != actual.get(n)}
        if changed != PATCH_CLASSES | {'META-INF/MANIFEST.MF'}:
            raise ValueError('Unexpected JAR change outside exact allowlist')
        maps.append(files)
    if maps[0] != maps[1]:
        raise ValueError('Builds differ')
    print('PASS: both manifests match, bundle content matches, original non-allowlisted bytes preserved')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build1', type=Path)
    p.add_argument('build2', type=Path)
    args = p.parse_args()
    verify(args.build1, args.build2)
