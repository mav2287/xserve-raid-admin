#!/usr/bin/env python3
"""Run real ACP and dispatch code against memory-only transport; no sockets or GUI."""
import argparse
import json
import platform
import subprocess
from pathlib import Path
import tempfile
import zipfile
from audit_support import ROOT, verify_jdk, verify_python, run_jdk, sha, isolated_env
from baseline import verify_original
from runtime import runtime_manifest, verify_runtime


def completed(result, parser_policy=False, allocation_policy=False, header_policy=False):
    lines = result.splitlines()
    marker = 'PASS parser failures: -103 terminal, one send each, no requeue; guarded_operations=0' if parser_policy else 'PASS memory-only transport and queue observations; real reconnection/backoff excluded'
    if header_policy: marker='PASS header quota observations; guarded_operations=0'
    if allocation_policy: marker='PASS response allocation observations; guarded_operations=0'
    if not lines or lines[-1] != marker:
        raise RuntimeError('Transport fixture incomplete; raw output withheld')
    return lines


def common_observations(lines, require_length_policy=False):
    legacy='follow_on invalid-length results=-102,-102; sends=1; outstanding=true; reconnects=0'
    security=[line for line in lines if line.startswith('security_length ')]
    expected=['security_length '+label+' fixed-marker; closed; no-input-or-cause' for label in ('invalid-length','negative-length','overflow-length')]+['security_length follow-on qualified by recovery fixture']
    if require_length_policy and not security:raise ValueError('Required length security policy missing')
    if security:
        if security!=expected or legacy in lines:raise ValueError('Intentional length security coverage differs')
    elif lines.count(legacy)!=1:raise ValueError('Original/legacy follow-on observation missing')
    return [line for line in lines if line!=legacy and not line.startswith('security_length ')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('jars', nargs='+', type=Path)
    parser.add_argument('--default-logging', action='store_true', help='Also require candidate configured logging to emit only one fixed error code')
    parser.add_argument('--runtime', action='append', type=Path, help='Pinned Runtime.jdk root; repeat for both architectures. Compiler runtime is used if omitted.')
    parser.add_argument('--parser-policy', action='store_true', help='Candidate-only quota/depth/blocked XML queue failure tests')
    parser.add_argument('--allocation-policy', action='store_true', help='Candidate-only oversized response rejection before allocation; original never receives oversized fixture')
    parser.add_argument('--length-policy', action='store_true', help='Require candidate malformed/negative-length markers; recovery separately recorded')
    parser.add_argument('--header-policy', action='store_true', help='Candidate-only header line/count/aggregate rejection and follow-on state')
    args = parser.parse_args()
    if any(jar.is_symlink() or not jar.is_file() for jar in args.jars):
        raise ValueError('Candidate JAR must be a regular file, not a symlink')
    args.jars = [jar.resolve() for jar in args.jars]
    verify_python(); lock = verify_jdk(args.jdk)
    original = ROOT / 'original/RAID_Admin_original.jar'; verify_original(original)
    if original.resolve() in args.jars: raise ValueError('Original must not be supplied as a candidate')
    fixture_commit = subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    fixture_dirty = bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    runtimes = []
    runtime_lock = runtime_manifest()
    seen = set()
    for root in args.runtime or []:
        architecture = None
        for key in ('aarch64', 'x64'):
            try: verify_runtime(root, runtime_lock['architectures'][key])
            except ValueError: continue
            architecture = key; break
        if architecture is None or architecture in seen:
            raise ValueError('Runtime must match a distinct pinned architecture')
        seen.add(architecture)
        runtimes.append((root.resolve()/'Contents/Home', architecture, root))
    if not runtimes: runtimes = [(args.jdk, 'compiler-runtime', None)]
    sources = [ROOT / p for p in ('tests/java/fixture/OfflineGuard.java',
               'tests/java/com/apple/xsr/net/TransportObservation.java', 'patches/sun/io/MalformedInputException.java','tests/java/com/apple/xsr/net/HeaderObservation.java')]
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    helpers = [ROOT/'tools'/name for name in ('audit_support.py','baseline.py','class_patch.py','runtime.py')]
    helper_hashes = {str(p.relative_to(ROOT)): sha(p) for p in helpers}
    tool_hash = sha(Path(__file__))
    observations = []
    parser_observations = []
    allocation_observations = []
    header_observations = []
    with tempfile.TemporaryDirectory(prefix='raid-transport-') as tmp:
        run_jdk(args.jdk, 'javac', ['-source','8','-target','8','-cp',str(original),'-d',tmp] + [str(p) for p in sources])
        shim = Path(tmp) / 'sun/io/MalformedInputException.class'
        for jar in [original] + args.jars:
            if jar.is_symlink() or not jar.is_file(): raise ValueError('JAR must be a regular file')
            identity = sha(jar)
            with zipfile.ZipFile(jar) as archive:
                if jar != original and archive.read('sun/io/MalformedInputException.class') != shim.read_bytes():
                    raise RuntimeError('Fixture shim differs from candidate shim')
            for home, architecture, root in runtimes:
                result = run_jdk(home, 'java', ['-Xverify:all','-Djava.awt.headless=true','-Duser.home=' + tmp,
                '-cp',tmp + ':' + str(jar.resolve()),'com.apple.xsr.net.TransportObservation'], timeout=20)
                observations.append({'jar_sha256': identity, 'architecture':architecture, 'application_logging':'forced-off', 'results': completed(result)})
                if args.default_logging and jar != original:
                    configured = run_jdk(home, 'java', ['-Xverify:all','-Djava.awt.headless=true','-Duser.home=' + tmp,
                    '-cp',tmp + ':' + str(jar.resolve()),'com.apple.xsr.net.TransportObservation','default-logging'], timeout=20)
                    observations.append({'jar_sha256':identity,'architecture':architecture,'application_logging':'candidate-configured; fixed stderr code verified','results':completed(configured)})
                if root is not None: verify_runtime(root, runtime_lock['architectures'][architecture])
                if args.parser_policy and jar != original:
                    for mode in ['parser-policy','parser-policy-default-logging']:
                        output=run_jdk(home,'java',['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,
                            '-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.TransportObservation',mode],timeout=20)
                        lines=completed(output,True)
                        if parser_observations and lines!=parser_observations[0]['results']: raise ValueError('Parser failure mapping varies with runtime/logging')
                        parser_observations.append({'jar_sha256':identity,'architecture':architecture,'mode':mode,'results':lines})
                    if root is not None: verify_runtime(root,runtime_lock['architectures'][architecture])
                if args.allocation_policy and jar != original:
                    for mode in ('allocation-policy','allocation-policy-default-logging'):
                        output=run_jdk(home,'java',['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,
                            '-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.TransportObservation',mode],timeout=20)
                        lines=completed(output,allocation_policy=True)
                        if allocation_observations and lines!=allocation_observations[0]['results']: raise ValueError('Allocation rejection varies with runtime/logging')
                        allocation_observations.append({'jar_sha256':identity,'architecture':architecture,'mode':mode,'results':lines})
                    if root is not None: verify_runtime(root,runtime_lock['architectures'][architecture])
                if args.header_policy and jar != original:
                    for mode in ('header-policy','header-policy-default-logging'):
                        output=run_jdk(home,'java',['-Xverify:all','-Xmx64m','-Xss1m','-Djava.awt.headless=true','-Duser.home='+tmp,
                            '-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.TransportObservation',mode],timeout=20)
                        lines=completed(output,header_policy=True)
                        if header_observations and lines!=header_observations[0]['results']:raise ValueError('Header failure observations differ')
                        header_observations.append({'jar_sha256':identity,'architecture':architecture,'mode':mode,'results':lines})
                    if root is not None:verify_runtime(root,runtime_lock['architectures'][architecture])
            if sha(jar) != identity: raise ValueError('JAR changed during observation')
    if any(common_observations(o['results']) != common_observations(observations[0]['results']) for o in observations):
        raise RuntimeError('Transport observations differ')
    if args.length_policy:
        for observation in observations:
            if observation['jar_sha256']!=sha(original):common_observations(observation['results'],True)
    if source_hashes != {str(p.relative_to(ROOT)): sha(p) for p in sources} or tool_hash != sha(Path(__file__)):
        raise ValueError('Fixture source changed during observation')
    if helper_hashes != {str(p.relative_to(ROOT)): sha(p) for p in helpers}:
        raise ValueError('Harness source changed during observation')
    verify_original(original)
    verify_jdk(args.jdk)
    print(json.dumps({'fixture_commit':fixture_commit, 'fixture_dirty':fixture_dirty, 'host_machine':platform.machine(),
        'tool_sha256':tool_hash, 'jdk_tree_sha256': lock['tree_sha256'],
        'runtime_trees':{arch:runtime_lock['architectures'][arch]['tree_sha256'] for arch in seen},
        'fixture_sources': source_hashes, 'harness_sources':helper_hashes, 'observations': observations,'parser_observations':parser_observations,'allocation_observations':allocation_observations,'header_observations':header_observations,
        'required_length_policy':args.length_policy,
        'length_recovery_scope':'Follow-on coverage is a reference to separately recorded architecture --recovery results, not a transport-tool claim.',
        'intentional_differences': 'When parseLength exists, malformed/overflow/negative response declarations use fixed terminal markers and retire the connection; original stale follow-on is retained in original results, candidate follow-on measured separately. All remaining transport observations must match.',
        'limits': 'Original queue and ACP send with bounded synthetic memory HttpConnection replies; Unsafe bypasses transport/model constructors. Reconnection injected through invalid-address callback. Two-request ordering observed after one injected drop, not concurrency or indefinite retry qualification. ACP status decoding through BasicResponse, not authentication UI or real controller. Exception shim supplied to original and candidate; candidate bytes verified identical. Firmware stream test invokes send twice directly, not via queue. Each reply uses a fresh stream; shared-socket residual bytes/desynchronization and real EOF/timeout timing are not qualified. Synthetic idle streams throw immediately after their scripted bytes. Per-process 20-second timeout is the outer bound. Candidate-only allocation probes use empty bodies with advertised 16777217 and 2147483647 bytes, 64 MiB heap, terminal -102 and zero reconnects; original JAR is never passed these oversized declarations. Boundary gate exercised without allocating ceiling-sized buffers. Candidate header-policy tests cover line 65537, field 129, aggregate 1048577, sticky rejection and terminal -102 without resend; follow-on security recovery is recorded separately by the architecture recovery fixture. No TCP, hardware, polling, or real reconnect/backoff qualification. x64 on this arm64 host is Rosetta, not physical Intel qualification.'}, indent=2))

if __name__ == '__main__': main()
