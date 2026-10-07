#!/usr/bin/env python3
"""Static exception/message consumer inventory; no application execution."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from audit_support import ROOT,sha,verify_jdk,verify_python,isolated_env
from verify_builds import entries
from class_patch import ClassFile,u2
from inventory import disassemble_entries
TYPES={'java/io/IOException','java/io/InterruptedIOException','java/net/UnknownHostException',
       'java/net/ConnectException','java/net/NoRouteToHostException','java/net/SocketTimeoutException',
       'java/net/BindException','java/net/SocketException'}
def state():
    return (subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),
            bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
def scan(jdk,jar,reference,output):
    verify_python();compiler=verify_jdk(jdk);initial=state();before=sha(jar);reference_sha=sha(reference)
    output=output.resolve()
    if not output.is_relative_to((ROOT/'build').resolve()) or output.suffix!='.json' or output.exists() or output.with_suffix('.javap').exists():raise ValueError('New ignored build JSON required')
    expected=json.loads((ROOT/'audit/expected-build.json').read_text())['expected']['files']['Contents/Resources/RAID_Admin.jar']
    if before!=expected or reference_sha!='202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd':raise ValueError('Anchored inventory artifacts differ')
    sources=[ROOT/n for n in ('tools/socket_configuration_consumers.py','tools/class_patch.py',
        'tools/inventory.py','tools/audit_support.py','tools/verify_builds.py','tools/baseline.py',
        'tools/socket_configuration_patch.py','tools/connection_publication_patch.py','audit/jdk-lock.json','audit/python-lock.json','audit/expected-build.json')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
    actual,old=entries(jar),entries(reference);types=[];messages=[]
    classes=sorted(n for n in actual if n.endswith('.class'))
    for name in classes:
        c=ClassFile(actual[name]);found=set();refs=[]
        for tag,data in c.pool.values():
            if tag==7:
                value=c.text(u2(data,0))
                if value in TYPES:found.add(value)
            if tag in (10,11):
                owner=c.text(u2(c.pool[u2(data,0)][1],0))
                nat=c.pool[u2(data,2)][1];method=c.text(u2(nat,0));descriptor=c.text(u2(nat,2))
                if method=='getMessage':refs.append({'owner':owner,'descriptor':descriptor})
        if found:types.append({'entry':name,'types':sorted(found)})
        if refs:messages.append({'entry':name,'references':refs})
    selected=sorted({r['entry'] for r in types}|{r['entry'] for r in messages if r['entry'].startswith('com/apple/')})
    text=disassemble_entries(jdk,jar,selected);invocations=[];owner=method=None
    for line in text.splitlines():
        declared=re.search(r'(?:class|interface) ([^ ]+)',line)
        if declared and not line.startswith(' '):owner=declared[1]
        if re.match(r'^  [^\s\d].*\(.*\).*;',line):method=line.strip()
        call=re.search(r'^\s+(\d+):\s+invoke\S*.*// (?:InterfaceMethod|Method) ((?:[^ ]*\.)?getMessage):\(\)Ljava/lang/String;',line)
        if call:invocations.append({'class':owner,'method':method,'offset':int(call[1]),'target':call[2]})
    verify_jdk(jdk)
    if state()!=initial or hashes!={str(p.relative_to(ROOT)):sha(p) for p in sources} or sha(jar)!=before or sha(reference)!=reference_sha:raise ValueError('Inventory artifact changed')
    output.with_suffix('.javap').write_text(text)
    output.write_text(json.dumps({'fixture_commit':initial[0],'fixture_dirty':initial[1],'jar_sha256':before,'reference_jar_sha256':reference_sha,
        'class_entries_scanned':len(classes),'exception_type_classes':types,
        'getMessage_reference_classes':messages,'selected_class_entries':selected,
        'selected_disassembly_sha256':sha(output.with_suffix('.javap')),
        'message_invocations':invocations,
        'changed_entries':sorted(n for n in actual.keys()|old.keys() if actual.get(n)!=old.get(n)),
        'compiler_tree_sha256':compiler['tree_sha256'],'sources':hashes,
        'scope':'All candidate class constant pools scanned. Full javap for every standard setup exception-type reference and every Apple getMessage reference class. String-returning invocation sites include unqualified same-class calls. Other library references listed without complete disassembly. This is static source evidence; reachability, native UI/CLI rendering and external extensions remain unqualified.'},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('candidate',type=Path);a=p.parse_args();scan(a.jdk,a.candidate,a.reference,a.output)
