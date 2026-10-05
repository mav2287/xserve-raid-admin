#!/usr/bin/env python3
"""Run real ACP and dispatch code against memory-only transport; no sockets or GUI."""
import argparse
import json
from pathlib import Path
import tempfile
import zipfile
from audit_support import ROOT, verify_jdk, verify_python, run_jdk, sha
from baseline import verify_original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('jars', nargs='+', type=Path)
    args = parser.parse_args()
    verify_python(); lock = verify_jdk(args.jdk)
    original = ROOT / 'original/RAID_Admin_original.jar'; verify_original(original)
    sources = [ROOT / p for p in ('tests/java/fixture/OfflineGuard.java',
               'tests/java/com/apple/xsr/net/TransportObservation.java', 'patches/sun/io/MalformedInputException.java')]
    observations = []
    with tempfile.TemporaryDirectory(prefix='raid-transport-') as tmp:
        run_jdk(args.jdk, 'javac', ['-source','8','-target','8','-cp',str(original),'-d',tmp] + [str(p) for p in sources])
        shim = Path(tmp) / 'sun/io/MalformedInputException.class'
        for jar in [original] + args.jars:
            with zipfile.ZipFile(jar) as archive:
                if jar != original and archive.read('sun/io/MalformedInputException.class') != shim.read_bytes():
                    raise RuntimeError('Fixture shim differs from candidate shim')
            result = run_jdk(args.jdk, 'java', ['-Djava.awt.headless=true','-Duser.home=' + tmp,
                '-cp',tmp + ':' + str(jar.resolve()),'com.apple.xsr.net.TransportObservation'], timeout=20)
            observations.append({'jar_sha256': sha(jar), 'results': result.splitlines()})
    if any(o['results'] != observations[0]['results'] for o in observations):
        raise RuntimeError('Transport observations differ')
    print(json.dumps({'jdk_tree_sha256': lock['tree_sha256'],
        'fixture_sources': {str(p.relative_to(ROOT)): sha(p) for p in sources}, 'observations': observations,
        'limits': 'Original queue and ACP send with memory HttpConnection; Unsafe bypasses transport/model constructors. Reconnection injected through invalid-address callback. Exception shim supplied to original and candidate; candidate bytes verified identical. Firmware stream test invokes send twice directly, not via queue. No TCP, hardware, polling, or real reconnect/backoff qualification.'}, indent=2))

if __name__ == '__main__': main()
