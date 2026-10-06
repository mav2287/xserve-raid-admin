#!/usr/bin/env python3
"""Prove local worker/shutdown lock ordering with guarded empty queues only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from audit_support import ROOT,sha,verify_jdk,verify_python,run_jdk,isolated_env
from baseline import verify_original,write_jar
from class_patch import ClassFile,assert_stop_lock_order,AUDIT18_MANAGER_SHA256,u2
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact
ENTRY='com/apple/xsr/net/CommunicationsManager.class'
OWNER='com/apple/xsr/net/CommunicationsManager'

def expected(mode,deadlock):return ['stop_lock '+mode+' outcome='+('exact-deadlock-pair' if deadlock else 'completed')+' guarded_operations=0; requests=0','PASS stop lock observation; no profiles, sockets or production transport']

def subclass_inventory(jar):
    count=0;found=[]
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith('.class'):continue
            cls=ClassFile(z.read(name));count+=1;index=u2(cls.data,cls.pool_end+4)
            if not index:continue
            tag,v=cls.pool[index]
            if tag!=7:raise ValueError('Superclass constant differs')
            if cls.text(u2(v,0))==OWNER:found.append(name)
    if found:raise ValueError('Manager subclass would lose overridden stop behavior')
    return {'jar_sha256':sha(jar),'class_count':count,'manager_subclasses':found}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',required=True,type=Path);p.add_argument('--runtime',required=True,action='append',type=Path);p.add_argument('--candidate-sha256',required=True);p.add_argument('--development',action='store_true');p.add_argument('candidate',type=Path);a=p.parse_args();verify_python();compiler=verify_jdk(a.jdk)
    commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip();dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    if dirty and not a.development:raise ValueError('Clean fixture required')
    original=ROOT/'original/RAID_Admin_original.jar';verify_original(original)
    if a.candidate.is_symlink() or not a.candidate.is_file() or a.candidate.resolve()==original.resolve() or sha(a.candidate)!=a.candidate_sha256:raise ValueError('Candidate identity differs')
    identity,manifest=check_artifact(a.candidate.resolve().parents[3])
    if identity!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected'] or a.candidate_sha256!=json.loads((ROOT/'audit/stopped-post-recovery-expected.json').read_text())['candidate_jar_sha256']:raise ValueError('Candidate differs from reviewed artifact')
    if not a.development and manifest['source_dirty']:raise ValueError('Clean application required')
    with zipfile.ZipFile(original) as z:before=z.read(ENTRY)
    with zipfile.ZipFile(a.candidate) as z:entries={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    assert_stop_lock_order(before,entries[ENTRY])
    reference=json.loads((ROOT/'audit/connect-stop-final-integrity.json').read_text())
    if reference['changed_entry_sha256_from_audit17'][ENTRY]['after']!=AUDIT18_MANAGER_SHA256:raise ValueError('Audit.18 class pin differs from measured qualification ledger')
    names=('tests/java/fixture/OfflineGuard.java','tests/java/com/apple/xsr/net/StopLockObservation.java','tools/check_stop_lock.py','tools/class_patch.py','tools/baseline.py','tools/audit_support.py','tools/runtime.py','tools/verify_builds.py','audit/expected-build.json','audit/stopped-post-recovery-expected.json','audit/runtime-lock.json','audit/connect-stop-final-integrity.json')
    inputs=[ROOT/n for n in names];hashes={n:sha(ROOT/n) for n in names};runtimes=[];seen=set();lock=runtime_manifest()
    for root in a.runtime:
        arch=None
        for key in ('aarch64','x64'):
            try:verify_runtime(root,lock['architectures'][key])
            except ValueError:continue
            arch=key;break
        if arch is None or arch in seen:raise ValueError('Distinct pinned runtime required')
        seen.add(arch);runtimes.append((root,arch))
    if seen!={'aarch64','x64'}:raise ValueError('Both architectures required')
    inventories={'original':subclass_inventory(original),'candidate':subclass_inventory(a.candidate)}
    for root,arch in runtimes:
        inventories[arch+'-vendor-extension-classpath']={str(j.relative_to(root)):subclass_inventory(j) for j in sorted((root/'Contents/Home/jre/lib/ext').glob('*.jar'))}
    observations=[]
    with tempfile.TemporaryDirectory(prefix='raid-stop-lock-') as tmp:
        run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(a.candidate.resolve()),'-d',tmp]+[str(x) for x in inputs[:2]])
        classes={str(x.relative_to(tmp)):sha(x) for x in Path(tmp).rglob('*.class')}
        if set(classes)!={'fixture/OfflineGuard.class','com/apple/xsr/net/StopLockObservation.class','com/apple/xsr/net/StopLockObservation$1.class','com/apple/xsr/net/StopLockObservation$2.class'}:raise ValueError('Fixture class allowlist differs')
        if set(classes)&set(entries):raise ValueError('Fixture shadows application class')
        cls=ClassFile(entries[ENTRY]);_,b,e=next(x for m in cls.methods if m['name']==('dispatchLoop' if any(t['name']=='dispatchLoop' for t in cls.methods) else 'run') for x in m['attributes'] if x[0]=='Code');mutants=[]
        for label,pcs in (('pc18',(18,)),('pc45',(45,)),('both',(18,45))):
            changed=bytearray(assert_stop_lock_order(before,entries[ENTRY]) if label=='both' else entries[ENTRY])
            if label!='both':
                for pc in pcs:changed[b+14+pc:b+14+pc+3]=bytes.fromhex('b6001b')
            modified=dict(entries);modified[ENTRY]=bytes(changed);jar=Path(tmp)/(label+'-getter-bypass.jar');write_jar(jar,modified);mutants.append((label,jar))
        for root,arch in runtimes:
            def observe(jar,mode,deadlock,execution,label):
                with zipfile.ZipFile(jar) as z:class_sha=hashlib.sha256(z.read(ENTRY)).hexdigest()
                output=run_jdk(root/'Contents/Home','java',['-Xverify:all',execution,'-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.StopLockObservation',mode,'deadlock' if deadlock else 'safe',str(jar.resolve()),class_sha],timeout=25)
                if output.splitlines()!=expected(mode,deadlock):raise ValueError('Lock observation differs; verifier/error/timeout never count as evidence')
                observations.append({'architecture':arch,'execution':execution,'variant':label,'scenario':mode,'exact_deadlock_pair':deadlock,'jar_sha256':sha(jar),'manager_class_sha256':class_sha,'lines':output.splitlines()})
            for execution in ('-Xint','-Xcomp'):
                for mode in ('pc18','pc45'):observe(a.candidate,mode,False,execution,'candidate')
            for label,jar in mutants:
                for mode in ('pc18','pc45'):observe(jar,mode,not(label=='pc45' and mode=='pc18'),'-Xint','audit18-Manager-restored' if label=='both' else label+'-getter-restored')
            verify_runtime(root,lock['architectures'][arch])
    if any(sha(ROOT/n)!=value for n,value in hashes.items()):raise ValueError('Fixture input changed')
    if sha(a.candidate)!=a.candidate_sha256:raise ValueError('Candidate changed')
    if not a.development and subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()):raise ValueError('Clean fixture changed')
    print(json.dumps({'qualification':not a.development,'source_commit':manifest['source_commit'],'source_dirty':manifest['source_dirty'],'fixture_commit':commit,'fixture_dirty':dirty,'candidate_sha256':sha(a.candidate),'original_sha256':sha(original),'compiler_tree_sha256':compiler['tree_sha256'],'source_hashes':hashes,'fixture_class_hashes':classes,'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'subclass_inventory':inventories,'observations':observations,'limits':'Real empty-queue worker and original shutdown with synthetic Manager allocated without constructor; no requests, polling, GUI, profiles, sockets or controller transport. Two direct-read windows and private volatile field statically reconstruct exact audit.18 class. Exact lock identity/owner/state and ThreadMXBean exact two-thread deadlock pair are observed, never inferred from timeout. Negative leftover threads are daemon and process exits naturally; no interrupts. Restored PC45 alone must still pass PC18 scenario. Launcher uses -jar with no manifest Class-Path, so application Manager subclasses must be in the candidate JAR. Vendor extension inventories are supplemental; parent bootstrap/extension loaders cannot link an application-loader superclass. External plugins unqualified. Both-restored control uses the exact audit.18 Manager class in the otherwise current candidate JAR, not the full historical app. Atomic posting, abnormal callback/interrupt exit, GUI callbacks and production/mounted volumes remain unqualified; x64 is Rosetta.'},indent=2))
if __name__=='__main__':main()
