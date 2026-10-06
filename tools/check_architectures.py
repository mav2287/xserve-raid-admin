#!/usr/bin/env python3
"""Observe existing runtime architectures without starting RAID Admin or networking."""
import argparse
import json
import platform
import re
from pathlib import Path
import subprocess
import tempfile

from audit_support import ROOT, digest, isolated_env, run_jdk, sha, tree, verify_jdk, verify_python
from baseline import verify_original


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
    parser.add_argument('--headers', action='store_true', help='Compare bounded header corpus and candidate-only limits')
    args = parser.parse_args()
    verify_python()
    compiler = verify_jdk(args.compiler)
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    if args.jar.is_symlink() or not args.jar.is_file():
        raise ValueError('Candidate must be a regular file, not a symlink')
    candidate_sha = sha(args.jar)
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
    sources = list(dict.fromkeys(sources))
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    observations = []
    expected_parser = None
    expected_headers = None
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
                resource_flags=['-Xmx64m','-Xss1m'] if entry=='com.apple.xsr.net.HeaderObservation' else []
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
            if digest(tree(runtime)) != runtime_identity:
                raise RuntimeError('Runtime changed during observation')
    if source_hashes != {str(p.relative_to(ROOT)): sha(p) for p in sources}:
        raise RuntimeError('Fixture sources changed during observation')
    if sha(args.jar) != candidate_sha:
        raise RuntimeError('Candidate changed during observation')
    print(json.dumps({'compiler_tree_sha256': compiler['tree_sha256'],
                      'host_machine': platform.machine(), 'macos_version': platform.mac_ver()[0],
                      'original_sha256': sha(original), 'candidate_sha256': candidate_sha,
                      'fixture_sources': {str(p.relative_to(ROOT)): sha(p) for p in sources},
                      'observations': observations,
                      'header_limits': '174762 bounded short-input/EOF constructor cases; candidate counters and phase independently compared with unchanged private parseHeaders/readLine on isolated Unsafe shells. Exact line/count/aggregate boundaries, fresh per-response budget and body pass-through above 1 MiB. Three candidate-only overlimit rejections; no real socket framing or recovery qualification.' if args.headers else None,
                      'menu_limits': 'Real interface proxies and API metadata; synthetic backend callbacks only. No native singleton registration, real event construction or AppleEvent delivery.' if args.menus else None,
                      'limits': 'Headless serializer and simple HTTP 200 Content-Length replay only. No GUI/Aqua, JNI, app launcher, preferences, ACP transport, controller, or physical Intel Mac qualification. x86_64 JVM on the recorded arm64 host uses Rosetta; translation status is inferred, not separately probed.'}, indent=2))


if __name__ == '__main__':
    main()
