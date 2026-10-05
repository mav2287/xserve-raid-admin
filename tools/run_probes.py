#!/usr/bin/env python3
"""Run bounded, socket-denied observation fixtures using the locked toolchain."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from audit_support import ROOT, verify_python, verify_jdk, run_jdk, sha
from baseline import verify_original


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jdk', required=True, type=Path)
    p.add_argument('--jar', required=True, type=Path)
    p.add_argument('--probe', choices=['ClassOriginProbe','XmlObservation','ApiProbe'], required=True)
    args = p.parse_args()
    verify_python(); lock = verify_jdk(args.jdk)
    original = ROOT / 'original/RAID_Admin_original.jar'; verify_original(original)
    source = ROOT / 'tests/java' / (args.probe + '.java')
    with tempfile.TemporaryDirectory(prefix='raid-probe-') as tmp:
        run_jdk(args.jdk, 'javac', ['-source','8','-target','8','-cp',str(original),'-d',tmp,str(source)])
        result = run_jdk(args.jdk, 'java', ['-Djava.awt.headless=true','-cp',tmp + ':' + str(args.jar.absolute()),args.probe],timeout=30)
    print(json.dumps({'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                      'fixture_sha256':sha(source),'jar_sha256':sha(args.jar),'jdk_tree_sha256':lock['tree_sha256'],
                      'isolation':'Java8 socket guard; no GUI; ambient JVM variables excluded','result':result.splitlines()},indent=2))

if __name__ == '__main__': main()
