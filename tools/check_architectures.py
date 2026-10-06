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
    observations = []
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
            def run(jar, entry, *arguments):
                # These flags work on both Java 8 and 11. This is a runtime observation,
                # separate from the Java-8-only reproducible build environment.
                command = [str(runtime / 'bin/java')] + extension_flags + ['-Djava.awt.headless=true', '-Duser.home=' + tmp,
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
            if digest(tree(runtime)) != runtime_identity:
                raise RuntimeError('Runtime changed during observation')
    if sha(args.jar) != candidate_sha:
        raise RuntimeError('Candidate changed during observation')
    print(json.dumps({'compiler_tree_sha256': compiler['tree_sha256'],
                      'host_machine': platform.machine(), 'macos_version': platform.mac_ver()[0],
                      'original_sha256': sha(original), 'candidate_sha256': candidate_sha,
                      'fixture_sources': {str(p.relative_to(ROOT)): sha(p) for p in sources},
                      'observations': observations,
                      'menu_limits': 'Real interface proxies and API metadata; synthetic backend callbacks only. No native singleton registration, real event construction or AppleEvent delivery.' if args.menus else None,
                      'limits': 'Headless serializer and simple HTTP 200 Content-Length replay only. No GUI/Aqua, JNI, app launcher, preferences, ACP transport, controller, or physical Intel Mac qualification. x86_64 JVM on the recorded arm64 host uses Rosetta; translation status is inferred, not separately probed.'}, indent=2))


if __name__ == '__main__':
    main()
