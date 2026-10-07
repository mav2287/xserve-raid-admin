#!/usr/bin/env python3
"""Observe existing runtime architectures without starting RAID Admin or networking."""
import argparse
import json
import platform
import re
from pathlib import Path
import subprocess
import tempfile
import zipfile

from audit_support import ROOT, digest, isolated_env, run_jdk, sha, tree, verify_jdk, verify_python
from baseline import verify_original


def validate_containment_recovery(lines,expected):
    if not isinstance(lines,list) or len(lines)!=143 or any(type(line) is not str for line in lines) or lines!=expected:raise ValueError('Session recovery differs from reviewed exact matrix; raw output withheld')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--jar', required=True, type=Path)
    parser.add_argument('--runtime', required=True, action='append', type=Path)
    parser.add_argument('--folders', action='store_true', help='Also require the candidate Desktop bridge regression to pass')
    parser.add_argument('--menus', action='store_true', help='Check menu adapter callbacks without initializing native UI')
    parser.add_argument('--vendor-extensions', action='store_true', help='Use only the Java 8 runtime vendor extension directory, as the bundled launcher does')
    parser.add_argument('--security', action='store_true', help='Require resolver isolation and request-format redaction regressions')
    parser.add_argument('--logging', action='store_true', help='Check actual JAR logging configuration and fixed-code appender')
    parser.add_argument('--parser', action='store_true', help='Compare accepted XML boundaries and values')
    parser.add_argument('--recovery', action='store_true', help='Candidate marker cleanup and no-replay fixtures; ordinary original logging parity')
    parser.add_argument('--headers', action='store_true', help='Compare bounded header corpus and candidate-only limits')
    parser.add_argument('--stop-lock-order',action='store_true',help='Require audit.19 volatile stop field and queue lock reads; separate deadlock gate supplies concurrency proof')
    parser.add_argument('--connect-failure-stop',action='store_true',help='Require audit.18 reported connection failure stop; separate constructor gate proves sequencing')
    parser.add_argument('--sync-preenqueue',action='store_true',help='Require audit.17 constructor guard; separate posting gate supplies sequencing proof')
    parser.add_argument('--worker-failure-stop',action='store_true',help='Require worker-fault stopped-session selection')
    parser.add_argument('--terminal-io-policy',action='store_true',help='Require audit.15 non-prefix IO terminal policy')
    parser.add_argument('--session-containment',action='store_true',help='Require security-marker session stop and blocked queued writes')
    parser.add_argument('--null-io-policy', action='store_true', help='Require null-message terminal IO recovery')
    parser.add_argument('--invalid-header-policy', action='store_true', help='Require terminal invalid-header recovery')
    parser.add_argument('--framing-policy', action='store_true', help='Require response framing class and expanded recovery coverage')
    args = parser.parse_args()
    verify_python()
    fixture_commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    fixture_dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    compiler = verify_jdk(args.compiler)
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    if args.jar.is_symlink() or not args.jar.is_file():
        raise ValueError('Candidate must be a regular file, not a symlink')
    candidate_sha = sha(args.jar)
    with zipfile.ZipFile(args.jar) as archive: framing_policy='compat/ResponseFraming.class' in archive.namelist()
    with zipfile.ZipFile(args.jar) as archive: invalid_header_policy=framing_policy and b'invalidHeader' in archive.read('compat/ResponseFraming.class')
    with zipfile.ZipFile(args.jar) as archive: null_io_policy='compat/RejectionRecovery.class' in archive.namelist() and b'nullMessage' in archive.read('compat/RejectionRecovery.class')
    with zipfile.ZipFile(args.jar) as archive:session_containment='compat/RejectionRecovery.class' in archive.namelist() and b'STOPS_REJECTED_SESSIONS' in archive.read('compat/RejectionRecovery.class')
    with zipfile.ZipFile(args.jar) as archive:terminal_io_policy=b'TERMINATES_AMBIGUOUS_IO' in archive.read('compat/RejectionRecovery.class') if 'compat/RejectionRecovery.class' in archive.namelist() else False
    with zipfile.ZipFile(args.jar) as archive:worker_failure_stop=b'STOPS_OPERATION_FAILURES' in archive.read('compat/RejectionRecovery.class') if 'compat/RejectionRecovery.class' in archive.namelist() else False
    with zipfile.ZipFile(args.jar) as archive,zipfile.ZipFile(original) as reference:sync_preenqueue=archive.read('com/apple/xsr/net/CommunicationsManager$SyncSender.class')!=reference.read('com/apple/xsr/net/CommunicationsManager$SyncSender.class')
    with zipfile.ZipFile(args.jar) as archive:connect_failure_stop=b'STOPS_REPORTED_CONNECT_FAILURES' in archive.read('compat/RejectionRecovery.class') if 'compat/RejectionRecovery.class' in archive.namelist() else False
    with zipfile.ZipFile(args.jar) as archive:stop_lock_order=b'AVOIDS_STOP_LOCK_INVERSION' in archive.read('compat/RejectionRecovery.class') if 'compat/RejectionRecovery.class' in archive.namelist() else False
    if stop_lock_order!=args.stop_lock_order or stop_lock_order and not args.connect_failure_stop:raise ValueError('Stop lock qualification flag differs')
    if connect_failure_stop!=args.connect_failure_stop or connect_failure_stop and not args.sync_preenqueue:raise ValueError('Connect failure qualification flag differs')
    if sync_preenqueue!=args.sync_preenqueue or sync_preenqueue and not worker_failure_stop:raise ValueError('Sync constructor qualification flag differs')
    if worker_failure_stop!=args.worker_failure_stop or worker_failure_stop and not args.terminal_io_policy:raise ValueError('Worker fault qualification flag differs')
    if terminal_io_policy!=args.terminal_io_policy or (args.terminal_io_policy and not args.session_containment):raise ValueError('Terminal IO qualification flag differs')
    if session_containment!=args.session_containment or (args.session_containment and not args.null_io_policy):raise ValueError('Session containment qualification flag differs')
    if args.null_io_policy and (not args.recovery or not null_io_policy):raise ValueError('Required null IO policy missing')
    if args.invalid_header_policy and (not args.recovery or not args.headers or not invalid_header_policy):raise ValueError('Required invalid-header policy missing')
    if args.framing_policy and (not args.recovery or not framing_policy):raise ValueError('Required framing recovery policy missing')
    sources = [ROOT / 'tests/java/ApiProbe.java', ROOT / 'tests/java/com/apple/xsr/net/OfflineParity.java']
    if args.folders:
        sources += [ROOT / 'tests/java/FolderProbe.java', ROOT / 'tests/java/fixture/OfflineGuard.java']
    if args.menus:
        sources += [ROOT / 'tests/java/com/apple/mrj/MenuProbe.java']
        if not args.folders:
            sources += [ROOT / 'tests/java/fixture/OfflineGuard.java']
    if args.vendor_extensions:
        sources += [ROOT / 'tests/java/RuntimeProbe.java']
    if args.security:
        sources += [ROOT / 'tests/java/SecurityProbe.java', ROOT / 'tests/java/fixture/OfflineGuard.java']
    if args.logging:
        sources += [ROOT/'tests/java/LoggingProbe.java', ROOT/'tests/java/fixture/OfflineGuard.java']
    if args.parser:
        sources += [ROOT/'tests/java/ParserParityProbe.java', ROOT/'tests/java/fixture/OfflineGuard.java']
    if args.headers:
        sources += [ROOT/'tests/java/com/apple/xsr/net/HeaderObservation.java',ROOT/'tests/java/fixture/OfflineGuard.java']
    if args.recovery:
        sources += [ROOT/'tests/java/com/apple/xsr/net/RecoveryObservation.java',ROOT/'tests/java/com/apple/xsr/net/HeaderObservation.java',ROOT/'tests/java/fixture/OfflineGuard.java',ROOT/'patches/sun/io/MalformedInputException.java']
    sources = list(dict.fromkeys(sources))
    identity_sources=list(sources)+[ROOT/"tools/socket_configuration_patch.py"]
    if session_containment:
        expected_path=ROOT/('audit/stopped-post-recovery-expected.json' if stop_lock_order else 'audit/connect-stop-recovery-expected.json' if connect_failure_stop else 'audit/sync-preenqueue-recovery-expected.json' if sync_preenqueue else 'audit/worker-stop-recovery-expected.json' if worker_failure_stop else 'audit/terminal-io-recovery-expected.json' if terminal_io_policy else 'audit/session-containment-recovery-expected.json')
        expected_recovery_record=json.loads(expected_path.read_bytes())
        if expected_recovery_record['candidate_jar_sha256']!=candidate_sha:raise ValueError('Session matrix candidate identity differs')
        validate_containment_recovery(expected_recovery_record['lines'],expected_recovery_record['lines'])
        identity_sources.append(expected_path)
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in identity_sources}
    with zipfile.ZipFile(args.jar) as archive:guarded_worker=b"workerActiveTxn" in archive.read("com/apple/xsr/net/CommunicationsManager.class")
    observations = []
    expected_parser = None
    expected_headers = None
    expected_recovery = None
    with tempfile.TemporaryDirectory(prefix='raid-architecture-') as tmp:
        run_jdk(args.compiler, 'javac', ['-source', '8', '-target', '8', '-cp', str(args.jar.resolve()) + ':' + str(original),
                                       '-d', tmp] + [str(p) for p in sources])
        expected = None
        for runtime in args.runtime:
            runtime = runtime.resolve()
            runtime_identity = digest(tree(runtime))
            try:
                version_result = subprocess.run([str(runtime / 'bin/java'), '-version'],
                                                env=isolated_env(), capture_output=True, timeout=10)
            except subprocess.TimeoutExpired:
                raise RuntimeError('Runtime version probe timed out; command withheld') from None
            version = re.search(r'version "([^"]+)"', version_result.stderr.decode('utf-8'))
            if version is None or not version[1].startswith(('1.8.', '11.')):
                raise ValueError('This observation supports Java 8 and 11 only')
            extension_path = str(runtime / 'jre/lib/ext') if args.vendor_extensions else ''
            extension_flags = ['-Djava.ext.dirs=' + extension_path, '-Djava.endorsed.dirs='] if version[1].startswith('1.8.') else []
            if args.vendor_extensions:
                extension_flags += ['-Djava.library.path=' + str(runtime / 'jre/lib')]
            def run(jar, entry, *arguments):
                # These flags work on both Java 8 and 11. This is a runtime observation,
                # separate from the Java-8-only reproducible build environment.
                resource_flags=['-Xmx64m','-Xss1m'] if entry in ('com.apple.xsr.net.HeaderObservation','com.apple.xsr.net.RecoveryObservation') else []
                command = [str(runtime / 'bin/java'), '-Xverify:all'] + resource_flags + extension_flags + ['-Djava.awt.headless=true', '-Duser.home=' + tmp,
                           '-Dfile.encoding=UTF-8', '-Duser.language=en', '-Duser.country=US',
                           '-Duser.timezone=UTC', '-cp', tmp + ':' + str(jar.resolve()), entry] + list(arguments)
                try:
                    result = subprocess.run(command, env=isolated_env(), capture_output=True, timeout=30)
                except subprocess.TimeoutExpired:
                    raise RuntimeError('Architecture fixture timed out; command withheld') from None
                if result.returncode:
                    raise RuntimeError('Architecture fixture failed; raw output withheld')
                return result.stdout.decode('utf-8')
            api = run(original, 'ApiProbe').splitlines()
            results = [run(jar, 'com.apple.xsr.net.OfflineParity') for jar in (original, args.jar)]
            if expected is None:
                expected = results[0]
            if any(result != expected for result in results):
                raise RuntimeError('Serializer/HTTP-parser parity differs across runtimes or artifacts')
            observations.append({'runtime_tree_sha256': runtime_identity, 'api': api,
                                 'parity': 'PASS', 'fixture_output_sha256': digest(results[0])})
            if args.folders:
                observations[-1]['folder_regression'] = [run(original, 'FolderProbe', 'false').strip(),
                                                        run(args.jar, 'FolderProbe', 'true').strip()]
            if args.menus:
                observations[-1]['menu_regression'] = run(args.jar, 'com.apple.mrj.MenuProbe').strip()
            if args.vendor_extensions:
                observations[-1]['vendor_extension_regression'] = run(args.jar, 'RuntimeProbe').strip()
            if args.security:
                original_security = run(original, 'SecurityProbe', 'false').splitlines()
                candidate_security = run(args.jar, 'SecurityProbe', 'true').splitlines()
                if original_security[:-1] != candidate_security[:-1]:
                    raise RuntimeError('Allowed XML behavior differs across artifacts')
                observations[-1]['security_regression'] = candidate_security
            if args.logging:
                observations[-1]['logging_regression'] = [run(args.jar,'LoggingProbe').strip(),run(args.jar,'LoggingProbe','write-failure').strip(),run(args.jar,'LoggingProbe','closed-first').strip()]
            if args.parser:
                parser_results = [run(jar,'ParserParityProbe').splitlines() for jar in (original,args.jar)]
                if any(not lines or lines[-1] != 'PASS accepted parser parity; guarded_operations=0' for lines in parser_results) or parser_results[0] != parser_results[1]:
                    raise RuntimeError('Accepted parser differential failed')
                if expected_parser is None: expected_parser = parser_results[1]
                if parser_results[1] != expected_parser: raise RuntimeError('Accepted parser outputs differ across runtimes')
                observations[-1]['parser_regression'] = parser_results[1]
            if args.headers:
                header_results=[run(original,'com.apple.xsr.net.HeaderObservation','false').splitlines(),run(args.jar,'com.apple.xsr.net.HeaderObservation','true').splitlines()]
                marker='PASS bounded header observations; guarded_operations=0'
                if any(not lines or lines[-1]!=marker for lines in header_results): raise RuntimeError('Header fixture incomplete')
                allowed=[line for line in header_results[1] if not line.startswith('rejection ')]
                if allowed!=header_results[0] or len(allowed)!=7 or len(header_results[1])!=10: raise RuntimeError('Header acceptance or coverage differs')
                if expected_headers is None: expected_headers=header_results[1]
                if header_results[1]!=expected_headers: raise RuntimeError('Header observations differ across runtimes')
                observations[-1]['header_regression']=header_results[1]
            if args.recovery:
                a=run(original,'com.apple.xsr.net.RecoveryObservation','false').splitlines()
                b=run(args.jar,'com.apple.xsr.net.RecoveryObservation','true').splitlines()
                if worker_failure_stop and (not a or a[0].count('connected=true')!=1):raise ValueError('Original ordinary-fault logger control differs')
                first_expected=a[0] if a else None
                if worker_failure_stop and first_expected:first_expected=first_expected.replace('connected=true','connected=false; stop=true')
                if guarded_worker and first_expected:first_expected=first_expected.replace('method=run','method=dispatchLoop')
                if len(a)!=2 or not b or b[0]!=first_expected or a[-1]!='PASS recovery fixed=false; guarded_operations=0' or b[-1]!='PASS recovery fixed=true; guarded_operations=0' or len(b)!=(143 if session_containment else 141 if null_io_policy else 135 if invalid_header_policy else 113 if framing_policy else 78):
                    raise RuntimeError('Recovery coverage incomplete or ordinary logger parity differs')
                if null_io_policy:
                    expected_null=['null_io_recovery log_capture=false close_failure='+str(failure)+' logger_failure=false stop=false results=-102,0 sends=2 reconnect_seams=1' for failure in range(3)]+['null_io_recovery log_capture=true close_failure=0 logger_failure=true stop=false results=-102,0 sends=2 reconnect_seams=1','null_io_recovery log_capture=true close_failure=0 logger_failure=false stop=false results=-102,0 sends=2 reconnect_seams=1','null_io_recovery log_capture=false close_failure=0 logger_failure=false stop=true results=-102,-102 sends=1 reconnect_seams=0']
                    if session_containment:expected_null=[line.replace('stop=false results=-102,0 sends=2 reconnect_seams=1','stop=true results=-102,-102 sends=1 reconnect_seams=0') for line in expected_null]
                    if [line for line in b if line.startswith('null_io_recovery ')]!=expected_null:raise RuntimeError('Null IO recovery coverage differs; raw output withheld')
                if session_containment:
                    reviewed=list(expected_recovery_record['lines'])
                    if guarded_worker:
                        if sum('method=run;' in line for line in reviewed)!=1 or sum('callback-drain-unqualified' in line for line in reviewed)!=2:raise ValueError('Reviewed worker recovery seams differ')
                        reviewed=[line.replace('method=run;','method=dispatchLoop;').replace('queued=1; callback-drain-unqualified','queued=0; callbacks=2; terminal-drain') for line in reviewed]
                    validate_containment_recovery(b,reviewed)
                    wanted=['containment callback-throws null_io='+value+('; sends=1; stopped=true; queued=0; callbacks=2; terminal-drain' if guarded_worker else '; sends=1; stopped=true; queued=1; callback-drain-unqualified') for value in ('false','true')]
                    if [line for line in b if line.startswith('containment ')]!=wanted:raise RuntimeError('Session callback containment coverage differs')
                    if any('stop=false' in line for line in b if line.startswith(('recovery ','null_io_recovery '))):raise RuntimeError('Rejected session resumed dispatch')
                if expected_recovery is None:expected_recovery=b
                if b!=expected_recovery:raise RuntimeError('Recovery observations differ across runtimes')
                observations[-1]['recovery_regression']=b
            if digest(tree(runtime)) != runtime_identity:
                raise RuntimeError('Runtime changed during observation')
    if source_hashes != {str(p.relative_to(ROOT)): sha(p) for p in identity_sources}:
        raise RuntimeError('Fixture sources changed during observation')
    if sha(args.jar) != candidate_sha:
        raise RuntimeError('Candidate changed during observation')
    print(json.dumps({'fixture_commit':fixture_commit,'fixture_dirty':fixture_dirty,'tool_sha256':sha(Path(__file__)), 'compiler_tree_sha256': compiler['tree_sha256'],
                      'required_framing_policy':args.framing_policy,'required_invalid_header_policy':args.invalid_header_policy,'required_null_io_policy':args.null_io_policy,'host_machine': platform.machine(), 'macos_version': platform.mac_ver()[0],
                      'original_sha256': sha(original), 'candidate_sha256': candidate_sha,
                      'fixture_sources': {str(p.relative_to(ROOT)): sha(p) for p in identity_sources},
                      'observations': observations,
                      'null_io_recovery_limits':('Six exact null-IO stop variants: close failures, throwing/nonthrowing logger and metadata shutdown. Normal first callback closes once; metadata failure closes only at exit. Successful close clears the inner reference; failed close can be attempted again at exit. One marker event, no reconnect event. Logger owner remains CommunicationsManager, with private dispatchLoop location when worker guards are present. Two callback-throw cases prove stopped dispatch and no later sends, native GUI/disposed AppContext and VM failure completion excluded.' if session_containment else 'Six exact null-IO recovery variants: close failures, throwing/nonthrowing logger and metadata shutdown. Normal first callback has one old-source close; metadata failure has zero then closes once after queued callbacks and run exit. Logger owner remains CommunicationsManager, with private dispatchLoop location when worker guards are present through the existing FQCN boundary.') if args.recovery and null_io_policy else None,
                      'terminal_io_scope':'Feature selection and retained 143-line security-marker regression with intentional ordinary-worker-fault stop; non-prefix IO and additional worker-failure qualification are in check_transport, not this matrix.','required_stop_lock_order':args.stop_lock_order,'required_connect_failure_stop':args.connect_failure_stop,'required_sync_preenqueue':args.sync_preenqueue,'required_worker_failure_stop':args.worker_failure_stop,'required_terminal_io_policy':args.terminal_io_policy,'required_session_containment':args.session_containment,'recovery_limits': ('Exact security markers stop local dispatch before logging/callbacks; all 15 violations block queued mutation/restart; two throwing-callback cases prove no later sends and, when worker guards are present, terminal queued callback attempts; callback exceptions are contained. No new-session UI procedure qualified. ' if session_containment else '')+'Actual dispatch/send with bounded memory replies; '+('15 security violations (13 prior cases plus colonless/empty-name headers)' if invalid_header_policy else '13 security violations (8 prior bounds/length cases plus 5 framing cases)' if framing_policy else '8 security violations')+' plus parse gates, persistent/nonpersistent close IO/runtime failures, marker identity, retained callback contexts, '+('blocked queued writes after session stop' if session_containment else 'distinct next-command send on fresh connection')+', logger throw containment, metadata failure shutdown and ordinary logger ownership with explicit private dispatchLoop location change for the guarded wrapper. Malformed-header flag/codec/logger-throw variants use the colonless case; empty-name receives pair and six direct close variants. Invalid-address callback injects reconnection; no TCP or real retry/controller qualification.' if args.recovery else None,
                      'header_limits': '174762 bounded short-input/EOF constructor cases; candidate counters/phase independently compared with original readLine behavior on isolated Unsafe shells; exact fixed malformed-header markers normalized only for parse/consumption parity. Exact line/count/aggregate boundaries, fresh per-response budget and body pass-through above 1 MiB. Three candidate-only overlimit rejections; no real socket framing or recovery qualification.' if args.headers else None,
                      'menu_limits': 'Real interface proxies and API metadata; synthetic backend callbacks only. No native singleton registration, real event construction or AppleEvent delivery.' if args.menus else None,
                      'limits': 'Base parity covers headless serializer and simple HTTP 200 Content-Length replay. Additional flagged fixtures qualify only their separately recorded scopes. No GUI/Aqua, JNI, app launcher, preferences, controller, or physical Intel Mac qualification. x86_64 JVM on the recorded arm64 host uses Rosetta; translation status is inferred, not separately probed.'}, indent=2))


if __name__ == '__main__':
    main()
