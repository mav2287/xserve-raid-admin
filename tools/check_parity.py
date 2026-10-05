#!/usr/bin/env python3
"""Compare synthetic, credential-free in-memory HTTP serialization across JARs."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from baseline import ROOT, verify_original
from audit_support import verify_jdk, verify_python, run_jdk, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jdk', type=Path, required=True)
    p.add_argument('jars', nargs='+', type=Path)
    args = p.parse_args()
    verify_python()
    args.jdk = args.jdk.absolute()
    lock = verify_jdk(args.jdk)
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    with tempfile.TemporaryDirectory(prefix='raid-parity-') as tmp:
        source = ROOT / 'tests/java/com/apple/xsr/net/OfflineParity.java'
        run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(original), '-d', tmp, str(source)])
        results = []
        for jar in [original] + args.jars:
            # No app entry point and no preferences; JVM refuses all sockets.
            result = run_jdk(args.jdk, 'java', ['-Djava.awt.headless=true', '-cp', tmp + ':' + str(jar.resolve()), 'com.apple.xsr.net.OfflineParity'], timeout=30)
            results.append(result)
        if any(result != results[0] for result in results):
            raise SystemExit('FAIL: synthetic serialization or replay differs')
        print('JDK tree SHA256:', lock['tree_sha256'])
        for jar in [original] + args.jars:
            print('JAR SHA256:', sha(jar))
        print(results[0], end='')
        print('PASS: serializer/HTTP-parser smoke checks match; ACP, handlers, retries and hardware remain outside this fixture')


if __name__ == '__main__':
    main()
