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
from class_patch import ClassFile
from runtime import runtime_manifest, verify_runtime


def completed(result, parser_policy=False, allocation_policy=False, header_policy=False):
    lines = result.splitlines()
    marker = 'PASS parser failures: -103 terminal, one send each, no requeue; guarded_operations=0' if parser_policy else 'PASS memory-only transport and queue observations; real reconnection/backoff excluded'
    if header_policy: marker='PASS header quota observations; guarded_operations=0'
    if allocation_policy: marker='PASS response allocation observations; guarded_operations=0'
    if not lines or lines[-1] != marker:
        raise RuntimeError('Transport fixture incomplete; raw output withheld')
    return lines


def completed_io(result, invalid_header_policy=False, null_io_policy=False, session_containment=False):
    expected=[
        'io invalid-header message_has_peer_line=true; direct_sends=1',
        'queue_response invalid-header-read-retry result=0 sends=2 terminal_callbacks=1',
        'queue_response invalid-header-mutation-retry result=0 sends=2 terminal_callbacks=1',
        'dispatch drops=1 malformed=false sends=2 terminal_callbacks=1',
        'io synthetic-restart lost-response; same-command-replayed; shutdown_flag=true; memory-only',
        'io null-message worker-escaped=NPE; callbacks=0; sends=1; stopped=false; connected=true; later_queue=1',
        'io shallow-clone property-changed-after-post; wire=after; sends=1; callbacks=1',
        'PASS IO characterization; guarded_operations=0']
    if invalid_header_policy:
        expected[:3]=['io invalid-header message_has_peer_line=false; direct_sends=1','queue_response invalid-header-read-terminal result=-102 sends=1 terminal_callbacks=1','queue_response invalid-header-mutation-terminal result=-102 sends=1 terminal_callbacks=1']
        expected.insert(-1,'io sync invalid-header fixed-IOException; no-peer-or-cause; sends=1')
    if null_io_policy:
        expected[5]='io null-message terminal=-102; callbacks=1; failed_sends=1; next_distinct=0; worker-survives'
    if session_containment:expected[5]='io null-message terminal=-102; callbacks=1; failed_sends=1; next_distinct=-102; session-stopped'
    lines=result.splitlines()
    if lines!=expected:raise ValueError('IO characterization differs; raw output withheld')
    return lines


def completed_null_io(result, session_containment=False):
    expected=['null_io '+label+' terminal=-102; fixed-no-cause; failed_sends=1; next_distinct=0; worker-survives' for label in ('eof','cause','changing-first-null')]+['null_io changing-first-text ordinary-retry; getMessage_calls=1; sends=2','null_io sync fixed-IOException; no-peer-or-cause; sends=1','PASS null IO policy; guarded_operations=0']
    if session_containment:expected=[line.replace('next_distinct=0; worker-survives','next_distinct=-102; session-stopped') for line in expected]
    if result.splitlines()!=expected:raise ValueError('Null IO policy differs; raw output withheld')
    return expected

def common_observations(lines, require_length_policy=False, require_framing_policy=False, require_invalid_header_policy=False):
    changed='response invalid-header framing-rejected'
    legacy_header='response invalid-header protocol-error'
    if require_invalid_header_policy and lines.count(changed)!=1:raise ValueError('Required invalid-header rejection missing')
    if changed in lines:
        if lines.count(changed)!=1 or legacy_header in lines:raise ValueError('Invalid-header rejection coverage differs')
        lines=[legacy_header if line==changed else line for line in lines]
    framing_map={
        'response missing-length framing-rejected':'response missing-length empty',
        'response missing-length-idle framing-rejected':'response missing-length-idle empty',
        'response duplicate-last-valid framing-rejected':'response duplicate-last-valid result=0',
        'response duplicate-last-zero framing-rejected':'response duplicate-last-zero empty',
        'response chunked framing-rejected':'response chunked empty',
        'response lowercase-length result=0':'response lowercase-length empty',
        'queue_response lowercase-length-parsed-success result=0 sends=1 terminal_callbacks=1':'queue_response lowercase-length-empty-success result=0 sends=1 terminal_callbacks=1',
    }
    has_framing=any(line in framing_map for line in lines)
    if require_framing_policy and not has_framing:raise ValueError('Required framing policy missing')
    if has_framing:
        if any(lines.count(line)!=1 for line in framing_map) or any(line in lines for line in framing_map.values()):raise ValueError('Intentional framing security coverage differs')
        lines=[framing_map.get(line,line) for line in lines]
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
    parser.add_argument('--framing-policy', action='store_true', help='Require candidate explicit unambiguous length policy')
    parser.add_argument('--session-containment',action='store_true',help='Require terminal rejected session and blocked follow-up writes')
    parser.add_argument('--null-io-policy', action='store_true', help='Require terminal null-message IO recovery and verifier negative control')
    parser.add_argument('--invalid-header-policy', action='store_true', help='Require fixed terminal malformed-header rejection')
    parser.add_argument('--io-characterization', action='store_true', help='Bounded memory queue/null-message/shallow-clone/restart-request characterization')
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
    io_observations = []
    null_io_observations = []
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
                if args.io_characterization:
                    output=run_jdk(home,'java',['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,
                        '-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.TransportObservation','io-characterization'],timeout=20)
                    io_observations.append({'jar_sha256':identity,'architecture':architecture,'results':completed_io(output,args.invalid_header_policy and jar!=original,args.null_io_policy and jar!=original,args.session_containment and jar!=original)})
                if args.null_io_policy and jar!=original:
                    output=run_jdk(home,'java',['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.TransportObservation','null-io-policy'],timeout=20)
                    results=completed_null_io(output,args.session_containment)
                    corrupted=Path(tmp)/'corrupt-manager.jar'
                    with zipfile.ZipFile(jar) as archive,zipfile.ZipFile(corrupted,'w') as bad:
                        for entry in archive.namelist():
                            data=archive.read(entry)
                            if entry=='com/apple/xsr/net/CommunicationsManager.class':
                                cls=ClassFile(data);m=next(m for m in cls.methods if m['name']=='run');_,begin,end=next(a for a in m['attributes'] if a[0]=='Code');data=bytearray(data)
                                if data[begin+14+339:begin+14+344]!=bytes.fromhex('c8000000d6'):raise ValueError('Required null IO trampoline missing')
                                data[begin+14+340:begin+14+344]=bytes.fromhex('00000001')
                            bad.writestr(entry,data)
                    negative=run_jdk(home,'java',['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',tmp+':'+str(corrupted),'com.apple.xsr.net.TransportObservation','verify-manager-corrupt'],timeout=20)
                    if negative!='PASS corrupt manager rejected by verifier; guarded_operations=0\n':raise ValueError('Manager verifier negative control differs; raw output withheld')
                    null_io_observations.append({'jar_sha256':identity,'architecture':architecture,'results':results,'verifier_negative_control':negative.strip()})
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
    if args.framing_policy:
        for observation in observations:
            if observation['jar_sha256']!=sha(original):common_observations(observation['results'],True,True)
    if args.session_containment and not args.null_io_policy:raise ValueError('Session containment requires null IO evidence')
    if args.null_io_policy and (not args.io_characterization or not args.invalid_header_policy):raise ValueError('Null IO qualification requires IO/header policy evidence')
    if args.invalid_header_policy:
        if not args.io_characterization:raise ValueError('Invalid-header qualification requires IO observations')
        for observation in observations:
            if observation['jar_sha256']!=sha(original):common_observations(observation['results'],True,True,True)
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
        'required_framing_policy':args.framing_policy,'required_invalid_header_policy':args.invalid_header_policy,'required_session_containment':args.session_containment,'required_null_io_policy':args.null_io_policy,'null_io_observations':null_io_observations,'null_io_limits':('Exact-marker session stop; already-queued synthetic mutation/restart blocked, later async post stranded without callback, stopped-before-post sync throws; post/exit race remains unqualified. ' if args.session_containment else '')+'Injected EOF/null/caused/changing-message IO at a memory seam; real socket origin and timing unqualified. One getMessage evaluation with logging disabled. Source outcome unconfirmed. Synchronous fixed exception and classpath VerifyError negative control measured. Other IO retry policy unchanged.' if args.null_io_policy else None,
        'io_observations':io_observations,
        'io_limits':('Session containment supersedes next-command success for exact security markers; broader nonnull IO replay remains open. ' if args.session_containment else '')+'Initial G10-a cases only, not classifier qualification; factory/RPC metadata and complete caller/UI/sequencing inventories remain open. Actual send/dispatch with bounded memory responses. Manager constructor is bypassed; a standalone fixture worker calls run, not the constructor-started CommMgr thread. Its custom uncaught handler captures only class/throw site; default thread-group stderr behavior is not measured. Null IOException is injected at the transport seam, not shown to originate from a real socket/parser. Original/audit.11 invalid-header retry is bounded only by the scripted valid second reply; with explicit invalid-header policy the candidate returns -102 after one send. Repeated bad peers and real reconnects are not qualified. Restart is synthetic serialization on memory output; shutdown_flag reports the request flag, not transport effect or a controller operation. Original null-message worker death leaves a later async post queued; with explicit null IO policy the candidate produces a fixed terminal failure. The session-containment flag changes follow-up behavior from fresh read success to blocked queued mutation/restart and permanent session stop. synchronous callers after that death and polling blockage remain unmeasured. Fixed malformed-header synchronous IOException is measured with explicit policy. Mutation -102 does not mean not applied; outcome is unconfirmed. CLI direct entry/exit remains unqualified. Header properties are changed synchronously after enqueue, not a parameter-structure or concurrency stress test. Reconnect uses invalid-address callback injection, not TCP/backoff.' if args.io_characterization else None,
        'length_recovery_scope':'Follow-on coverage is a reference to separately recorded architecture --recovery results, not a transport-tool claim.',
        'invalid_header_scope':'Fixed terminal colonless/leading-colon rejection only; unconfirmed controller outcome, ordinary nonnull IO replay unchanged; null-message handling follows null_io_limits.' if args.invalid_header_policy else None,
        'intentional_differences': 'When ResponseFraming exists, five missing/duplicate/chunked direct cases reject and one lowercase direct/queue case parses its plist; complete exact-line coverage is required. When parseLength exists, malformed/overflow/negative response declarations use fixed terminal markers and retire the connection; original stale follow-on is retained in original results, candidate follow-on measured separately. All remaining transport observations must match.',
        'limits': 'Original queue and ACP send with bounded synthetic memory HttpConnection replies; Unsafe bypasses transport/model constructors. Reconnection injected through invalid-address callback. Two-request ordering observed after one injected drop, not concurrency or indefinite retry qualification. ACP status decoding through BasicResponse, not authentication UI or real controller. Exception shim supplied to original and candidate; candidate bytes verified identical. Firmware stream test invokes send twice directly, not via queue. Each reply uses a fresh stream; shared-socket residual bytes/desynchronization and real EOF/timeout timing are not qualified. Synthetic idle streams throw immediately after their scripted bytes. Per-process 20-second timeout is the outer bound. Candidate-only allocation probes use empty bodies with advertised 16777217 and 2147483647 bytes, 64 MiB heap, terminal -102 and zero reconnects; original JAR is never passed these oversized declarations. Boundary gate exercised without allocating ceiling-sized buffers. Candidate header-policy tests cover line 65537, field 129, aggregate 1048577, sticky rejection and terminal -102 without resend; follow-on security recovery is recorded separately by the architecture recovery fixture. No TCP, hardware, polling, or real reconnect/backoff qualification. x64 on this arm64 host is Rosetta, not physical Intel qualification.'}, indent=2))

if __name__ == '__main__': main()
