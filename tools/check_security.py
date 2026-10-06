#!/usr/bin/env python3
"""Differential XML and request-format tests with JVM verification and no external IO."""
import argparse
import json
from pathlib import Path
import re
import tempfile
import zipfile
from audit_support import ROOT, verify_python, verify_jdk, run_jdk, sha
from baseline import verify_original
from class_patch import TARGETS
from verify_builds import check_artifact, EXPECTED
from inventory import disassemble_entries


def plain_constructor_code(text):
    """The original constructor has only a frame line and instructions."""
    code = re.search(r'^    Code:\n(.*?)(?=^    \S|\Z)', text, re.M | re.S)[1]
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    if not lines or not re.fullmatch(r'stack=\d+, locals=\d+, args_size=\d+', lines[0]) or any(not re.fullmatch(r'\d+:\s+.*', line) for line in lines[1:]):
        raise ValueError('Unexpected constructor Code table or attribute')


def independent_preservation(jdk, original, candidate, entry, target, descriptor):
    before, after = [disassemble_entries(jdk, jar, [entry], verbose=True) for jar in (original,candidate)]
    def sections(text):
        header, body = text.split('Constant pool:\n',1)
        pool, members = body.split('\n{\n',1)
        declarations = re.split(r'(?=^  \S.*[;{]$)', members, flags=re.M)
        kept = []
        selected = []
        for part in declarations:
            constructor = target=='getBody' and re.match(r'^  com\.apple\.xsr\.net\.HttpResponse\(',part)
            if constructor: part = re.sub(r'^    Code:\n.*?(?=^    \S|^}|\Z)', '', part, flags=re.M | re.S)
            if re.match(r'^  [^\n]*\b' + target + r'\(', part) and ('    descriptor: ' + descriptor + '\n') in part:
                selected.append(part)
                part = re.sub(r'^    Code:\n.*?(?=^    \S|^}|\Z)', '', part, flags=re.M | re.S)
            kept.append(part)
        if len(selected) != 1: raise ValueError('Independent target descriptor lookup failed')
        identity = re.findall(r'^  (?:minor version|major version|flags|this_class|super_class|interfaces):.*$',header,re.M)
        identity += re.findall(r'^(?:\w+ )*(?:class|interface) .+$',header,re.M)
        return identity,pool.splitlines(),kept,selected[0]
    old,new = sections(before),sections(after)
    if old[0] != new[0] or '  major version: 47' not in old[0]:
        raise ValueError('Independent class identity/version check failed')
    if new[1][:len(old[1])] != old[1] or old[2] != new[2]:
        raise ValueError('Independent constant pool/non-target disassembly check failed')
    if target in ('run','send'):
        a,b=old[3],new[3]
        if target=='run':
            window=re.findall(r'^\s+(\d+):\s+(.*)$',b,re.M)
            window=[(int(offset),rest) for offset,rest in window if 464<=int(offset)<474]
            expected=[(464,'aload_0'),(465,'aload         5')]
            if window[:2]!=expected or len(window)!=7 or window[2][0]!=467 or not re.fullmatch(r'invokestatic\s+#\d+\s+// Method compat/RejectionRecovery.report:\(Lcom/apple/xsr/net/CommunicationsManager;Ljava/lang/Exception;\)V',window[2][1]) or window[3:]!=[(i,'nop') for i in range(470,474)]:
                raise ValueError('Independent recovery report window differs')
            def mask(text):return re.sub(r'^\s+(?:46[4-9]|47[0-3]):.*\n','',text,flags=re.M)
            if mask(a)!=mask(b):raise ValueError('Run differs outside report window')
        else:
            appended=re.findall(r'^\s+(\d+):\s+(.*)$',b,re.M)[-3:]
            if len(appended)!=3 or appended[0]!=('392','aload_0') or appended[2]!=('396','athrow') or appended[1][0]!='393' or not re.fullmatch(r'invokestatic\s+#\d+\s+// Method compat/RejectionRecovery.sendFailure:\(Ljava/lang/Throwable;Lcom/apple/xsr/net/AcpxConnection;\)Ljava/lang/Throwable;',appended[1][1]):raise ValueError('Independent send handler differs')
            row=r'^\s+32\s+271\s+392\s+Class compat/UntrustedResponseException\n'
            if len(re.findall(row,b,re.M))!=1:raise ValueError('Marker handler row missing/duplicate')
            masked=re.sub(row,'',b,flags=re.M)
            masked=re.sub(r'^\s+(?:392|393|396):.*\n','',masked,flags=re.M)
            if masked!=a:raise ValueError('Send differs outside handler/exception row')
        return
    if target == 'getBody':
        old_lines,new_lines=old[3].splitlines(),new[3].splitlines()
        if len(old_lines)!=len(new_lines): raise ValueError('Response disassembly length changed')
        changed=[]
        for a,b in zip(old_lines,new_lines):
            if a!=b: changed.append((a,b))
        if len(changed)!=3: raise ValueError('Response changes outside parse and allocation operands')
        for (a,b),offset,operation,owner in zip(changed,(14,23,28),('invokestatic','new','invokespecial'),('Method compat/BoundedResponseBuffer.parseLength:(Ljava/lang/String;)I','class compat/BoundedResponseBuffer','Method compat/BoundedResponseBuffer."<init>":(I)V')):
            if not re.match(r'^\s+'+str(offset)+r': '+operation+r'\s+#\d+\s+// ',b) or owner not in b or ('java/lang/Integer.parseInt' if offset==14 else 'java/io/ByteArrayOutputStream') not in a:
                raise ValueError('Response allocation target differs')
        def ctor(text):
            return re.search(r'^  com\.apple\.xsr\.net\.HttpResponse\(com\.apple\.xsr\.net\.HttpConnection\).*?(?=^  \S|^})',text,re.M|re.S)[0]
        a,b=ctor(before),ctor(after)
        instructions=lambda text:re.findall(r'^\s+(\d+):\s+(.*)$',text,re.M)
        plain_constructor_code(a); plain_constructor_code(b)
        ai,bi=instructions(a),instructions(b)
        expected=[]
        for offset,rest in ai:
            if int(offset)==36:
                added=bi[len(expected)]
                if added[0]!='36' or not re.fullmatch(r'invokestatic\s+#\d+\s+// Method compat/BoundedHeaderStream.wrap:\(Ljava/io/InputStream;\)Ljava/io/InputStream;',added[1]):raise ValueError('Header constructor insertion differs')
                expected.append(added)
            expected.append((str(int(offset)+(3 if int(offset)>=36 else 0)),rest))
        if expected!=bi or re.findall(r'stack=\d+, locals=\d+, args_size=\d+',a)!=re.findall(r'stack=\d+, locals=\d+, args_size=\d+',b) or any(label in text for text in (a,b) for label in ('Exception table:','LineNumberTable:','LocalVariableTable:','StackMapTable:')):
            raise ValueError('Independent constructor preservation failed')
        return
    expected_frame = {'resolveEntity':'stack=2, locals=3, args_size=3', 'getParser':'stack=1, locals=0, args_size=0'}.get(target,'stack=1, locals=1, args_size=1')
    if expected_frame not in new[3] or 'Exception table:' in new[3]:
        raise ValueError('Unexpected target stack/locals/exception table')


def request_override_inventory(jdk, original):
    with zipfile.ZipFile(original) as archive:
        entries = [n for n in archive.namelist() if n.endswith('.class')]
    text = '\n'.join(disassemble_entries(jdk, original, entries[i:i+150]) for i in range(0,len(entries),150))
    parents, overrides = {}, set()
    current = None
    for line in text.splitlines():
        match = re.match(r'^(?:\w+ )*(?:class|interface) ([\w.$]+)(.*)\{$', line)
        if match:
            current = match[1]
            parents[current] = re.findall(r'[\w.$]+', re.sub(r'\b(?:extends|implements)\b','',match[2]))
        if re.match(r'^  (?:\w+ )*java\.lang\.String toString\(\);$',line): overrides.add(current)
    requests = {'com.apple.xsr.net.RequestMessage'}
    while True:
        enlarged = requests | {c for c,bases in parents.items() if requests.intersection(bases)}
        if enlarged == requests: break
        requests = enlarged
    expected = {n[:-6].replace('/','.') for n,(_,method,_) in TARGETS.items() if method == 'toString'}
    if overrides.intersection(requests) != expected: raise ValueError('Uncovered request diagnostic override')
    return {'request_types':len(requests),'diagnostic_overrides':sorted(expected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path); parser.add_argument('--build', required=True, type=Path)
    args = parser.parse_args(); verify_python(); lock = verify_jdk(args.jdk)
    original = ROOT / 'original/RAID_Admin_original.jar'; verify_original(original)
    identity, provenance = check_artifact(args.build)
    if identity != json.loads(EXPECTED.read_text())['expected']:
        raise ValueError('Security candidate differs from reviewed build')
    args.jar = args.build / 'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    request_inventory = request_override_inventory(args.jdk, original)
    helper = disassemble_entries(args.jdk,args.jar,['compat/SafePlistResolver.class'],verbose=True)
    if '  major version: 52' not in helper: raise ValueError('Helper requires unexpected JVM version')
    parser_helper = disassemble_entries(args.jdk,args.jar,['compat/SafePlistParser.class'],verbose=True)
    if '  major version: 52' not in parser_helper: raise ValueError('Parser helper requires unexpected JVM version')
    allocation_helper = disassemble_entries(args.jdk,args.jar,['compat/BoundedResponseBuffer.class'],verbose=True)
    if '  major version: 52' not in allocation_helper or 'ConstantValue: int 16777216' not in allocation_helper or not re.search(r'ldc\s+#\d+\s+// int 16777216',allocation_helper) or 'if_icmple' not in allocation_helper or '// String Response length exceeds limit' not in allocation_helper:
        raise ValueError('Allocation helper version, ceiling or fixed rejection differs')
    constructor = re.search(r'public compat.BoundedResponseBuffer\(int\);.*?    Code:\n(.*?)(?=\n  \S|\n})',allocation_helper,re.S)
    if constructor is None or re.findall(r'^\s+\d+:\s+(\S+)',constructor[1],re.M) != ['aload_0','iload_1','invokestatic','invokespecial','return'] or 'Method checkLength:(I)I' not in constructor[1] or 'java/io/ByteArrayOutputStream."<init>":(I)V' not in constructor[1]:
        raise ValueError('Response size check does not precede superclass allocation')
    header_helper=disassemble_entries(args.jdk,args.jar,['compat/BoundedHeaderStream.class'],verbose=True)
    if '  major version: 52' not in header_helper or not all(re.search(pattern,header_helper) for pattern in (r'ldc\s+#\d+\s+// int 1048576',r'ldc\s+#\d+\s+// int 65536',r'sipush\s+129',r'// String Response headers exceed limit')):
        raise ValueError('Header helper version, budgets or fixed rejection differs')
    recovery_helper=disassemble_entries(args.jdk,args.jar,['compat/RejectionRecovery.class'],verbose=True)
    marker_helper=disassemble_entries(args.jdk,args.jar,['compat/UntrustedResponseException.class'],verbose=True)
    if 'public final class compat.UntrustedResponseException extends java.lang.IllegalArgumentException' not in marker_helper or '  major version: 52' not in marker_helper or '  major version: 52' not in recovery_helper or not all(text in recovery_helper for text in ('public final class compat.RejectionRecovery', 'public static java.lang.Throwable sendFailure(java.lang.Throwable, com.apple.xsr.net.AcpxConnection);', 'descriptor: (Ljava/lang/Throwable;Lcom/apple/xsr/net/AcpxConnection;)Ljava/lang/Throwable;', 'public static void report(com.apple.xsr.net.CommunicationsManager, java.lang.Exception);')):
        raise ValueError('Marker/recovery helper linkage or hierarchy differs')
    verified_methods = {}
    for entry, (_, name, descriptor) in TARGETS.items():
        independent_preservation(args.jdk, original, args.jar, entry, name, descriptor)
        disassembly = disassemble_entries(args.jdk, args.jar, [entry])
        match = re.search(r'^  (?:public|protected) [^\n]*\b' + name + r'\([^\n]*\n(.*?)(?=^  \S|^})', disassembly, re.M | re.S)
        if match is None: raise ValueError('javap did not find patched method')
        operations = re.findall(r'^\s+\d+:\s+(\S+)', match[1], re.M)
        if name in ('run','send'):
            verified_methods[entry]='Exact report window / appended marker handler independently verified, original remainder unchanged'
            continue
        if name == 'getBody':
            verified_methods[entry] = 'Parse operand at 14 and allocation operands at 23 and 28 plus exact static wrapper insertion in constructor; independent complete disassembly comparisons'
            continue
        expected = {'resolveEntity':['aload_1','aload_2','invokestatic','areturn'],'getParser':['invokestatic','areturn']}.get(name,['ldc_w','areturn'])
        if operations != expected: raise ValueError('Independent disassembly differs from intended substitution')
        if name == 'resolveEntity' and ('compat/SafePlistResolver.resolve:' + descriptor) not in match[1]:
            raise ValueError('Resolver delegate differs')
        if name == 'getParser' and ('compat/SafePlistParser.create:' + descriptor) not in match[1]:
            raise ValueError('Parser delegate differs')
        if name == 'toString' and '// String RAID Admin request [details redacted]' not in match[1]:
            raise ValueError('Request diagnostic literal differs')
        verified_methods[entry] = operations
    sources = [ROOT/'tests/java/SecurityProbe.java', ROOT/'tests/java/fixture/OfflineGuard.java']
    results = []
    with tempfile.TemporaryDirectory(prefix='raid-security-') as tmp:
        run_jdk(args.jdk,'javac',['-source','8','-target','8','-cp',str(original),'-d',tmp]+[str(p) for p in sources])
        for jar,fixed in [(original,'false'),(args.jar,'true')]:
            results.append(run_jdk(args.jdk,'java',['-Xverify:all','-Djava.awt.headless=true','-Duser.home='+tmp,
                '-cp',tmp+':'+str(jar.resolve()),'SecurityProbe',fixed],timeout=30).splitlines())
    if results[0][:-1] != results[1][:-1]: raise ValueError('Allowed XML behavior differs')
    print(json.dumps({'source_commit':provenance['source_commit'],'source_dirty':provenance['source_dirty'],
        'request_inventory':request_inventory,'independent_preservation':'PASS', 'original_sha256':sha(original),'candidate_sha256':sha(args.jar),'jdk_tree_sha256':lock['tree_sha256'],
        'verifier_sources':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(), ROOT/'tools/inventory.py', ROOT/'tools/verify_builds.py']},
        'fixture_sources':{str(p.relative_to(ROOT)):sha(p) for p in sources},'javap_verified_methods':verified_methods,'observations':results,
        'limits':'Independent preservation of resolver, parser construction delegate, two request diagnostics and response allocation operands. Helper class version, 16 MiB ceiling, comparison and preallocation constructor order checked. Small allowed/malformed/external-resource XML and diagnostic fixtures only. Explicit XML quota behavior and allocation boundary/queue behavior are separately recorded by resource and transport tools. Header constructor insertion is independently verified; header budget behavior is separately recorded by the header/transport fixtures. No HTTP framing qualification, connection recovery, real controller data, full application output or GUI qualification.'},indent=2))

if __name__ == '__main__': main()
