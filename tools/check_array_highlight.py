#!/usr/bin/env python3
"""Observe original/current array highlights with fresh headless raster images only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from audit_support import ROOT, JAVA_FLAGS, isolated_env, verify_jdk, verify_python, run_jdk, sha
from runtime import runtime_manifest, verify_runtime

EXPECTED = 'PASS array highlight; transitions=1000; pixel_checks=14000; drive_to_array=true; cleared_row_paths=2; zero_tints_unassigned=true; minus_ten_clears=true; fresh_buffer_only=true; forbidden_operations=0\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    verify_python(); verify_jdk(args.jdk)
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('Fresh output under build required')
    original = ROOT / 'original/RAID_Admin_original.jar'
    current = ROOT / 'build/secure-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(original) != '5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449' or sha(current) != 'bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e':
        raise ValueError('Frozen input JAR differs')
    sources = [ROOT / 'tests/java' / name for name in (
        'uifixture/ArrayHighlightObservation.java', 'fixture/OfflineGuard.java', 'fixture/FixtureIdentity.java')]
    record = {'scope': 'fresh headless raster rendering; no native display or live model qualification',
              'source_commit': subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=ROOT, env=isolated_env(), text=True).strip(),
              'source_dirty': bool(subprocess.check_output(['/usr/bin/git', 'status', '--porcelain'], cwd=ROOT, env=isolated_env())),
              'inputs': {str(p.relative_to(ROOT)): sha(p) for p in sources + [Path(__file__).resolve(), original, current]}, 'runs': []}
    probes = output / 'probes'; probes.mkdir(parents=True)
    run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(original), '-d', str(probes)] + [str(p) for p in sources])
    for arch, expected_arch in [('aarch64', 'aarch64'), ('x64', 'x86_64')]:
        runtime = ROOT / ('build/secure-release-' + arch + '-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk')
        lock = runtime_manifest()['architectures'][arch]; verify_runtime(runtime, lock)
        for label, jar in [('original', original), ('current', current)]:
            lines = ['\t'.join([str(p.relative_to(probes)).replace('/', '.').removesuffix('.class'), str(probes), sha(p)]) for p in sorted(probes.rglob('*.class'))]
            with zipfile.ZipFile(jar) as archive:
                for name in ['com/apple/xsr/DriveSelectionPanel.class', 'com/apple/xsr/DrivePanel.class', 'com/apple/gui/GUIFactory.class', 'com/apple/xsr/Resources.class', 'com/apple/xsr/ArraySelectionPanel.class', 'com/apple/xsr/ArraySelectionPanel$ArrayLabel.class', 'com/apple/xsr/ArraySelectionPanel$2.class', 'com/apple/xsr/ArraySelectionPanel$3.class', 'com/apple/xsr/ArraySelectionPanel$4.class']:
                    lines.append('\t'.join([name.replace('/', '.').removesuffix('.class'), str(jar), hashlib.sha256(archive.read(name)).hexdigest()]))
            manifest = output / ('identity-' + arch + '-' + label + '.tsv')
            manifest.write_text('\n'.join(lines) + '\n')
            flags = ['-Xint', '-Djava.awt.headless=true', '-Dlog4j.defaultInitOverride=true',
                     '-Dfixture.expectedArch=' + expected_arch, '-Dfixture.identitymanifest=' + str(manifest)]
            proc = subprocess.run([str(runtime / 'Contents/Home/bin/java')] + JAVA_FLAGS + flags + ['-cp', str(probes) + ':' + str(jar), 'uifixture.ArrayHighlightObservation'],
                                  env=isolated_env(), capture_output=True, timeout=45)
            if proc.returncode or proc.stdout.decode() != EXPECTED or proc.stderr:
                raise ValueError('Array observation failed; execution output withheld')
            record['runs'].append({'architecture': arch, 'jar': label, 'stdout': EXPECTED.strip(), 'empty_stderr': True, 'runtime_tree_sha256': lock['tree_sha256']})
    (output / 'results.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print('PASS original/current fresh-buffer highlights on native ARM and x64 Rosetta; native display issue remains unresolved')


if __name__ == '__main__':
    main()
