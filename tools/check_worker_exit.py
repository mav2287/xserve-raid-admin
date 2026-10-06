#!/usr/bin/env python3
"""Positively characterize worker-death gaps; not baseline/release acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from audit_support import ROOT,sha,verify_jdk,verify_python,run_jdk,isolated_env
from baseline import write_jar
from sync_ownership_patch import transform_manager,transform_sender,normalize_manager,normalize_sender
from check_sync_ownership import MANAGER,SENDER,REFERENCE,CANDIDATE_SHA
from runtime import runtime_manifest,verify_runtime

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',required=True,type=Path);p.add_argument('--runtime',required=True,action='append',type=Path);p.add_argument('reference',type=Path);a=p.parse_args();verify_python();compiler=verify_jdk(a.jdk)
 if a.reference.is_symlink() or not a.reference.is_file() or sha(a.reference)!=REFERENCE:raise ValueError('Exact audit20 required')
 with zipfile.ZipFile(a.reference) as z:original={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
 modified=dict(original);modified[MANAGER]=transform_manager(original[MANAGER]);modified[SENDER]=transform_sender(original[SENDER])
 if normalize_manager(modified[MANAGER])!=original[MANAGER] or normalize_sender(modified[SENDER])!=original[SENDER] or {n for n in modified if modified[n]!=original[n]}!={MANAGER,SENDER}:raise ValueError('Ownership reconstruction/delta differs')
 if json.loads((ROOT/'audit/stopped-post-final-integrity.json').read_text())['candidate_jar_sha256']!=REFERENCE:raise ValueError('Reference ledger differs')
 names=('tests/java/fixture/OfflineGuard.java','tests/java/com/apple/xsr/net/WorkerExitObservation.java','tests/java/ownershipfixture/AcpxConnection.java','tools/check_worker_exit.py','tools/check_sync_ownership.py','tools/sync_ownership_structure.py','tools/inventory.py','audit/stopped-post-final-integrity.json','tools/sync_ownership_patch.py','tools/class_patch.py','tools/audit_support.py','tools/runtime.py','tools/baseline.py','audit/python-lock.json','audit/jdk-lock.json','audit/runtime-lock.json')
 hashes={n:sha(ROOT/n) for n in names};commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip();dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
 lock=runtime_manifest();runtimes=[];seen=set()
 for root in a.runtime:
  arch=None
  for key in ('aarch64','x64'):
   try:verify_runtime(root,lock['architectures'][key])
   except ValueError:continue
   arch=key;break
  if arch is None or arch in seen:raise ValueError('Distinct pinned runtime required')
  seen.add(arch);runtimes.append((root,arch))
 if seen!={'aarch64','x64'}:raise ValueError('Both architectures required')
 observations=[]
 with tempfile.TemporaryDirectory(prefix='raid-worker-exit-') as tmp:
  tmp=Path(tmp);candidate=tmp/'ownership.jar';write_jar(candidate,modified)
  if sha(candidate)!=CANDIDATE_SHA:raise ValueError('Reviewed ownership experiment differs')
  fixtures=tmp/'fixtures';stub=tmp/'stub';fixtures.mkdir();stub.mkdir()
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(candidate),'-d',str(stub),str(ROOT/names[2])])
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(stub)+':'+str(candidate),'-d',str(fixtures)]+[str(ROOT/n) for n in names[:2]])
  classes={str(x.relative_to(fixtures)):sha(x) for x in fixtures.rglob('*.class')};shadows={str(x.relative_to(stub)):sha(x) for x in stub.rglob('*.class')}
  if set(classes)!={'fixture/OfflineGuard.class','com/apple/xsr/net/WorkerExitObservation.class','com/apple/xsr/net/WorkerExitObservation$SyntheticFault.class'} or set(shadows)!={'com/apple/xsr/net/AcpxConnection.class','com/apple/xsr/net/AcpxConnection$1.class'} or set(classes)&set(original):raise ValueError('Fixture/shadow allowlists differ')
  for root,arch in runtimes:
   for policy,jar,entries in [('legacy',a.reference.resolve(),original),('fixed-ownership',candidate,modified)]:
    for execution in ('-Xint','-Xcomp'):
     for mode in ('send-error','callback-error'):
      pins=[hashlib.sha256(entries[n]).hexdigest() for n in (MANAGER,SENDER)]
      lines=run_jdk(root/'Contents/Home','java',['-Xverify:all',execution,'-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(tmp),'-cp',str(fixtures)+':'+str(stub)+':'+str(jar),'com.apple.xsr.net.WorkerExitObservation',mode,policy,str(jar),str(stub)]+pins+[shadows['com/apple/xsr/net/AcpxConnection.class'],str(fixtures),classes['com/apple/xsr/net/WorkerExitObservation.class'],classes['fixture/OfflineGuard.class'],classes['com/apple/xsr/net/WorkerExitObservation$SyntheticFault.class'],shadows['com/apple/xsr/net/AcpxConnection$1.class']],timeout=25,require_empty_stderr=True).splitlines()
      expected=['worker_exit '+mode+' ownership='+str(policy=='fixed-ownership').lower()+' actual_worker_dead=true stopped=false caller_waiting=true queue='+str(int(mode=='callback-error'))+' outcome=unfixed','PASS worker exit characterization; guarded_operations=0; fixture cleanup only']
      if lines!=expected:raise ValueError('Worker exit vector differs; timeout/error cannot qualify')
      observations.append({'architecture':arch,'execution':execution,'policy':policy,'scenario':mode,'jar_sha256':sha(jar),'manager_class_sha256':pins[0],'sender_class_sha256':pins[1],'lines':lines})
   verify_runtime(root,lock['architectures'][arch])
 verify_jdk(a.jdk)
 if subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()!=commit or bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))!=dirty:raise ValueError('Characterization working-tree state changed')
 if any(sha(ROOT/n)!=value for n,value in hashes.items()) or sha(a.reference)!=REFERENCE:raise ValueError('Characterization input changed')
 print(json.dumps({'qualification':False,'status':'positive characterization of unfixed worker exit; fixture manually releases caller after observation','fixture_commit':commit,'fixture_dirty':dirty,'reference_jar_sha256':REFERENCE,'candidate_jar_sha256':CANDIDATE_SHA,'compiler_tree_sha256':compiler['tree_sha256'],'source_hashes':hashes,'fixture_class_hashes':classes,'shadow_class_hashes':shadows,'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'observations':observations,'limits':'Memory transport and Unsafe constructor bypass only. Original and ownership experiment both fail terminal completion; no product fix is demonstrated here. Actual worker error identity, death, stopped=false and exact waiting Sender positively observed. Fixture manually answers after evidence collected. No controller or production volume contact; x64 is Rosetta.'},indent=2))
if __name__=='__main__':main()
