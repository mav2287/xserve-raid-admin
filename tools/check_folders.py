#!/usr/bin/env python3
"""Verify the single changed MRJ method and exercise it without opening any UI."""
import argparse
import json
from pathlib import Path
import re
import tempfile
from audit_support import ROOT, verify_python, verify_jdk, run_jdk, sha
from baseline import verify_original
from inventory import disassemble_entries


def normalized_members(disassembly):
    members = {}
    current = None
    in_exceptions = False
    for line in disassembly.splitlines():
        if line.startswith('public class '):
            members['class declaration'] = [line]
        if re.match(r'^  \S.*[;{]$', line):
            in_exceptions = False
            current = line.strip()
            members[current] = []
        elif current and line.strip() == 'Exception table:':
            in_exceptions = True
        elif current and in_exceptions and line.strip():
            members[current].append(line.strip())
        elif current and re.match(r'^\s+\d+:', line):
            instruction = re.sub(r'^\s+\d+:\s*', '', line)
            if '//' in instruction:
                op, comment = instruction.split('//', 1)
                instruction = op.split()[0] + ' ' + comment.strip()
            members[current].append(instruction)
    return members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--jar', required=True, type=Path)
    args = parser.parse_args()
    verify_python(); lock = verify_jdk(args.jdk)
    original = ROOT / 'original/RAID_Admin_original.jar'; verify_original(original)
    entry = ['com/apple/mrj/MRJFileUtils.class']
    old = normalized_members(disassemble_entries(args.jdk, original, entry))
    new = normalized_members(disassemble_entries(args.jdk, args.jar, entry))
    if old.keys() != new.keys():
        raise RuntimeError('MRJFileUtils ABI changed')
    changed = [name for name in old if old[name] != new[name]]
    if changed != ['public static java.io.File findFolder(com.apple.mrj.MRJOSType) throws java.io.FileNotFoundException;']:
        raise RuntimeError('Unexpected MRJFileUtils method changes')
    sources = [ROOT / 'tests/java/FolderProbe.java', ROOT / 'tests/java/fixture/OfflineGuard.java']
    results = []
    with tempfile.TemporaryDirectory(prefix='raid-folder-') as tmp:
        run_jdk(args.jdk, 'javac', ['-source','8','-target','8','-cp',str(original),'-d',tmp] + [str(p) for p in sources])
        for jar, fixed in [(original, 'false'), (args.jar, 'true')]:
            results.append(run_jdk(args.jdk, 'java', ['-Djava.awt.headless=true','-Duser.home=' + tmp,
                '-cp',tmp + ':' + str(jar.resolve()),'FolderProbe',fixed], timeout=20).strip())
    print(json.dumps({'original_sha256':sha(original),'candidate_sha256':sha(args.jar),
        'jdk_tree_sha256':lock['tree_sha256'],'fixture_sources':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'changed_methods':changed,'results':results,
        'limits':'Used folder lookup only. Callers catalogued separately in audit/static-inventory.json. Java class-file target intentionally raised to Java 8; GUI workflows not qualified.'},indent=2))

if __name__ == '__main__': main()
