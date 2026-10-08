#!/usr/bin/env python3
"""Rebuild audit28, then overlay only the information-view sentinel conversion."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import sys
from audit_support import ROOT, digest, isolated_env, modes, run_jdk, sha, tree, verify_jdk, verify_python
from array_info_patch import ENTRY, HELPER, plan, verify_delta
from baseline import write_jar
from bundle import copy_verified
from secure_build import check_secure_artifact, entries, state

VERSION = '1.5.1-modern.audit.29'
BASE_SHA = 'bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); verify_python(); verify_jdk(args.jdk)
    initial = state(); out = args.output.resolve()
    if initial['dirty'] or out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('Clean source and fresh build output required')
    out.mkdir(); base = out / 'audit28-reference'
    result = subprocess.run([sys.executable, '-E', '-s', str(ROOT / 'tools/secure_build.py'),
                             '--jdk', str(args.jdk), '--output', str(base), '--require-clean'],
                            env=isolated_env(), capture_output=True, timeout=180)
    if result.returncode: raise ValueError('Audit28 reference rebuild failed; output withheld')
    identity, baseline = check_secure_artifact(base)
    if baseline['jar_sha256'] != BASE_SHA: raise ValueError('Rebuilt audit28 reference differs')
    helper_source = ROOT / 'modernization/array-info/compat/ArrayInfoSelection.java'
    classes = out / 'classes'; classes.mkdir()
    jar = base / 'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(jar), '-d', str(classes), str(helper_source)])
    generated = {str(p.relative_to(classes)):p.read_bytes() for p in classes.rglob('*.class')}
    if set(generated) != {HELPER}: raise ValueError('Unexpected information helper class inventory')
    before = entries(jar); after = dict(before); after[ENTRY] = plan(before[ENTRY]); after.update(generated)
    verify_delta(before, after, generated[HELPER])
    app = out / 'RAID Admin.app'; copy_verified(base / 'RAID Admin.app', app, baseline['files'], baseline['file_modes'])
    write_jar(app / 'Contents/Resources/RAID_Admin.jar', after)
    plist = app / 'Contents/Info.plist'; data = plistlib.loads(plist.read_bytes())
    data.update(CFBundleShortVersionString=VERSION, CFBundleVersion='29'); plist.write_bytes(plistlib.dumps(data, sort_keys=True))
    record = dict(baseline)
    record.update(compatibility_version=VERSION, purpose='Information-view-only trial fix; native symptom not yet confirmed',
                  jar_sha256=sha(app / 'Contents/Resources/RAID_Admin.jar'), files=tree(app), file_modes=modes(app))
    record['input_hashes'] = dict(baseline['input_hashes']); record['input_hashes'][str(helper_source.relative_to(ROOT))] = sha(helper_source)
    record['array_info_delta'] = {'base_jar_sha256':BASE_SHA, 'modified':[ENTRY], 'added':[HELPER],
                                'helper_sha256':sha(classes / HELPER), 'base_provenance_sha256':sha(base / 'provenance.json')}
    # The native helper is reused byte-for-byte from this fresh, pinned audit28 rebuild.
    for spec in record['native_helpers'].values(): spec['path'] = 'audit28-reference/' + spec['path']
    record['bundle_tree_sha256'] = digest({'files':record['files'], 'file_modes':record['file_modes']})
    if state() != initial: raise ValueError('Build source state changed')
    (out / 'provenance.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    check_array_info_artifact(out)
    print('PASS audit29 rebuild; exact audit28 inverse; one information listener and one helper only')


def check_array_info_artifact(output):
    output = Path(output); record = json.loads((output / 'provenance.json').read_bytes())
    _, base = check_secure_artifact(output / 'audit28-reference')
    app = output / 'RAID Admin.app'; before_app = output / 'audit28-reference/RAID Admin.app'
    if (base['jar_sha256'] != BASE_SHA or sha(output / 'audit28-reference/provenance.json') != record['array_info_delta']['base_provenance_sha256']
            or record['compatibility_version'] != VERSION or record['source_dirty']):
        raise ValueError('Array-info reference/provenance differs')
    before = entries(before_app / 'Contents/Resources/RAID_Admin.jar'); after = entries(app / 'Contents/Resources/RAID_Admin.jar')
    helper = (output / 'classes' / HELPER).read_bytes(); verify_delta(before, after, helper)
    if sha(output / 'classes' / HELPER) != record['array_info_delta']['helper_sha256']: raise ValueError('Helper hash differs')
    files, permissions = tree(app), modes(app)
    if (files != record['files'] or permissions != record['file_modes'] or permissions != base['file_modes']
            or set(files) != set(base['files'])
            or {n for n in files if files[n] != base['files'][n]} != {'Contents/Resources/RAID_Admin.jar', 'Contents/Info.plist'}
            or digest({'files':files, 'file_modes':permissions}) != record['bundle_tree_sha256']
            or sha(app / 'Contents/Resources/RAID_Admin.jar') != record['jar_sha256']):
        raise ValueError('Information artifact delta differs')
    expected = plistlib.loads((before_app / 'Contents/Info.plist').read_bytes())
    expected.update(CFBundleShortVersionString=VERSION, CFBundleVersion='29')
    if plistlib.loads((app / 'Contents/Info.plist').read_bytes()) != expected: raise ValueError('Unexpected bundle metadata change')
    for name, value in record['input_hashes'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or sha(ROOT / name) != value: raise ValueError('Build input differs')
        raw = subprocess.check_output(['/usr/bin/git', 'show', record['source_commit'] + ':' + name], cwd=ROOT, env=isolated_env())
        if hashlib.sha256(raw).hexdigest() != value: raise ValueError('Build source proof differs')
    for spec in record['native_helpers'].values():
        if sha(output / spec['path']) != spec['sha256']: raise ValueError('Native helper differs')
    identity = {'files':files, 'file_modes':permissions, 'input_hashes':record['input_hashes'],
                'original_jar_sha256':record['original_jar_sha256'], 'jdk':record['jdk'], 'builder':record['builder']}
    return identity, record, record['array_info_delta']


if __name__ == '__main__': main()
