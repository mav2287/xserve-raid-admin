#!/usr/bin/env python3
"""Generate static inventory from the hash-verified JAR without running app code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
import tempfile
from audit_support import verify_jdk, verify_python, run_jdk
from baseline import ROOT, verify_original, tree_hash



def parse_bytecode(bytecode):
    methods = []
    parents = {}
    current = None
    cls = None
    for line in bytecode.splitlines():
        match = re.match(r'^(?:[\w]+ )*(?:class|interface) ([\w.$]+).*\{$', line)
        if match:
            cls = match[1]
            parents[cls] = re.findall(r'(?:extends|implements) ([\w.$]+)', line)
            current = None
        if re.match(r'^  [^ ].*\(.*\).*;$', line) or line == '  static {};':
            current = {'class': cls, 'signature': line.strip(), 'calls': [], 'strings': []}
            methods.append(current)
        if current:
            if '// Method ' in line or '// InterfaceMethod ' in line:
                current['calls'].append(line.split('// ', 1)[1])
            if '// String ' in line:
                current['strings'].append(line.split('// String ', 1)[1])
    request_types = {'com.apple.xsr.net.RequestMessage'}
    while True:
        added = {c for c, bases in parents.items() if set(bases) & request_types}
        if added <= request_types:
            break
        request_types |= added
    return methods, request_types


def request_sites(methods, request_types):
    rows = []
    for method in methods:
        for call in method['calls']:
            member = call.split(' ', 1)[1].split(':', 1)[0]
            owner, _, name = member.rpartition('.')
            if not owner:
                owner, name = method['class'].replace('.', '/'), member
            owner = owner.replace('/', '.')
            kind = None
            if owner in {'com.apple.xsr.net.MessageFactory', 'com.apple.xsr.net.AcpxMessageFactory'} and name.startswith('new'):
                kind = 'factory'
            elif owner in request_types and name == '"<init>"':
                kind = 'request-constructor'
            elif (owner == 'com.apple.xsr.net.AcpxConnection' and name == 'send') or (owner in {'com.apple.xsr.som.RaidSystem', 'com.apple.xsr.net.CommunicationsManager'} and name.startswith('post')):
                kind = 'transport-sink'
            if kind:
                rows.append({'class': method['class'], 'signature': method['signature'],
                             'call': call, 'kind': kind, 'initiation': 'unreviewed'})
    if not rows or not any(r['kind'] == 'factory' for r in rows):
        raise ValueError('Empty request call-site inventory')
    return rows


def disassemble_entries(jdk, jar, entries, *, verbose=False):
    # Explicit class-file paths avoid javap resolving a platform class with the same name.
    with tempfile.TemporaryDirectory(prefix='raid-bytecode-') as tmp:
        paths = []
        with zipfile.ZipFile(jar) as archive:
            for name in entries:
                if name.startswith('/') or '..' in Path(name).parts:
                    raise ValueError('Unsafe class entry')
                target = Path(tmp) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
                paths.append(str(target))
        return run_jdk(jdk, 'javap', ['-p', '-c', '-constants'] + (['-v'] if verbose else []) + paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    args = parser.parse_args()
    verify_python()
    args.jdk = args.jdk.absolute()
    verify_jdk(args.jdk)
    jar = ROOT / 'original/RAID_Admin_original.jar'
    verify_original(jar)
    out = ROOT / 'audit'
    with zipfile.ZipFile(jar) as z:
        hashes = {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
        classes = sorted(n[:-6].replace('/', '.') for n in hashes if n.endswith('.class') and n.startswith(('com/apple/', 'com/chaotic/')))
        bytecode = disassemble_entries(args.jdk, jar, [c.replace('.', '/') + '.class' for c in classes])
        methods, request_types = parse_bytecode(bytecode)
        sites = request_sites(methods, request_types)
        # Flag archive names that also occur in runtime archives. Hashes here describe archive bytes.
        runtime_names = set()
        for runtime_jar in sorted(args.jdk.rglob('*.jar')):
            with zipfile.ZipFile(runtime_jar) as runtime_archive:
                runtime_names.update(runtime_archive.namelist())
        collisions = sorted(n for n in hashes if n.endswith('.class') and n in runtime_names)
        (out / 'request-call-sites.json').write_text(json.dumps(sites, indent=2) + '\n')
        # Preserve literals only for the request factory and firmware request definitions.
        for m in methods:
            if not m['class'].startswith('com.apple.xsr.net.AcpxMessageFactory') and m['class'] != 'com.apple.xsr.net.UpdateFirmwareRequest':
                del m['strings']
        result = {'scope': 'all com.apple and com.chaotic classes; static presence is not proof of reachability or functionality', 'jar_sha256': hashlib.sha256(jar.read_bytes()).hexdigest(), 'class_count': len(classes), 'classes': classes, 'methods': methods, 'entry_hashes': hashes, 'disassembly_source': 'explicit extracted class-file bytes', 'platform_name_collisions': collisions}
        (out / 'static-inventory.json').write_text(json.dumps(result, indent=2) + '\n')
        factory = [m for m in methods if m['class'] == 'com.apple.xsr.net.AcpxMessageFactory' and re.search(r'\bnew\w+Request\(', m['signature'])]
        protocol = ['# Static controller-operation catalog', '', 'Generated by `tools/inventory.py` from the verified original JAR. All overloads are included. Literals are evidence, not a substitute for request schemas or hardware tests. RPC names beginning `/raid/` or `/system/` are carried inside POST `/cgi-bin/perform`, not separate HTTP endpoints.', '', '| Factory signature | String literals (command, endpoint, parameter names, defaults) |', '|---|---|']
        for m in factory:
            protocol.append('| `' + m['signature'].replace('|', '\\|') + '` | ' + '; '.join('`' + s.replace('|','\\|').replace('`','') + '`' for s in m.get('strings',[])) + ' |')
        (out / 'CONTROLLER-OPERATIONS.md').write_text('\n'.join(protocol) + '\n')
        ui = ['# Static UI and CLI inventory', '', 'Every com.apple.xsr class is listed, including anonymous listeners and non-UI model/transport classes so hidden paths remain visible. The JSON companion records every declared method and call site. This is a complete static class inventory, not a completed behavioral inventory.', '', '## Named actions', '']
        ui += ['- `' + c + '`' for c in classes if c.startswith('com.apple.xsr.') and c.endswith('Action')]
        ui += ['', '## UI-to-request call sites', '', '| Class / method | Factory call |', '|---|---|']
        for site in sites:
            ui.append('| `' + site['class'] + ' ' + site['signature'] + '` | `' + site['call'] + '` (' + site['kind'] + '; initiation unreviewed) |')
        ui += ['', '## Complete application class list', ''] + ['- `' + c + '`' for c in classes if c.startswith('com.apple.xsr.')]
        ui += ['', '## English resource keys', '', 'Values and all locale variants remain immutable JAR resources. Keys enumerate labels/messages and do not prove a function is reachable.', '']
        data = z.read('com/apple/xsr/resources/GlobalResources.properties').decode('iso-8859-1')
        keys = sorted(set(line.split('=',1)[0].strip() for line in data.splitlines() if '=' in line and not line.lstrip().startswith('#')))
        ui += ['- `' + k.replace('`','') + '`' for k in keys]
        (out / 'UI-INVENTORY.md').write_text('\n'.join(ui) + '\n')
        groups = [
            ('Apple application and support', ('com/apple/',), '1.5.1 / 1.5.1GMc5', 'Apple proprietary; redistribution unresolved'),
            ('Chaotic support', ('com/chaotic/',), None, 'NOASSERTION'),
            ('BrowserLauncher', ('edu/stanford/ejalbert/',), None, 'NOASSERTION'),
            ('JmDNS', ('javax/jmdns/',), '0.2', 'NOASSERTION'),
            ('Xerces and DOM implementations', ('org/apache/xerces/', 'org/apache/html/', 'org/apache/wml/'), '2.0.0 (Xerces)', 'NOASSERTION'),
            ('Xalan and XML/XPath support', ('org/apache/xalan/', 'org/apache/xml/', 'org/apache/xpath/'), '2.3.0 (Xalan)', 'NOASSERTION'),
            ('Log4j', ('org/apache/log4j/',), '1.x; exact version unresolved', 'NOASSERTION'),
            ('BCEL', ('org/apache/bcel/',), None, 'Apache-1.1; BCEL.LICENSE.txt'),
            ('Regexp', ('org/apache/regexp/',), None, 'Apache-1.1; regexp.LICENSE.txt'),
            ('JLex', ('JLex/',), None, 'custom notice; JLex.LICENSE.txt'),
            ('Java CUP', ('java_cup/',), '0.10j', 'custom notice; java_cup.LICENSE.txt, runtime.LICENSE.txt'),
            ('XML API classes', ('javax/xml/', 'org/w3c/', 'org/xml/'), None, 'NOASSERTION'),
        ]
        components=[]
        for name,prefixes,version,license_name in groups:
            files={n:h for n,h in hashes.items() if n.startswith(prefixes)}
            components.append({'name':name,'version':version,'license_evidence':license_name,'files':files,'component_tree_sha256':tree_hash(files)})
        known={n for c in components for n in c['files']}
        components.append({'name':'Other resources and notices','version':None,'license_evidence':'NOASSERTION','files':{n:h for n,h in hashes.items() if n not in known}})
        sbom={'format':'project inventory schema 1 (not asserted SPDX/CycloneDX conformant)','scope':'immutable JAR entries; compiler and packaged runtimes separately inventoried in jdk-lock.json and runtime-lock.json','hash_definition':'component hash = SHA256 canonical JSON relative entry to SHA256; not upstream distribution checksum','jar_sha256':result['jar_sha256'],'components':components,'acquisition_evidence':'apple-distribution-acquisition.json'}
        (out / 'sbom.json').write_text(json.dumps(sbom,indent=2)+'\n')
        print(json.dumps({'classes':len(classes),'methods':len(methods),'factory_overloads':len(factory),'ui_resource_keys':len(keys),'jar_entries':len(hashes),'request_call_sites':len(sites),'platform_name_collisions':len(collisions)}))


if __name__ == '__main__': main()
