#!/usr/bin/env python3
"""Offline ownership experiment against pinned audit.20; not release qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from audit_support import ROOT,sha,verify_jdk,verify_python,run_jdk,isolated_env
from baseline import write_jar
from sync_ownership_patch import transform_manager,transform_sender,normalize_manager,normalize_sender,MANAGER_SHA,SENDER_SHA
from runtime import runtime_manifest,verify_runtime
from inventory import disassemble_entries
from sync_ownership_structure import check

MANAGER='com/apple/xsr/net/CommunicationsManager.class'
SENDER='com/apple/xsr/net/CommunicationsManager$SyncSender.class'
REFERENCE='f6e545bbd90e7f9616df448f09cc4a889b909fa8e79a8183af8fa96a71d9f859'
CANDIDATE_SHA='05a6ce59ba13a811a1e46478b1b2477bdf575ae66a14bb700933f8e13422aa38'
PASS='PASS memory transport ownership; guarded_operations=0; production transport unqualified'
VECTORS={
 ('fixed','queued'):'sync_ownership queued fixed=true cancelled_send=0 healthy_follow_on=1 caller=legacy-IOException',
 ('legacy','queued'):'sync_ownership queued fixed=false cancelled_send=1 healthy_follow_on=1 caller=legacy-IOException',
 ('fixed','active'):'sync_ownership active fixed=true sends=1 outcome=real-response-identity',
 ('legacy','active'):'sync_ownership active fixed=false sends=1 outcome=failure-before-reply',
 ('fixed','notify-race'):'sync_ownership notify_race fixed=true result=real-response-identity',
 ('legacy','notify-race'):'sync_ownership notify_race fixed=false result=interrupt-overwrote-reply',
 ('fixed','first-reply'):'sync_ownership first_reply fixed=true retained=first claim_once=true',
 ('legacy','first-reply'):'sync_ownership first_reply fixed=false retained=last claim_once=false'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',required=True,type=Path);p.add_argument('--runtime',required=True,type=Path,action='append');p.add_argument('reference',type=Path);a=p.parse_args()
 verify_python();compiler=verify_jdk(a.jdk)
 if a.reference.is_symlink() or not a.reference.is_file() or sha(a.reference)!=REFERENCE:raise ValueError('Exact audit.20 reference required')
 ledger=json.loads((ROOT/'audit/stopped-post-final-integrity.json').read_text())
 if ledger['candidate_jar_sha256']!=REFERENCE:raise ValueError('Reference ledger disagrees')
 with zipfile.ZipFile(a.reference) as z:entries={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
 if hashlib.sha256(entries[MANAGER]).hexdigest()!=MANAGER_SHA or hashlib.sha256(entries[SENDER]).hexdigest()!=SENDER_SHA:raise ValueError('Reference classes differ')
 modified=dict(entries);modified[MANAGER]=transform_manager(entries[MANAGER]);modified[SENDER]=transform_sender(entries[SENDER])
 if normalize_manager(modified[MANAGER])!=entries[MANAGER] or normalize_sender(modified[SENDER])!=entries[SENDER]:raise ValueError('Full predecessor reconstruction differs')
 if {n for n in modified if modified[n]!=entries[n]}!={MANAGER,SENDER}:raise ValueError('Ownership entry delta differs')
 names=('tests/java/fixture/OfflineGuard.java','tests/java/com/apple/xsr/net/SyncOwnershipObservation.java','tests/java/ownershipfixture/AcpxConnection.java','tools/check_sync_ownership.py','tools/sync_ownership_structure.py','tools/inventory.py','tools/sync_ownership_patch.py','tools/class_patch.py','tools/audit_support.py','tools/baseline.py','tools/runtime.py','audit/stopped-post-final-integrity.json','audit/runtime-lock.json','audit/python-lock.json','audit/jdk-lock.json')
 hashes={n:sha(ROOT/n) for n in names};commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip();dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
 lock=runtime_manifest();runtimes=[];seen=set()
 for root in a.runtime:
  arch=None
  for key in ('aarch64','x64'):
   try:verify_runtime(root,lock['architectures'][key])
   except ValueError:continue
   arch=key;break
  if arch is None or arch in seen:raise ValueError('Distinct pinned runtimes required')
  seen.add(arch);runtimes.append((root,arch))
 if seen!={'aarch64','x64'}:raise ValueError('Both runtime architectures required')
 observations=[]
 with tempfile.TemporaryDirectory(prefix='raid-sync-ownership-') as tmp:
  tmp=Path(tmp);candidate=tmp/'ownership-experiment.jar';write_jar(candidate,modified)
  if sha(candidate)!=CANDIDATE_SHA:raise ValueError('Reviewed experiment candidate differs')
  fixtures=tmp/'fixtures';stub=tmp/'stub';fixtures.mkdir();stub.mkdir()
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(candidate),'-d',str(stub),str(ROOT/names[2])])
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(stub)+':'+str(candidate),'-d',str(fixtures)]+[str(ROOT/n) for n in names[:2]])
  fixture_classes={str(x.relative_to(fixtures)):sha(x) for x in fixtures.rglob('*.class')};stub_classes={str(x.relative_to(stub)):sha(x) for x in stub.rglob('*.class')}
  if set(fixture_classes)!={'fixture/OfflineGuard.class','com/apple/xsr/net/SyncOwnershipObservation.class','com/apple/xsr/net/SyncOwnershipObservation$1.class'}:raise ValueError('Fixture class allowlist differs')
  if set(stub_classes)!={'com/apple/xsr/net/AcpxConnection.class','com/apple/xsr/net/AcpxConnection$1.class'}:raise ValueError('Memory shadow allowlist differs')
  if set(fixture_classes)&set(entries):raise ValueError('Unapproved application shadow')
  for kind,entry in (('manager',MANAGER),('sender',SENDER)):
   before,after=[disassemble_entries(a.jdk,jar,[entry],verbose=True) for jar in (a.reference,candidate)]
   check(before,after,kind)
  variants={'fixed':(candidate,modified),'legacy':(a.reference.resolve(),entries)}
  for root,arch in runtimes:
   for execution in ('-Xint','-Xcomp'):
    for (policy,mode),vector in VECTORS.items():
     jar,artifact=variants[policy];pins=[hashlib.sha256(artifact[n]).hexdigest() for n in (MANAGER,SENDER)]
     lines=run_jdk(root/'Contents/Home','java',['-Xverify:all',execution,'-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(tmp),'-cp',str(fixtures)+':'+str(stub)+':'+str(jar),'com.apple.xsr.net.SyncOwnershipObservation',mode,policy,str(jar),str(stub)]+pins+[stub_classes['com/apple/xsr/net/AcpxConnection.class'],str(fixtures),fixture_classes['com/apple/xsr/net/SyncOwnershipObservation.class'],fixture_classes['fixture/OfflineGuard.class'],fixture_classes['com/apple/xsr/net/SyncOwnershipObservation$1.class'],stub_classes['com/apple/xsr/net/AcpxConnection$1.class']],timeout=30,require_empty_stderr=True).splitlines()
     if lines!=[vector,PASS]:raise ValueError('Ownership vector differs; raw output withheld; timeout/error does not qualify')
     observations.append({'architecture':arch,'execution':execution,'policy':policy,'scenario':mode,'jar_sha256':sha(jar),'manager_class_sha256':pins[0],'sender_class_sha256':pins[1],'lines':lines})
   verify_runtime(root,lock['architectures'][arch])
  candidate_sha=sha(candidate)
 verify_jdk(a.jdk)
 if subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()!=commit or bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))!=dirty:raise ValueError('Experiment working-tree state changed')
 if any(sha(ROOT/n)!=value for n,value in hashes.items()) or sha(a.reference)!=REFERENCE:raise ValueError('Experiment input changed')
 print(json.dumps({'qualification':False,'status':'isolated experiment; baseline build unchanged','fixture_commit':commit,'fixture_dirty':dirty,'reference_jar_sha256':REFERENCE,'candidate_jar_sha256':candidate_sha,'compiler_tree_sha256':compiler['tree_sha256'],'source_hashes':hashes,'fixture_class_hashes':fixture_classes,'shadow_class_hashes':stub_classes,'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'observations':observations,'limits':'Memory transport serializes requests only; no controller contact or native GUI. Original constructor bypassed. Cancellation happens before worker claim, not before doConnect; connection attempts can still fail or stop session. After claim, interrupt cannot cancel the wait, transport has no overall deadline and abnormal worker exit may strand it. No release or baseline qualification. x64 executes under Rosetta, not physical Intel.'},indent=2))
if __name__=='__main__':main()
