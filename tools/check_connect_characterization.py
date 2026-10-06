#!/usr/bin/env python3
"""Characterize reported connection failure then held-request execution; stub only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from audit_support import ROOT, sha, tree, modes, digest, verify_jdk, verify_python, run_jdk, isolated_env
from class_patch import AUDIT17_MANAGER_SHA256
from baseline import verify_original
from runtime import runtime_manifest, verify_runtime


CM='com/apple/xsr/net/CommunicationsManager.class'
def expected(mode):
    return ['connect_failure '+mode+' reported=ConnectException then_sent=1 constructors='+('2' if mode=='single' else '3')+' held_request_identity=true held_body_equal=true polling_enable_calls=1',
            'PASS constructor-stub characterization; guarded_operations=0; production_transport=unqualified']

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
    ledger=json.loads((ROOT/'audit/sync-preenqueue-final-integrity.json').read_text())
    if a.candidate_sha256!=ledger['candidate_jar_sha256']:raise ValueError('Characterization requires reviewed audit.17 reference')
    output=a.candidate.resolve().parents[3];manifest=json.loads((output/'provenance.json').read_text());source_commit=ledger['source_commit']
    if manifest['source_commit']!=source_commit or manifest['source_dirty']:raise ValueError('Historical artifact source differs')
    measured={'files':tree(output/'RAID Admin.app'),'file_modes':modes(output/'RAID Admin.app')}
    if measured['files']!=manifest['files'] or measured['file_modes']!=manifest['file_modes'] or digest(measured)!=manifest['bundle_tree_sha256']:raise ValueError('Historical artifact manifest differs')
    historical=json.loads(subprocess.check_output(['/usr/bin/git','show',source_commit+':audit/expected-build.json'],cwd=ROOT,env=isolated_env(),text=True))['expected']
    measured.update(input_hashes=manifest['input_hashes'],original_jar_sha256=manifest['original_jar_sha256'],jdk=manifest['jdk'],builder=manifest['builder'])
    if measured!=historical:raise ValueError('Historical artifact differs from reviewed complete identity')
    for name,value in manifest['input_hashes'].items():
        if hashlib.sha256(subprocess.check_output(['/usr/bin/git','show',source_commit+':'+name],cwd=ROOT,env=isolated_env())).hexdigest()!=value:raise ValueError('Historical committed input differs')
    if not a.development and manifest['source_dirty']:raise ValueError('Clean source required')
    inputs=[ROOT/n for n in ('tests/java/connectfixture/AcpxConnection.java','tests/java/com/apple/xsr/net/ConnectFailureObservation.java','tests/java/fixture/OfflineGuard.java','patches/sun/io/MalformedInputException.java','tools/check_connect_characterization.py','tools/audit_support.py','tools/baseline.py','tools/runtime.py','tools/verify_builds.py','tools/class_patch.py','audit/runtime-lock.json','audit/sync-preenqueue-final-integrity.json')]
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
        for root,arch in runtimes:
            for jar in (original,a.candidate):
                with zipfile.ZipFile(jar) as z:
                    manager_hash=hashlib.sha256(z.read(CM)).hexdigest()
                    if jar==a.candidate and manager_hash!=AUDIT17_MANAGER_SHA256:raise ValueError('Measured audit.17 Manager class differs from reconstruction pin')
                    recovery_hash=hashlib.sha256(z.read('compat/RejectionRecovery.class')).hexdigest() if 'compat/RejectionRecovery.class' in z.namelist() else '-'
                cp=str(stub)+':'+str(fixture)+':'+str(jar.resolve())
                for mode in ('single','dual'):
                    output=run_jdk(root/'Contents/Home','java',['-Xverify:all','-Xint','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',cp,'com.apple.xsr.net.ConnectFailureObservation',mode,str(stub),str(jar.resolve()),manager_hash,recovery_hash,'legacy'],timeout=35)
                    if output.splitlines()!=expected(mode):raise ValueError('Connection characterization differs; raw output withheld')
                    observations.append({'architecture':arch,'execution':'-Xint','jar_sha256':sha(jar),'manager_class_sha256':manager_hash,'recovery_class_sha256':recovery_hash,'mode':mode,'lines':output.splitlines()})
            verify_runtime(root,runtime_lock['architectures'][arch])
    if sha(a.candidate)!=a.candidate_sha256:raise ValueError('Reference JAR changed')
    if any(sha(ROOT/n)!=value for n,value in hashes.items()):raise ValueError('Fixture input changed')
    if not a.development and subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()):raise ValueError('Fixture changed during run')
    print(json.dumps({'qualification':not a.development,'source_commit':manifest['source_commit'],'source_dirty':manifest['source_dirty'],'fixture_commit':commit,'fixture_dirty':dirty,'candidate_sha256':sha(a.candidate),'original_sha256':sha(original),'compiler_tree_sha256':lock['tree_sha256'],'source_hashes':hashes,'stub_class_hashes':stub_classes,'fixture_class_hashes':fixture_classes,'runtime_trees':{arch:runtime_lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'observations':observations,'limits':'Source characterization of initial single/dual-host reported-failure continuation only, interpreted verified execution. Test-only Acpx constructor/send shadow plus bounded synthetic body and worker-thread stop hook; not HTTP/network/production transport or wire parity. Original control uses the byte-identical compatibility shim. CodeSource and Manager/recovery resource hashes asserted. Guard blocks sockets, preferences, writes, exec and sentinel reads; ordinary class-file reads allowed. No production/mounted volume, real host or app launch. Parent 35-second watchdog per scenario; no fixture interrupt calls; worker stop uses preserved shutdown() queue notification (archived original bytecode). polling_enable_calls counts only FakeSystem; no polling agent is instantiated. Complete GUI recovery and original polling reconnect unqualified.'},indent=2))

if __name__=='__main__':main()
