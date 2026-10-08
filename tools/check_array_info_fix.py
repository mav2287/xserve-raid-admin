#!/usr/bin/env python3
"""Guarded actual listener tests and exact whole-JAR parity; never Main or controllers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from audit_support import ROOT, JAVA_FLAGS, isolated_env, verify_jdk, verify_python, run_jdk, sha
from array_info_build import check_array_info_artifact
from array_info_patch import ENTRY, HELPER, verify_delta
from inventory import disassemble_entries
from runtime import verify_runtime, runtime_manifest
from secure_build import entries, state

SOURCE_NAMES = ['uifixture/ArrayInfoFixObservation.java', 'fixture/OfflineGuard.java', 'fixture/FixtureIdentity.java']
IDENTITIES = ['com/apple/xsr/SystemInfoPane$5.class', 'com/apple/xsr/SystemInfoPane$ArrayDrivePanel.class',
              'com/apple/xsr/SystemInfoPane$ArrayDrivePanel$MessagePanel.class', 'com/apple/xsr/DriveSelectionPanel.class',
              'com/apple/xsr/Resources.class', 'com/apple/gui/GUIFactory.class', 'com/apple/xsr/SelectableLabel.class',
              'com/apple/xsr/SelectableStatusLabel.class', 'com/apple/xsr/ArraySelectionPanel.class',
              'com/apple/xsr/ArraySelectionPanel$ArrayLabel.class', 'com/apple/xsr/ArraySelectionPanel$2.class',
              'com/apple/xsr/ArraySelectionPanel$3.class', 'com/apple/xsr/ArraySelectionPanel$4.class']
COMPILED_TARGETS = ['com.apple.xsr.SystemInfoPane$5::propertyChange', 'compat.ArrayInfoSelection::setArrayIndex']


def validate_output(raw, expected, mode, fixed):
    if mode == '-Xint':
        if raw != expected: raise ValueError('Interpreted output differs')
        return []
    compiled = []; markers = []
    for line in raw.decode('ascii').splitlines():
        if line == expected.decode('ascii').strip():
            markers.append(line); continue
        if not re.match(r'^\s*\d+\s+\d+\s+.*::', line): raise ValueError('Unexpected compiler diagnostic')
        target = next((name for name in COMPILED_TARGETS if name + ' ' in line), None)
        if target and re.search(r'\(\d+ bytes\)\s*$', line): compiled.append(line)
        elif not target and '(native)' not in line: raise ValueError('Unexpected Java compilation outside target scope')
    required = COMPILED_TARGETS if fixed else COMPILED_TARGETS[:1]
    if len(markers) != 1 or any(not any(name + ' ' in line for line in compiled) for name in required):
        raise ValueError('Required compiled target or exact fixture marker missing')
    return compiled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); verify_python(); verify_jdk(args.jdk)
    initial = state(); out = args.output.resolve()
    if initial['dirty'] or out.exists() or not out.is_relative_to((ROOT / 'build').resolve()): raise ValueError('Clean source and fresh build output required')
    identity, product, delta = check_array_info_artifact(args.build)
    baseline = args.build.resolve() / 'audit28-reference/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    candidate = args.build.resolve() / 'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    before, after = entries(baseline), entries(candidate); verify_delta(before, after, after[HELPER])
    if HELPER in before: raise ValueError('Original control contains candidate helper')
    sources = [ROOT / 'tests/java' / n for n in SOURCE_NAMES]
    inputs = {str(p.relative_to(ROOT)):sha(p) for p in sources + sorted((ROOT / 'tools').glob('*.py'))}
    out.mkdir(); probes = out / 'probes'; probes.mkdir()
    run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(baseline), '-d', str(probes)] + [str(p) for p in sources])
    disassemblies = {}
    for label, jar in [('before', baseline), ('after', candidate)]:
        text = disassemble_entries(args.jdk, jar, [ENTRY]); (out / (label + '.javap')).write_text(text); disassemblies[label] = text
    # Independent instruction comparison: constant-pool text differs solely at pc30.
    instructions = lambda text: [line.strip() for line in text.splitlines() if re.match(r'^\s*\d+:', line)]
    old, new = instructions(disassemblies['before']), instructions(disassemblies['after'])
    if len(old) != len(new) or [(a,b) for a,b in zip(old,new) if a != b] != [
        ('30: invokevirtual #8                  // Method com/apple/xsr/DriveSelectionPanel.setArrayIndex:(I)V',
         '30: invokestatic  #90                 // Method compat/ArrayInfoSelection.setArrayIndex:(Lcom/apple/xsr/DriveSelectionPanel;I)V')]:
        raise ValueError('Independent listener bytecode comparison differs')
    record = {'source_commit':initial['commit'], 'source_dirty':False, 'inputs':inputs,
              'baseline_jar_sha256':sha(baseline), 'candidate_jar_sha256':sha(candidate), 'delta':delta,
              'whole_jar_inverse_exact':True, 'all_other_entries_unchanged':True,
              'scope':'Actual information listener and no-system refresh; synthetic detail components and fresh raster icons; no native presentation or hardware qualification',
              'runs':[], 'negatives':[]}
    for arch, expected_arch in [('aarch64', 'aarch64'), ('x64', 'x86_64')]:
        runtime = ROOT / ('build/secure-release-' + arch + '-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk')
        spec = runtime_manifest()['architectures'][arch]; verify_runtime(runtime, spec)
        for label, jar in [('before', baseline), ('after', candidate)]:
            lines = ['\t'.join([str(p.relative_to(probes)).replace('/', '.').removesuffix('.class'), str(probes), sha(p)]) for p in sorted(probes.rglob('*.class'))]
            with zipfile.ZipFile(jar) as z:
                for name in IDENTITIES + ([HELPER] if label == 'after' else []):
                    lines.append('\t'.join([name.replace('/', '.').removesuffix('.class'), str(jar), hashlib.sha256(z.read(name)).hexdigest()]))
            manifest = out / ('identity-' + arch + '-' + label + '.tsv'); manifest.write_text('\n'.join(lines) + '\n')
            fixed = 'true' if label == 'after' else 'false'
            for mode in ['-Xint', '-Xcomp']:
                compiler_flags = (['-XX:CompileCommand=quiet',
                    '-XX:CompileCommand=compileonly,com/apple/xsr/SystemInfoPane$5.propertyChange',
                    '-XX:CompileCommand=compileonly,compat/ArrayInfoSelection.setArrayIndex',
                    '-XX:+PrintCompilation'] if mode == '-Xcomp' else [])
                flags = JAVA_FLAGS + [mode, '-Xverify:all', '-Djava.awt.headless=true', '-Dlog4j.defaultInitOverride=true',
                                     '-Dfixture.expectedArch=' + expected_arch, '-Dfixture.fixed=' + fixed,
                                     '-Dfixture.requireFixed=' + fixed,
                                     '-Dfixture.identitymanifest=' + str(manifest)] + compiler_flags + ['-cp', str(probes) + ':' + str(jar)]
                command = [str(runtime / 'Contents/Home/bin/java')] + flags + ['uifixture.ArrayInfoFixObservation']
                result = subprocess.run(command, env=isolated_env(), capture_output=True, timeout=180)
                expected = ('PASS array info listener; fixed=' + fixed + '; valid_ids_preserved=true; raw_detail_selection_preserved=true; setter_once=true; radio_card_preserved=true; mode_transition=true; model_unchanged=true; forbidden_operations=0\n').encode()
                valid = result.returncode == 0 and not result.stderr
                try: compiled = validate_output(result.stdout, expected, mode, label == 'after')
                except (ValueError, UnicodeDecodeError): valid = False; compiled = []
                if not valid:
                    # Fixture emits only reviewed identifiers on failure; retain diagnostics locally, never secrets.
                    (out / ('failure-' + arch + '-' + label + '.stdout')).write_bytes(result.stdout)
                    (out / ('failure-' + arch + '-' + label + '.stderr')).write_bytes(result.stderr)
                    raise ValueError('Array-info observation failed; diagnostics withheld')
                log = out / ('jit-' + arch + '-' + label + '.txt')
                if mode == '-Xcomp': log.write_bytes(result.stdout)
                record['runs'].append({'architecture':arch, 'mode':mode, 'jar':label, 'stdout':expected.decode().strip(), 'empty_stderr':True, 'runtime_tree_sha256':spec['tree_sha256'],
                    'compiler_flags':compiler_flags, 'compiled_target_lines':compiled,
                    'jit_log_sha256':sha(log) if mode == '-Xcomp' else None})
                if label == 'before':
                    negative = command[:-1] + ['-Dfixture.requireFixed=true', command[-1]]
                    result = subprocess.run(negative, env=isolated_env(), capture_output=True, timeout=180)
                    validate_output(result.stdout, b'EXPECTED_NEGATIVE missing-fix\n', mode, False)
                    if (result.returncode != 1
                            or not result.stderr.startswith(b'Exception in thread "main" java.lang.AssertionError: array-info-fixture-failed\n')):
                        raise ValueError('Original fixed-oracle negative failed')
                    record['negatives'].append({'architecture':arch, 'mode':mode, 'expected_failure':'missing-fix', 'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
    if state() != initial or any(sha(ROOT / n) != h for n,h in inputs.items()) or check_array_info_artifact(args.build)[0] != identity:
        raise ValueError('Qualification inputs changed')
    (out / 'results.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    print('PASS array-info fix; 8 positive runs; 4 original negatives; exact whole-JAR inverse; ARM and x64 Rosetta; no controller')


if __name__ == '__main__': main()
