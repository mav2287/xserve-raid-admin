#!/usr/bin/env python3
"""Rebuild audit29, then remove information-view simulated press delays only."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import sys
from audit_support import ROOT, digest, isolated_env, modes, run_jdk, sha, tree, verify_jdk, verify_python
from array_responsiveness_patch import SPECS, HELPERS, plan, verify_delta
from baseline import write_jar
from bundle import copy_verified
from secure_build import entries, state
from array_info_build import check_array_info_artifact

VERSION = '1.5.1-modern.audit.30'
BASE_SHA = 'd616359dbea9fa8c9bd61f107b86e65b3563353f833a35430b314036d1a03fc6'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); verify_python(); verify_jdk(args.jdk)
    initial = state(); out = args.output.resolve()
    if initial['dirty'] or (ROOT / 'build').is_symlink() or out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('Clean source and fresh build output required')
    out.mkdir(); base = out / 'audit29-reference'
    result = subprocess.run([sys.executable, '-E', '-s', str(ROOT / 'tools/array_info_build.py'),
                             '--jdk', str(args.jdk), '--output', str(base)],
                            env=isolated_env(), capture_output=True, timeout=180)
    if result.returncode: raise ValueError('Audit29 reference rebuild failed; output withheld')
    identity, baseline, _ = check_array_info_artifact(base)
    if baseline['jar_sha256'] != BASE_SHA: raise ValueError('Rebuilt audit29 reference differs')
    helper_source = ROOT / 'modernization/array-responsiveness/compat/InfoSelectionClick.java'
    classes = out / 'classes'; classes.mkdir()
    jar = base / 'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(jar), '-d', str(classes), str(helper_source)])
    generated = {str(p.relative_to(classes)):p.read_bytes() for p in classes.rglob('*.class')}
    if set(generated) != HELPERS: raise ValueError('Unexpected information helper class inventory')
    before = entries(jar); after = dict(before); after.update({entry:plan(entry,before[entry]) for entry in SPECS}); after.update(generated)
    verify_delta(before, after, generated)
    app = out / 'RAID Admin.app'; copy_verified(base / 'RAID Admin.app', app, baseline['files'], baseline['file_modes'])
    write_jar(app / 'Contents/Resources/RAID_Admin.jar', after)
    plist = app / 'Contents/Info.plist'; data = plistlib.loads(plist.read_bytes())
    data.update(CFBundleShortVersionString=VERSION, CFBundleVersion='30'); plist.write_bytes(plistlib.dumps(data, sort_keys=True))
    record = dict(baseline)
    record.update(compatibility_version=VERSION, purpose='Information-view-only simulated press delay removal; native symptom confirmation pending',
                  jar_sha256=sha(app / 'Contents/Resources/RAID_Admin.jar'), files=tree(app), file_modes=modes(app))
    record['input_hashes'] = dict(baseline['input_hashes']); record['input_hashes'][str(helper_source.relative_to(ROOT))] = sha(helper_source)
    record['responsiveness_delta'] = {'base_jar_sha256':BASE_SHA, 'modified':sorted(SPECS), 'added':sorted(HELPERS),
                                     'helper_sha256':sha(classes / next(iter(HELPERS))), 'base_provenance_sha256':sha(base / 'provenance.json')}
    record['jar_delta'] = {'reference':'audit29', 'modified':sorted(SPECS), 'added':sorted(HELPERS)}
    record['helper_hashes'] = {**baseline['helper_hashes'], **{name:sha(classes/name) for name in HELPERS}}
    # The native helper is reused byte-for-byte from this fresh, pinned audit28 rebuild.
    for spec in record['native_helpers'].values(): spec['path'] = 'audit29-reference/' + spec['path']
    record['bundle_tree_sha256'] = digest({'files':record['files'], 'file_modes':record['file_modes']})
    if state() != initial: raise ValueError('Build source state changed')
    (out / 'provenance.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    check_responsiveness_artifact(out)
    print('PASS audit30 rebuild; exact audit29 inverse; two click listeners and one helper only')


def check_responsiveness_artifact(output):
    output = Path(output); record = json.loads((output / 'provenance.json').read_bytes())
    _, base, _ = check_array_info_artifact(output / 'audit29-reference')
    app = output / 'RAID Admin.app'; before_app = output / 'audit29-reference/RAID Admin.app'
    if (base['jar_sha256'] != BASE_SHA or sha(output / 'audit29-reference/provenance.json') != record['responsiveness_delta']['base_provenance_sha256']
            or record['compatibility_version'] != VERSION or record['source_dirty']):
        raise ValueError('Array-info reference/provenance differs')
    before = entries(before_app / 'Contents/Resources/RAID_Admin.jar'); after = entries(app / 'Contents/Resources/RAID_Admin.jar')
    helpers = {name:(output/'classes'/name).read_bytes() for name in HELPERS}; verify_delta(before, after, helpers)
    if sha(output / 'classes' / next(iter(HELPERS))) != record['responsiveness_delta']['helper_sha256']: raise ValueError('Helper hash differs')
    files, permissions = tree(app), modes(app)
    if (files != record['files'] or permissions != record['file_modes'] or permissions != base['file_modes']
            or set(files) != set(base['files'])
            or {n for n in files if files[n] != base['files'][n]} != {'Contents/Resources/RAID_Admin.jar', 'Contents/Info.plist'}
            or digest({'files':files, 'file_modes':permissions}) != record['bundle_tree_sha256']
            or sha(app / 'Contents/Resources/RAID_Admin.jar') != record['jar_sha256']):
        raise ValueError('Information artifact delta differs')
    expected = plistlib.loads((before_app / 'Contents/Info.plist').read_bytes())
    expected.update(CFBundleShortVersionString=VERSION, CFBundleVersion='30')
    if plistlib.loads((app / 'Contents/Info.plist').read_bytes()) != expected: raise ValueError('Unexpected bundle metadata change')
    for name, value in record['input_hashes'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or sha(ROOT / name) != value: raise ValueError('Build input differs')
        raw = subprocess.check_output(['/usr/bin/git', 'show', record['source_commit'] + ':' + name], cwd=ROOT, env=isolated_env())
        if hashlib.sha256(raw).hexdigest() != value: raise ValueError('Build source proof differs')
    for spec in record['native_helpers'].values():
        if sha(output / spec['path']) != spec['sha256']: raise ValueError('Native helper differs')
    identity = {'files':files, 'file_modes':permissions, 'input_hashes':record['input_hashes'],
                'original_jar_sha256':record['original_jar_sha256'], 'jdk':record['jdk'], 'builder':record['builder']}
    return identity, record, record['responsiveness_delta']


if __name__ == '__main__': main()
