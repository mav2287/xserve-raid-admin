#!/usr/bin/env python3
"""Qualify stop before reported connection failure; bounded constructor shadow only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import struct
import zipfile
from audit_support import ROOT, sha, tree, modes, digest, verify_jdk, verify_python, run_jdk, isolated_env
from baseline import verify_original, write_jar
from class_patch import ClassFile, assert_connect_failure_stop, normalize_current_extensions, AUDIT17_MANAGER_SHA256
from verify_builds import check_artifact
from runtime import runtime_manifest, verify_runtime


CM='com/apple/xsr/net/CommunicationsManager.class'
def expected(mode):
    return ['connect_failure '+mode+' reported=ConnectException then_sent=1 constructors='+('2' if mode=='single' else '3')+' held_request_identity=true held_body_equal=true polling_enable_calls=1',
            'PASS constructor-stub characterization; guarded_operations=0; production_transport=unqualified']

def terminal_expected(mode):
    if '-async' in mode:return ['connect_failure '+mode+' stop_inside_callback=true constructors='+('2' if mode.startswith('dual-') else '1')+' sends=0 commands='+'1'+' exception_identity=true','PASS constructor-stub async ordering; guarded_operations=0; production_transport=unqualified']
    if mode in ('single','dual'):
        return ['connect_failure '+mode+' reported=ConnectException then_sent=0 constructors='+('1' if mode=='single' else '2')+' stopped=true polling_enable_calls=0','PASS constructor-stub characterization; guarded_operations=0; production_transport=unqualified']
    line='connect_failure single-null unpublished_failure=true constructors=2 sends=1 retry_preserved=true' if mode=='single-null' else 'connect_failure '+mode+' constructors=0 sends=0 connects='+('0' if mode=='nohost-null' else '1')+' commands='+'1'+' stopped=true late_async_stranded=1'
    return [line,'PASS constructor-stub terminal extras; guarded_operations=0; production_transport=unqualified']

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jdk',required=True,type=Path)
    p.add_argument('--runtime',required=True,action='append',type=Path)
    p.add_argument('--candidate-sha256',required=True)
    p.add_argument('--development',action='store_true')
    p.add_argument('candidate',type=Path)
    a=p.parse_args();verify_python();lock=verify_jdk(a.jdk)
    commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    if dirty and not a.development:raise ValueError('Clean fixture required')
    original=ROOT/'original/RAID_Admin_original.jar';verify_original(original)
    if a.candidate.is_symlink() or not a.candidate.is_file() or a.candidate.resolve()==original.resolve() or sha(a.candidate)!=a.candidate_sha256:raise ValueError('Candidate identity differs')
    identity,manifest=check_artifact(a.candidate.resolve().parents[3])
    if identity!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected'] or a.candidate_sha256!=json.loads((ROOT/'audit/stopped-post-recovery-expected.json').read_text())['candidate_jar_sha256']:raise ValueError('Candidate differs from reviewed complete artifact')
    if not a.development and manifest['source_dirty']:raise ValueError('Clean application source required')
    with zipfile.ZipFile(original) as z:before=z.read(CM)
    with zipfile.ZipFile(a.candidate) as z:entries={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    assert_connect_failure_stop(before,entries[CM])
    derivation=json.loads((ROOT/'audit/connect-stop-reference-derivation.json').read_text())
    if derivation['manager_class_sha256']!=AUDIT17_MANAGER_SHA256 or derivation['jar_sha256']!=json.loads((ROOT/'audit/sync-preenqueue-final-integrity.json').read_text())['candidate_jar_sha256']:raise ValueError('Audit.17 class derivation differs from reviewed ledger')
    inputs=[ROOT/n for n in ('tests/java/connectfixture/AcpxConnection.java','tests/java/com/apple/xsr/net/ConnectFailureObservation.java','tests/java/fixture/OfflineGuard.java','patches/sun/io/MalformedInputException.java','tools/check_connect_stop.py','tools/audit_support.py','tools/baseline.py','tools/runtime.py','tools/verify_builds.py','tools/class_patch.py','tools/sync_ownership_patch.py','tools/worker_exit_patch.py','tools/stop_admission_patch.py','tools/stop_admission_structure.py','audit/runtime-lock.json','audit/expected-build.json','audit/stopped-post-recovery-expected.json','audit/connect-stop-reference-derivation.json','audit/sync-preenqueue-final-integrity.json')]
    hashes={str(x.relative_to(ROOT)):sha(x) for x in inputs}
    runtime_lock=runtime_manifest();runtimes=[];seen=set()
    for root in a.runtime:
        arch=None
        for key in ('aarch64','x64'):
            try:verify_runtime(root,runtime_lock['architectures'][key])
            except ValueError:continue
            arch=key;break
        if arch is None or arch in seen:raise ValueError('Distinct pinned runtime required')
        seen.add(arch);runtimes.append((root,arch))
    if seen!={'aarch64','x64'}:raise ValueError('Both pinned architectures required')
    observations=[]
    with tempfile.TemporaryDirectory(prefix='raid-connect-characterization-') as tmp:
        stub=Path(tmp)/'stub';fixture=Path(tmp)/'fixture';stub.mkdir();fixture.mkdir()
        run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(original),'-d',str(stub),str(inputs[0])])
        run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(stub)+':'+str(original),'-d',str(fixture)]+[str(x) for x in inputs[1:4]])
        stub_classes={str(x.relative_to(stub)):sha(x) for x in stub.rglob('*.class')}
        if set(stub_classes)!={'com/apple/xsr/net/AcpxConnection.class','com/apple/xsr/net/AcpxConnection$1.class'}:raise ValueError('Stub class allowlist differs')
        fixture_classes={str(x.relative_to(fixture)):sha(x) for x in fixture.rglob('*.class')}
        if set(fixture_classes)!={'fixture/OfflineGuard.class','sun/io/MalformedInputException.class','com/apple/xsr/net/ConnectFailureObservation.class','com/apple/xsr/net/ConnectFailureObservation$FakeSystem.class','com/apple/xsr/net/ConnectFailureObservation$1.class','com/apple/xsr/net/ConnectFailureObservation$2.class','com/apple/xsr/net/ConnectFailureObservation$3.class','com/apple/xsr/net/ConnectFailureObservation$4.class','com/apple/xsr/net/ConnectFailureObservation$5.class','com/apple/xsr/net/ConnectFailureObservation$6.class','com/apple/xsr/net/ConnectFailureObservation$7.class','com/apple/xsr/net/ConnectFailureObservation$8.class','com/apple/xsr/net/ConnectFailureObservation$FixtureAssertionDetected.class'}:raise ValueError('Fixture class allowlist differs')
        for jar in (original,a.candidate):
            with zipfile.ZipFile(jar) as z:
                if any(n in z.namelist() for n in (set(fixture_classes)|set(stub_classes))-{'sun/io/MalformedInputException.class','com/apple/xsr/net/AcpxConnection.class'}):raise ValueError('Unexpected fixture class shadow')
        with zipfile.ZipFile(a.candidate) as z:
            if (fixture/'sun/io/MalformedInputException.class').read_bytes()!=z.read('sun/io/MalformedInputException.class'):raise ValueError('Control shim differs from candidate')
            if 'com/apple/xsr/net/AcpxConnection$1.class' in z.namelist():raise ValueError('Nested stub shadows production class')
        original_class=ClassFile(before);patched_class=ClassFile(entries[CM])
        def code_start(cls):return next(a[1]+14 for m in cls.methods if m['name']=='doConnect' for a in m['attributes'] if a[0]=='Code')
        ob=code_start(original_class);nb=code_start(patched_class)
        mutants=[]
        for label,start,end,mode,policy in (('nohost',393,401,'verify-nohost','terminal'),('reported',578,583,'single','legacy')):
            control=normalize_current_extensions(entries[CM]) if label=='reported' else entries[CM]
            control_start=code_start(ClassFile(control))
            changed=bytearray(control);changed[control_start+start:control_start+end]=before[ob+start:ob+end]
            mutant_entries=dict(entries)
            if label=='reported':mutant_entries['com/apple/xsr/net/CommunicationsManager$SyncSender.class']=normalize_current_extensions(entries['com/apple/xsr/net/CommunicationsManager$SyncSender.class'])
            mutant_entries[CM]=bytes(changed);jar=Path(tmp)/(label+'-bypass.jar');write_jar(jar,mutant_entries);mutants.append((label,jar,mode,policy))
        _,cb,ce=next(a for m in patched_class.methods if m['name']=='doConnect' for a in m['attributes'] if a[0]=='Code')
        code_length=struct.unpack('>I',entries[CM][cb+10:cb+14])[0];original_code=entries[CM][cb+14:cb+14+code_length];reordered=bytearray(original_code);reordered[740:744]=b'\x00'*4;reordered[591:599]=b'\xc8'+struct.pack('>i',code_length-591)+bytes(3)
        reordered.extend(original_code[740:744]+original_code[591:599]+b'\xc8'+struct.pack('>i',599-(code_length+12)))
        body=entries[CM][cb+6:cb+10]+struct.pack('>I',len(reordered))+reordered+entries[CM][cb+14+code_length:ce]
        mutant_entries=dict(entries);mutant_entries[CM]=entries[CM][:cb]+entries[CM][cb:cb+2]+struct.pack('>I',len(body))+body+entries[CM][ce:]
        reordered_jar=Path(tmp)/'callback-before-stop.jar';write_jar(reordered_jar,mutant_entries);mutants.append(('late-stop',reordered_jar,'single-async','late-stop'))
        for root,arch in runtimes:
            def observe(jar,mode,policy,execution):
                with zipfile.ZipFile(jar) as z:
                    manager_hash=hashlib.sha256(z.read(CM)).hexdigest();recovery_hash=hashlib.sha256(z.read('compat/RejectionRecovery.class')).hexdigest()
                cp=str(stub)+':'+str(fixture)+':'+str(jar.resolve())
                try:output=run_jdk(root/'Contents/Home','java',['-Xverify:all',execution,'-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',cp,'com.apple.xsr.net.ConnectFailureObservation',mode,str(stub),str(jar.resolve()),manager_hash,recovery_hash,policy],timeout=35)
                except RuntimeError:raise RuntimeError('Connection fixture failed: '+arch+' '+mode+' '+policy+' (child output withheld)') from None
                return output.splitlines(),manager_hash,recovery_hash
            for execution in ('-Xint','-Xcomp'):
                for mode in ('single','dual','nohost','nohost-null','nohost-throw','single-null','single-async','dual-async','single-async-throw'):
                    lines,mh,rh=observe(a.candidate,mode,'terminal',execution)
                    if lines!=terminal_expected(mode):raise ValueError('Connect stop vector differs; raw output withheld')
                    observations.append({'architecture':arch,'execution':execution,'jar_sha256':sha(a.candidate),'manager_class_sha256':mh,'recovery_class_sha256':rh,'mode':mode,'lines':lines})
            for assertion_execution in ('-Xint','-Xcomp'):
             lines,mh,rh=observe(a.candidate,'verify-callback-assertions','terminal',assertion_execution)
             if lines!=['PASS fixture detects swallowed callback assertion outside worker; guarded_operations=0']:raise ValueError('Assertion containment control differs')
             observations.append({'architecture':arch,'execution':assertion_execution,'mode':'verify-callback-assertions','fixture_assertion_control':True,'jar_sha256':sha(a.candidate),'manager_class_sha256':mh,'recovery_class_sha256':rh,'lines':lines})
            for label,jar,mode,policy in mutants:
                lines,mh,rh=observe(jar,mode,policy,'-Xint')
                wanted=['PASS verified no-host bypass reports before stop; guarded_operations=0'] if label=='nohost' else [line.replace('stop_inside_callback=true','stop_inside_callback=false') for line in terminal_expected('single-async')] if label=='late-stop' else expected('single')
                if lines!=wanted:raise ValueError('Semantic negative control differs; verifier failure not accepted')
                observations.append({'architecture':arch,'execution':'-Xint','mode':mode,'semantic_negative_control':label,'jar_sha256':sha(jar),'manager_class_sha256':mh,'recovery_class_sha256':rh,'lines':lines})
            verify_runtime(root,runtime_lock['architectures'][arch])
    if sha(a.candidate)!=a.candidate_sha256:raise ValueError('Reference JAR changed')
    if any(sha(ROOT/n)!=value for n,value in hashes.items()):raise ValueError('Fixture input changed')
    if not a.development and subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()):raise ValueError('Fixture changed during run')
    print(json.dumps({'qualification':not a.development,'source_commit':manifest['source_commit'],'source_dirty':manifest['source_dirty'],'fixture_commit':commit,'fixture_dirty':dirty,'candidate_sha256':sha(a.candidate),'original_sha256':sha(original),'compiler_tree_sha256':lock['tree_sha256'],'source_hashes':hashes,'stub_class_hashes':stub_classes,'fixture_class_hashes':fixture_classes,'runtime_trees':{arch:runtime_lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'observations':observations,'limits':'Real Manager and SyncSender with strict test-only Acpx constructor/send shadow, CodeSource/resource hash assertions and class allowlists. No real transport/controller, app launch, profile or production volume. Fake polling setter counts do not prove agent behavior. Parent 35-second watchdog; worker shutdown uses preserved queue notification, no fixture interrupt. Positive no-host and callback-before-stop mutants demonstrate unsafe ordering. Reported-continuation control first restores exact audit.20 Manager and Sender, then bypasses reported-stop; current ownership independently blocks completed Sender continuation. Verifier/errors/timeouts never count as rejection. Dual first silent failure and unpublished single-handler retry remain. Late-post completion and ownership are qualified separately by admission/guarded-worker gates. VM failure completion, stop-versus-active-send and GUI reconnect recovery remain unqualified.'},indent=2))

if __name__=='__main__':main()
