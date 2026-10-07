#!/usr/bin/env python3
"""Offline combined ownership/worker qualification; no Main or controller transport."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from audit_support import ROOT,sha,verify_jdk,verify_python,run_jdk,isolated_env
from baseline import verify_original
from inventory import disassemble_entries
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact
from worker_exit_structure import normalize_extensions
from worker_exit_patch import normalize
from sync_ownership_patch import normalize_manager,normalize_sender
from check_sync_ownership import REFERENCE,VECTORS,PASS,MANAGER,SENDER

SOURCES=('tests/java/com/apple/xsr/net/WorkerCompletionBatchObservation.java','tests/java/fixture/OfflineGuard.java','tests/java/fixture/FixtureIdentity.java',
 'tests/java/com/apple/xsr/net/GuardedWorkerExitObservation.java',
 'tests/java/com/apple/xsr/net/WorkerOwnershipObservation.java',
 'tests/java/com/apple/xsr/net/WorkerConstructorObservation.java',
 'tests/java/com/apple/xsr/net/WorkerConnectCallbackObservation.java')
FIXTURES={'com/apple/xsr/net/WorkerCompletionBatchObservation.class','com/apple/xsr/net/WorkerCompletionBatchObservation$Fault.class','com/apple/xsr/net/WorkerCompletionBatchObservation$Capture.class','fixture/OfflineGuard.class','fixture/FixtureIdentity.class',
 'com/apple/xsr/net/GuardedWorkerExitObservation.class','com/apple/xsr/net/GuardedWorkerExitObservation$SyntheticFault.class',
 'com/apple/xsr/net/WorkerOwnershipObservation.class','com/apple/xsr/net/WorkerOwnershipObservation$1.class',
 'com/apple/xsr/net/WorkerConstructorObservation.class',
 'com/apple/xsr/net/WorkerConnectCallbackObservation$HostileIOException.class','com/apple/xsr/net/WorkerConnectCallbackObservation$Capture.class','com/apple/xsr/net/WorkerConnectCallbackObservation.class','com/apple/xsr/net/WorkerConnectCallbackObservation$FakeSystem.class'}
SHADOWS={'com/apple/xsr/net/AcpxConnection.class','com/apple/xsr/net/AcpxConnection$1.class'}

def state():
 return (subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),
 bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',required=True,type=Path);p.add_argument('--runtime',required=True,type=Path,action='append');p.add_argument('--candidate-sha256',required=True);p.add_argument('--development',action='store_true');p.add_argument('candidate',type=Path);p.add_argument('reference',type=Path);a=p.parse_args()
 verify_python();compiler=verify_jdk(a.jdk);original=ROOT/'original/RAID_Admin_original.jar';verify_original(original);initial=state()
 if initial[1] and not a.development:raise ValueError('Clean fixture required')
 candidate=a.candidate.resolve();reference=a.reference.resolve()
 if a.candidate.is_symlink() or sha(candidate)!=a.candidate_sha256 or a.reference.is_symlink() or sha(reference)!=REFERENCE:raise ValueError('Artifact identity differs')
 identity,manifest=check_artifact(candidate.parents[3])
 if identity!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected']:raise ValueError('Candidate differs from expected artifact')
 if not a.development and manifest['source_dirty']:raise ValueError('Clean candidate source required')
 with zipfile.ZipFile(candidate) as z:entries={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
 with zipfile.ZipFile(reference) as z:old={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
 if normalize_manager(normalize(entries[MANAGER]))!=old[MANAGER] or normalize_sender(entries[SENDER])!=old[SENDER]:raise ValueError('Exact predecessor reconstruction differs')
 from stop_admission_structure import normalize_stop_admission
 normalize_stop_admission(disassemble_entries(a.jdk,candidate,[MANAGER],verbose=True),True)
 for entry in (MANAGER,SENDER):
  text=disassemble_entries(a.jdk,candidate,[entry],verbose=True);normalize_extensions(text)
 names=SOURCES+('tests/java/ownershipfixture/AcpxConnection.java','tools/check_guarded_worker.py','tools/worker_exit_structure.py','tools/worker_exit_patch.py','tools/stop_admission_patch.py','tools/stop_admission_structure.py','tools/sync_ownership_patch.py','tools/sync_ownership_structure.py','tools/class_patch.py','tools/socket_configuration_patch.py','tools/audit_support.py','tools/baseline.py','tools/runtime.py','tools/verify_builds.py','tools/inventory.py','tools/check_security.py','tools/check_sync_ownership.py','audit/expected-build.json','audit/security-patches.json','audit/runtime-lock.json','audit/python-lock.json','audit/jdk-lock.json','patches/compat/WorkerExit.java')
 names+=tuple('tests/fixtures/'+n+'.javap' for n in ('sync-ownership-candidate-manager','sync-ownership-reference-manager','sync-ownership-reference-sender'))
 hashes={n:sha(ROOT/n) for n in names};lock=runtime_manifest();runtimes=[];seen=set()
 for root in a.runtime:
  matches=[]
  for arch in ('aarch64','x64'):
   try:verify_runtime(root,lock['architectures'][arch]);matches.append(arch)
   except ValueError:pass
  if len(matches)!=1 or matches[0] in seen:raise ValueError('Distinct pinned runtime required')
  seen.add(matches[0]);runtimes.append((root,matches[0]))
 if seen!={'aarch64','x64'}:raise ValueError('Both runtimes required')
 observations=[]
 with tempfile.TemporaryDirectory(prefix='raid-guarded-worker-') as tmp:
  tmp=Path(tmp);stub=tmp/'stub';fixtures=tmp/'fixtures';stub.mkdir();fixtures.mkdir()
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(candidate),'-d',str(stub),str(ROOT/'tests/java/ownershipfixture/AcpxConnection.java')])
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(stub)+':'+str(candidate),'-d',str(fixtures)]+[str(ROOT/n) for n in SOURCES])
  classes={str(x.relative_to(fixtures)):sha(x) for x in fixtures.rglob('*.class')};shadows={str(x.relative_to(stub)):sha(x) for x in stub.rglob('*.class')}
  if set(classes)!=FIXTURES or set(shadows)!=SHADOWS or set(classes)&set(entries) or 'com/apple/xsr/net/AcpxConnection$1.class' in entries:raise ValueError('Class allowlist/shadowing differs')
  def observe(root,arch,execution,policy,kind,args,wanted,memory=True):
   jar,artifact=(candidate,entries) if policy=='fixed' else (reference,old)
   pins=[hashlib.sha256(artifact[n]).hexdigest() for n in (MANAGER,SENDER)]
   app={n:hashlib.sha256(v).hexdigest() for n,v in artifact.items() if n.startswith('compat/') and n.endswith('.class')};app.update({MANAGER:pins[0],SENDER:pins[1]})
   if not memory:app['com/apple/xsr/net/AcpxConnection.class']=hashlib.sha256(artifact['com/apple/xsr/net/AcpxConnection.class']).hexdigest()
   rows=[]
   for mapping,location in ((classes,fixtures),(shadows if memory else {},stub),(app,jar)):
    rows.extend(n[:-6].replace('/','.')+'\t'+str(location)+'\t'+h for n,h in sorted(mapping.items()))
   idfile=tmp/'identity.tsv';idfile.write_text('\n'.join(rows)+'\n')
   cp=str(fixtures)+(':'+str(stub) if memory else '')+':'+str(jar)
   try:lines=run_jdk(root/'Contents/Home','java',[execution,'-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(tmp),'-Dfixture.identitymanifest='+str(idfile),'-cp',cp,'com.apple.xsr.net.'+kind]+args,timeout=35,require_empty_stderr=True).splitlines()
   except RuntimeError:raise RuntimeError('Guarded worker fixture failed: '+arch+' '+execution+' '+kind+' '+(':'.join(args[:2]) if args else 'default')+' (child output withheld)') from None
   if lines!=wanted:raise ValueError('Guarded worker vector differs; output withheld; errors/timeouts never qualify')
   observations.append({'architecture':arch,'execution':execution,'policy':policy,'scenario':kind+':'+':'.join(args[:2]),'jar_sha256':sha(jar),'class_identity_manifest_sha256':sha(idfile),'lines':lines})
  for root,arch in runtimes:
   for execution in ('-Xint','-Xcomp'):
    observe(root,arch,execution,'fixed','WorkerConstructorObservation',[],['PASS actual Manager constructor and local exit; guarded_operations=0'],False)
    observe(root,arch,execution,'fixed','WorkerCompletionBatchObservation',[],['PASS worker completion batch; sync_before_manager_lock=true async_edt=true callback_error_contained=true no_replay=true fixed_signals=2 guarded_operations=0'])
    for mode in ('send-error','callback-error'):
     args=[mode,'workerfix',str(candidate),str(stub)]+[hashlib.sha256(entries[n]).hexdigest() for n in (MANAGER,SENDER)]+[shadows['com/apple/xsr/net/AcpxConnection.class'],str(fixtures),classes['com/apple/xsr/net/GuardedWorkerExitObservation.class'],classes['fixture/OfflineGuard.class'],classes['com/apple/xsr/net/GuardedWorkerExitObservation$SyntheticFault.class'],shadows['com/apple/xsr/net/AcpxConnection$1.class']]
     observe(root,arch,execution,'fixed','GuardedWorkerExitObservation',args,['worker_exit '+mode+' actual_worker_dead=true stopped=true caller_completed=true queue=0 outcome='+('unsent-shutdown' if mode=='callback-error' else 'unconfirmed'),'PASS guarded worker exit experiment; guarded_operations=0'])
    for mode in ('queued','active','notify-race','first-reply'):
     args=[mode,'fixed',str(candidate),str(stub)]+[hashlib.sha256(entries[n]).hexdigest() for n in (MANAGER,SENDER)]+[shadows['com/apple/xsr/net/AcpxConnection.class'],str(fixtures),classes['com/apple/xsr/net/WorkerOwnershipObservation.class'],classes['fixture/OfflineGuard.class'],classes['com/apple/xsr/net/WorkerOwnershipObservation$1.class'],shadows['com/apple/xsr/net/AcpxConnection$1.class']]
     observe(root,arch,execution,'fixed','WorkerOwnershipObservation',args,[VECTORS['fixed',mode],PASS])
   for policy in ('fixed','legacy'):
    for execution in (('-Xint','-Xcomp') if policy=='fixed' else ('-Xint',)):
     for location in ('nohost','single'):
      for failure in (('runtime','prefix-io','io','null-io','malformed','error','hostile-io','interrupt') if policy=='fixed' else ('runtime','prefix-io','io','null-io','malformed','error')):
       dup=int(policy=='legacy' and failure!='error');follow=int(policy=='fixed' or failure!='error')
       wanted=['worker_connect '+location+' '+failure+' fixed='+str(policy=='fixed').lower()+' connect_attempts=1 duplicate='+str(dup)+' follow='+str(follow)+' sends=0','PASS memory connection callback experiment; guarded_operations=0']
       observe(root,arch,execution,policy,'WorkerConnectCallbackObservation',[policy,location,failure],wanted)
   verify_runtime(root,lock['architectures'][arch])
 verify_jdk(a.jdk)
 if state()!=initial or any(sha(ROOT/n)!=h for n,h in hashes.items()) or sha(candidate)!=a.candidate_sha256 or sha(reference)!=REFERENCE:raise ValueError('Qualification inputs changed')
 print(json.dumps({'qualification':not a.development,'source_commit':manifest['source_commit'],'source_dirty':manifest['source_dirty'],'fixture_commit':initial[0],'fixture_dirty':initial[1],'candidate_sha256':sha(candidate),'reference_sha256':REFERENCE,'compiler_tree_sha256':compiler['tree_sha256'],'source_hashes':hashes,'fixture_class_hashes':classes,'shadow_class_hashes':shadows,'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'observations':observations,'limits':'Memory transport only, production and mounted volumes untouched. Actual Manager constructor verified separately with no connection; synthetic RaidSystem constructor bypassed. Positive original callback duplicates and queued loss, preserved ownership fixtures, exact class/resource identities. Ordinary Error completion verified; VM exhaustion and ThreadDeath delivery best-effort, not guaranteed. After claim interrupts wait for actual outcome with no overall deadline. Stop versus active send remains open. Async abnormal-exit deliveries move to headless EDT; native GUI and disposed AppContext unqualified. x64 executes under Rosetta, not physical Intel.'},indent=2))
if __name__=='__main__':main()
