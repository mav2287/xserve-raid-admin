#!/usr/bin/env python3
"""Compare bounded shared-stream association on the immutable and candidate JARs."""
import argparse
import json
import platform
import subprocess
import tempfile
from pathlib import Path
from audit_support import ROOT, sha, verify_jdk, verify_python, run_jdk, isolated_env
from baseline import verify_original
from runtime import runtime_manifest, verify_runtime

EXPECTED = [
    'shared source-controls idle-timeout; terminal-close PASS',
    'shared canonical first=first second=second pending_before_second=0 pending_after_second=0 reads=225 sends=2 closes=0',
    'shared missing-length first=empty second=prior-body pending_before_second=117 pending_after_second=113 reads=141 sends=2 closes=0',
    'shared lowercase-length first=empty second=prior-body pending_before_second=117 pending_after_second=113 reads=162 sends=2 closes=0',
    'shared duplicate-last-zero first=empty second=prior-body pending_before_second=117 pending_after_second=113 reads=181 sends=2 closes=0',
    'shared declared-zero first=empty second=prior-body pending_before_second=117 pending_after_second=113 reads=160 sends=2 closes=0',
    'shared chunked first=empty second=protocol-error pending_before_second=13 pending_after_second=118 reads=60 sends=2 closes=0 follow_on=blocked',
    'PASS shared-stream association; guarded_operations=0',
]
FRAMING_EXPECTED = [EXPECTED[0],
    'framing canonical first=first second=second; sends=2; pending=0; closes=0',
    'framing lowercase first=first second=second; sends=2; pending=0; closes=0',
    'framing zero first=empty second=second; sends=2; pending=0; closes=0',
    'framing missing fixed-marker; retired; sends=1; no-cause',
    'framing duplicate-identical fixed-marker; retired; sends=1; no-cause',
    'framing duplicate-mixed-case fixed-marker; retired; sends=1; no-cause',
    'framing duplicate-last-zero fixed-marker; retired; sends=1; no-cause',
    'framing transfer-encoding fixed-marker; retired; sends=1; no-cause',
    'framing uppercase-turkish first=first second=second; sends=2; pending=0; closes=0',
    'framing transfer-encoding-turkish fixed-marker; retired; sends=1; no-cause',
    'framing connection-close original-source-close; sends=1; pending=0; closes=1',
    EXPECTED[5], 'PASS framing policy; guarded_operations=0']

def completed(output, framing=False):
    lines = output.splitlines()
    if lines != (FRAMING_EXPECTED if framing else EXPECTED):
        raise ValueError('Unexpected shared-stream observations; raw output withheld')
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--runtime', required=True, action='append', type=Path)
    parser.add_argument('--candidate-sha256', required=True)
    parser.add_argument('--framing-policy', action='store_true')
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    verify_python(); compiler = verify_jdk(args.jdk)
    original = ROOT/'original/RAID_Admin_original.jar'; verify_original(original)
    if args.candidate.is_symlink() or not args.candidate.is_file() or args.candidate.resolve() == original.resolve():
        raise ValueError('Expected distinct regular candidate')
    candidate = args.candidate.resolve()
    if len(args.candidate_sha256)!=64 or sha(candidate)!=args.candidate_sha256:
        raise ValueError('Candidate differs from required anchored identity')
    lock = runtime_manifest(); runtimes = {}; roots = {}
    for root in args.runtime:
        matching = []
        for arch in ('aarch64', 'x64'):
            try: verify_runtime(root, lock['architectures'][arch])
            except ValueError: continue
            matching.append(arch)
        if len(matching) != 1 or matching[0] in roots:
            raise ValueError('Runtime must match a distinct pinned architecture')
        arch = matching[0]; roots[arch] = root.resolve(); runtimes[arch] = lock['architectures'][arch]['tree_sha256']
    sources = [ROOT/p for p in ('tests/java/fixture/OfflineGuard.java',
               'tests/java/com/apple/xsr/net/SharedResponseObservation.java',
               'patches/sun/io/MalformedInputException.java')]
    inputs = sources + [Path(__file__).resolve()] + [ROOT/'tools'/name for name in
             ('audit_support.py', 'baseline.py', 'runtime.py', 'class_patch.py', 'socket_configuration_patch.py','connection_publication_patch.py')]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    identities = {jar: sha(jar) for jar in (original, candidate)}
    commit = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=ROOT, env=isolated_env(), text=True).strip()
    dirty = bool(subprocess.check_output(['/usr/bin/git', 'status', '--porcelain'], cwd=ROOT, env=isolated_env()))
    observations = []
    with tempfile.TemporaryDirectory(prefix='raid-shared-') as tmp:
        run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(original), '-d', tmp]+[str(p) for p in sources])
        for jar in (original, candidate):
            for arch, root in roots.items():
                framing=args.framing_policy and jar==candidate
                output = run_jdk(root/'Contents/Home', 'java', ['-Xverify:all', '-Xmx64m',
                       '-Djava.awt.headless=true', '-Duser.home='+tmp, '-cp', tmp+':'+str(jar),
                       'com.apple.xsr.net.SharedResponseObservation']+(['framing-policy'] if framing else []), timeout=20)
                lines = completed(output,framing)
                if any(o['mode']==('framing-policy' if framing else 'baseline') and lines!=o['results'] for o in observations):
                    raise ValueError('Shared-stream observations differ')
                observations.append({'jar_sha256': identities[jar], 'architecture': arch, 'mode':'framing-policy' if framing else 'baseline', 'results': lines})
                verify_runtime(root, lock['architectures'][arch])
    if hashes != {str(p.relative_to(ROOT)): sha(p) for p in inputs} or identities != {jar: sha(jar) for jar in identities}:
        raise ValueError('Inputs changed during observation')
    verify_original(original); verify_jdk(args.jdk)
    print(json.dumps({'fixture_commit': commit, 'fixture_dirty': dirty, 'host_machine': platform.machine(),
          'compiler_tree_sha256': compiler['tree_sha256'], 'runtime_trees': runtimes,
          'sources': hashes, 'observations': observations,
          'required_framing_policy':args.framing_policy,
          'limits': 'One synthetic persistent InputStream per two actual ACP sends; replies appended only after request serialization. Chunked case has a third blocked send attempt with no output acquisition. Exhaustion throws immediate synthetic timeout, close is terminal: these are fixture controls, not measured legacy timeout handling. Peer EOF is not modeled. Baseline mode does not model Connection: close; framing-policy mode tests one valid-length close reply and performs no follow-on socket operation. Uppercase Content-Length under Turkish locale is a case-folding control; uppercase Transfer-Encoding contains I and exercises the Turkish locale hazard. At most 8192 bytes per reply, 16384 read calls per source, 64 MiB heap and 20 second subprocess bound. No TCP, timing, controller, UI, authentication, polling or queue-retry qualification. No raw requests, peer content, credentials or exception messages printed. x64 here uses Rosetta, not physical Intel. Without policy mode original/candidate baseline gaps match. Policy mode verifies explicit unambiguous length, locale independence and retirement, and retains declared-zero extra-body association as a known gap. Stricter framing cannot encrypt or authenticate legacy HTTP.'}, indent=2))


if __name__ == '__main__': main()
