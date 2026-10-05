#!/usr/bin/env python3
"""Compare synthetic, credential-free in-memory HTTP serialization across JARs."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from baseline import ROOT, verify_original


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jdk', type=Path, required=True)
    p.add_argument('jars', nargs='+', type=Path)
    args = p.parse_args()
    original = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(original)
    with tempfile.TemporaryDirectory(prefix='raid-parity-') as tmp:
        source = ROOT / 'tests/java/com/apple/xsr/net/OfflineParity.java'
        subprocess.run([str(args.jdk / 'bin/javac'), '-source', '8', '-target', '8', '-cp', str(original), '-d', tmp, str(source)], check=True)
        results = []
        for jar in [original] + args.jars:
            # No app entry point and no preferences; JVM refuses all sockets.
            result = subprocess.run([str(args.jdk / 'bin/java'), '-Djava.awt.headless=true', '-cp', tmp + ':' + str(jar.resolve()), 'com.apple.xsr.net.OfflineParity'], capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise SystemExit('Offline harness failed; inspect fixture locally (no arbitrary error payload emitted)')
            results.append(result.stdout)
        if any(result != results[0] for result in results):
            raise SystemExit('FAIL: synthetic serialization or replay differs')
        print(results[0], end='')
        print('PASS: all tested JARs match the immutable reference under this JDK')


if __name__ == '__main__':
    main()
