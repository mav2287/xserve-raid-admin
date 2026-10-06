#!/usr/bin/env python3
"""Inventory logging-level/configuration calls across every original JAR class."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from audit_support import ROOT, verify_jdk, verify_python, sha
from baseline import verify_original
from inventory import disassemble_entries, parse_bytecode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    args = parser.parse_args(); verify_python(); lock = verify_jdk(args.jdk)
    jar = ROOT/'original/RAID_Admin_original.jar'; verify_original(jar)
    with zipfile.ZipFile(jar) as archive:
        entries = [n for n in archive.namelist() if n.endswith('.class')]
        config = archive.read('log4j.properties')
    text = '\n'.join(disassemble_entries(args.jdk,jar,entries[i:i+150]) for i in range(0,len(entries),150))
    methods,_ = parse_bytecode(text)
    rows = []
    for method in methods:
        if not method['class'] or method['class'].startswith('org.apache.log4j.'): continue
        calls = [c for c in method['calls'] if 'org/apache/log4j/' in c and any(t in c for t in
                 ['isEnabled','isDebugEnabled','isInfoEnabled','getEffectiveLevel','getLevel:',
                  'getPriority:','getChainedPriority:','reset','shutdown','Configurator','setLevel:','setPriority:','addAppender:','configure:',
                  'removeAllAppenders:','setAdditivity:'])]
        if calls: rows.append({'class':method['class'],'method':method['signature'],'calls':calls})
    if not entries or not methods or not rows: raise ValueError('Incomplete logging inventory')
    print(json.dumps({'original_sha256':sha(jar),'jdk_tree_sha256':lock['tree_sha256'],
        'tool_sha256':sha(Path(__file__)), 'disassembler_sha256':sha(ROOT/'tools/inventory.py'),
        'searched_call_patterns':['isEnabled','isDebugEnabled','isInfoEnabled','getEffectiveLevel','getLevel:','getPriority:','getChainedPriority:','reset','shutdown','Configurator','setLevel:','setPriority:','addAppender:','configure:','removeAllAppenders:','setAdditivity:'],
        'owner_match':'Any org/apache/log4j owner, including Category, Logger, LogManager and configurators',
        'class_count':len(entries),'method_count':len(methods),
        'scope':'All original JAR classes; log4j internals excluded from caller rows; static direct-call inventory only',
        'log4j_config_sha256':hashlib.sha256(config).hexdigest(),
        'active_config_lines':[line for line in config.decode().splitlines() if line.strip() and not line.lstrip().startswith('#')],
        'level_or_configuration_calls':rows,
        'limits':'Reflection, external configuration, dynamically loaded classes and full logging-event execution are not characterized. No logging configuration was changed or application launched.'},indent=2,sort_keys=True))


if __name__ == '__main__': main()
