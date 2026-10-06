#!/usr/bin/env python3
"""Headless stopped admission qualification; never starts Main or contacts RAID."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from audit_support import ROOT,sha,verify_jdk,verify_python,run_jdk,isolated_env
from baseline import verify_original,write_jar
from class_patch import normalize_stopped_admission,normalize_current_extensions,AUDIT19_MANAGER_SHA256
from inventory import disassemble_entries
from stopped_post_structure import normalize_admission
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact

ENTRY='com/apple/xsr/net/CommunicationsManager.class'
PASS='PASS stopped post observation; guarded_operations=0; no transport, profiles or production volumes'
EXPECTED={
 'async':['stopped_post async fixed=true queue=0 callbacks=1 clones=1',PASS],
 'sync':['stopped_post sync fixed=true clones=2 outcome=CommShutdownException',PASS],
 'worker':['stopped_post worker callbacks=3 clones=3 queue=0 original_thread=true',PASS],
 'concurrent':['stopped_post concurrent contexts=32 callbacks=32 clones=32 queue=0',PASS],
 'edt':['stopped_post edt deferred=true caller_lock_released=true queue=0',PASS],
 'null-clone':['stopped_post null clones=1 queue=0 edt_started=false; clone_failure identity=true monitor_released=true',PASS],
 'throwing':['stopped_post throwing fixed_log_only=true render_calls=0 callback_exception_contained=true',PASS],
 'boundary':['stopped_post boundary logger_failure_contained=true linkage_contained=true nonLinkage_Error_escaped=true fixed_signals=2',PASS],
 'boundary-unsafe':['stopped_post boundary negative_control exact_appender_escapes=2 fatal_identity=true',PASS],
 'missing-helper':['stopped_post missing_helper NoClassDefFoundError=true monitor_released=true queue=0',PASS]}
LEGACY={
 'async':['stopped_post async fixed=false queue=1 callbacks=0 clones=1',PASS],
 'sync':['stopped_post sync fixed=false clones=2 outcome=pending-sender-observed',PASS]}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',required=True,type=Path);p.add_argument('--runtime',required=True,action='append',type=Path);p.add_argument('--candidate-sha256',required=True);p.add_argument('--development',action='store_true');p.add_argument('candidate',type=Path);a=p.parse_args();verify_python();compiler=verify_jdk(a.jdk)
 commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip();dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
 if dirty and not a.development:raise ValueError('Clean fixture required')
 original=ROOT/'original/RAID_Admin_original.jar';verify_original(original)
 if a.candidate.is_symlink() or not a.candidate.is_file() or sha(a.candidate)!=a.candidate_sha256:raise ValueError('Candidate identity differs')
 identity,manifest=check_artifact(a.candidate.resolve().parents[3]);reviewed=json.loads((ROOT/'audit/stopped-post-recovery-expected.json').read_text())
 if identity!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected'] or a.candidate_sha256!=reviewed['candidate_jar_sha256']:raise ValueError('Candidate differs from reviewed artifact')
 if not a.development and manifest['source_dirty']:raise ValueError('Clean application required')
 with zipfile.ZipFile(a.candidate) as z:entries={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
 restored=normalize_stopped_admission(normalize_current_extensions(entries[ENTRY]));reference=json.loads((ROOT/'audit/stop-lock-final-integrity.json').read_text())
 if hashlib.sha256(restored).hexdigest()!=AUDIT19_MANAGER_SHA256 or reference['changed_entry_sha256_from_audit18'][ENTRY]['after']!=AUDIT19_MANAGER_SHA256:raise ValueError('Audit.19 reconstruction/ledger differs')
 before,after=[disassemble_entries(a.jdk,jar,[ENTRY],verbose=True) for jar in (original,a.candidate)];
 from worker_exit_structure import normalize_extensions
 normalize_admission(before,normalize_extensions(after),True)
 names=('tests/java/fixture/OfflineGuard.java','tests/java/com/apple/xsr/net/StoppedPostObservation.java','tools/check_stopped_post.py','tools/stopped_post_structure.py','tools/worker_exit_structure.py','tools/sync_ownership_structure.py','tools/class_patch.py','tools/sync_ownership_patch.py','tools/worker_exit_patch.py','tools/stop_admission_patch.py','tools/stop_admission_structure.py','tools/baseline.py','tools/audit_support.py','tools/runtime.py','tools/verify_builds.py','tools/inventory.py','audit/expected-build.json','audit/stopped-post-recovery-expected.json','audit/runtime-lock.json','audit/stop-lock-final-integrity.json','patches/compat/StoppedDelivery.java')
 hashes={n:sha(ROOT/n) for n in names};runtimes=[];seen=set();lock=runtime_manifest()
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
 with tempfile.TemporaryDirectory(prefix='raid-stopped-post-') as tmp:
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(a.candidate.resolve()),'-d',tmp]+[str(ROOT/n) for n in names[:2]])
  classes={str(x.relative_to(tmp)):sha(x) for x in Path(tmp).rglob('*.class')}
  expected_classes={'fixture/OfflineGuard.class','com/apple/xsr/net/StoppedPostObservation.class'}|{'com/apple/xsr/net/StoppedPostObservation$'+str(i)+'.class' for i in range(1,5)}
  if set(classes)!=expected_classes or set(classes)&set(entries):raise ValueError('Fixture class allowlist/shadowing differs')
  modified=dict(entries);modified[ENTRY]=restored;legacy=Path(tmp)/'audit19-manager-restored.jar';write_jar(legacy,modified)
  modified=dict(entries);del modified['compat/StoppedDelivery.class'];del modified['compat/StoppedDelivery$Callback.class'];missing=Path(tmp)/'missing-helper.jar';write_jar(missing,modified)
  badsource=Path(tmp)/'badsource/compat/StoppedDelivery.java';badsource.parent.mkdir(parents=True)
  source=(ROOT/'patches/compat/StoppedDelivery.java').read_text()
  old='try { Logger.getLogger(CommunicationsManager.class).error("RAID_ADMIN_STOPPED_CALLBACK_FAILED"); }\n        catch (Exception ignored) {} catch (LinkageError ignored) {}'
  if source.count(old)!=1:raise ValueError('Logging containment mutant source seam differs')
  badsource.write_text(source.replace(old,'Logger.getLogger(CommunicationsManager.class).error("RAID_ADMIN_STOPPED_CALLBACK_FAILED");'))
  badclasses=Path(tmp)/'badclasses';badclasses.mkdir()
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(a.candidate.resolve()),'-d',str(badclasses),str(badsource)])
  badentries={str(x.relative_to(badclasses)):x.read_bytes() for x in badclasses.rglob('*.class')}
  if set(badentries)!={'compat/StoppedDelivery.class','compat/StoppedDelivery$Callback.class'}:raise ValueError('Mutant helper class allowlist differs')
  modified=dict(entries);modified.update(badentries);unsafe=Path(tmp)/'logging-containment-bypass.jar';write_jar(unsafe,modified)
  for root,arch in runtimes:
   def observe(jar,mode,fixed,execution,label):
    with zipfile.ZipFile(jar) as z:class_sha=hashlib.sha256(z.read(ENTRY)).hexdigest()
    lines=run_jdk(root/'Contents/Home','java',['-Xverify:all',execution,'-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.StoppedPostObservation',mode,'fixed' if fixed else 'legacy',str(jar.resolve()),class_sha],timeout=25,require_empty_stderr=True).splitlines()
    if lines!=(EXPECTED if fixed else LEGACY)[mode]:raise ValueError('Admission vector differs; raw output withheld; timeout/verifier/error never qualifies')
    observations.append({'architecture':arch,'execution':execution,'variant':label,'scenario':mode,'jar_sha256':sha(jar),'manager_class_sha256':class_sha,'lines':lines})
   for execution in ('-Xint','-Xcomp'):
    for mode in EXPECTED:
     if mode not in ('missing-helper','boundary-unsafe'):observe(a.candidate,mode,True,execution,'candidate')
   for mode in LEGACY:observe(legacy,mode,False,'-Xint','audit19-Manager-restored')
   observe(missing,'missing-helper',True,'-Xint','helper-removed')
   observe(unsafe,'boundary-unsafe',True,'-Xint','logging-containment-removed')
   verify_runtime(root,lock['architectures'][arch])
 if any(sha(ROOT/n)!=value for n,value in hashes.items()) or sha(a.candidate)!=a.candidate_sha256:raise ValueError('Qualification input changed')
 if not a.development and subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()):raise ValueError('Clean fixture changed')
 print(json.dumps({'qualification':not a.development,'source_commit':manifest['source_commit'],'source_dirty':manifest['source_dirty'],'fixture_commit':commit,'fixture_dirty':dirty,'candidate_sha256':sha(a.candidate),'original_sha256':sha(original),'compiler_tree_sha256':compiler['tree_sha256'],'source_hashes':hashes,'fixture_class_hashes':classes,'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'observations':observations,'limits':'Real locally stopped Manager admission, worker drain and SyncSender; Unsafe bypasses constructor and no connection exists. EventQueue is headless, native GUI and third-party handlers unqualified. Async refused handlers run on EDT, may precede earlier queued callbacks and non-EDT poster return. Scheduling errors propagate; disposed AppContext can silently drop delivery. Worker exemption inherits unbounded repost loops; external -102 callbacks can cycle through EDT events, and original handlers may now show errors/update model state after stop. Production stderr emits only existing RAID_ADMIN_ERROR, internal callback signal checked by capture appender. JVM stderr is required empty for every observation. This gate excludes ownership/abnormal worker completion, checked separately by check_guarded_worker; VM failure completion, transport deadlines and stop-vs-active-send remain open. x64 is Rosetta, not physical Intel.'},indent=2))

if __name__=='__main__':main()
