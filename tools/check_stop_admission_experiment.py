#!/usr/bin/env python3
"""Reproducible local stop-admission qualification; never a release gate."""
import argparse,hashlib,json,os,subprocess,tempfile,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from audit_support import ROOT,sha,run_jdk,verify_jdk,verify_python,isolated_env
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact
from inventory import disassemble_entries
from stop_admission_structure import normalize_stop_admission
import stop_admission_fixtures,stop_exposure_fixtures
REFERENCE='9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562'
SOURCES=('tests/java/com/apple/xsr/net/StopAdmissionObservation.java','tests/java/com/apple/xsr/net/StopExposureObservation.java','tests/java/com/apple/xsr/net/StopActiveObservation.java','tests/java/stopfixture/AcpxConnection.java','tests/java/fixture/OfflineGuard.java','tests/java/fixture/FixtureIdentity.java','tools/check_stop_admission_experiment.py','tools/stop_admission_patch.py','tools/stop_admission_structure.py','tools/stop_admission_fixtures.py','tools/stop_exposure_fixtures.py','tools/class_patch.py','tools/socket_configuration_patch.py','tools/connection_publication_patch.py','tools/socket_configuration_structure.py','patches/compat/SocketConfiguration.java','tools/sync_ownership_patch.py','tools/worker_exit_patch.py','tools/check_security.py','tools/inventory.py','tools/sync_ownership_structure.py','tools/audit_support.py','tools/verify_builds.py','tools/runtime.py','audit/runtime-lock.json','audit/python-lock.json','audit/jdk-lock.json','tests/fixtures/guarded-worker-candidate-manager.javap','tests/fixtures/stop-admission-candidate-manager.javap','tests/fixtures/sync-ownership-candidate-sender.javap','tests/test_stop_admission.py','audit/expected-build.json','audit/security-patches.json','audit/stop-admission-clean-stop.json')
def state():
 return (subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',required=True,type=Path);p.add_argument('--runtime',required=True,type=Path,action='append');p.add_argument('--development',action='store_true');p.add_argument('--candidate',required=True,type=Path);p.add_argument('--candidate-sha256',required=True);p.add_argument('reference',type=Path);a=p.parse_args();os.chdir(ROOT)
 verify_python();compiler=verify_jdk(a.jdk);initial=state()
 if initial[1] and not a.development:raise ValueError('Clean experiment source required')
 reference=a.reference.resolve()
 if a.reference.is_symlink() or sha(reference)!=REFERENCE:raise ValueError('Audit21 reference differs')
 reference_manifest=json.loads((reference.parents[3]/'provenance.json').read_text())
 if reference_manifest['source_dirty']:raise ValueError('Reference source dirty')
 candidate=a.candidate.resolve()
 if a.candidate.is_symlink() or sha(candidate)!=a.candidate_sha256:raise ValueError('Candidate identity differs')
 identity,manifest=check_artifact(candidate.parents[3])
 if identity!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected'] or (manifest['source_dirty'] and not a.development):raise ValueError('Candidate source or expected identity differs')
 with zipfile.ZipFile(reference) as z:old={n:z.read(n) for n in z.namelist()}
 with zipfile.ZipFile(candidate) as z:new={n:z.read(n) for n in z.namelist()}
 entry='com/apple/xsr/net/CommunicationsManager.class'
 from socket_configuration_patch import ENTRY as HTTP,normalize as normalize_socket
 from connection_publication_patch import ENTRY as ACPX,normalize as normalize_publication
 helper='compat/SocketConfiguration.class'
 if set(new)-set(old)!={helper} or set(old)-set(new) or {n for n in old if old[n]!=new[n]}!={entry,HTTP,ACPX}:raise ValueError('Candidate differs beyond stop guard and socket setup')
 if normalize_publication(new[ACPX])!=old[ACPX]:raise ValueError('Acpx publication predecessor differs')
 if normalize_socket(new[HTTP])!=old[HTTP]:raise ValueError('Socket setup predecessor differs')
 with tempfile.TemporaryDirectory(prefix='raid-stop-helper-check-') as checkdir:
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-d',checkdir,str(ROOT/'patches/compat/SocketConfiguration.java')],require_empty_stderr=True)
  if (Path(checkdir)/helper).read_bytes()!=new[helper]:raise ValueError('Socket helper differs from source')
 from stop_admission_patch import plan,normalize
 prototype=plan(old[entry]);manager_sha=hashlib.sha256(prototype).hexdigest()
 if prototype!=new[entry] or normalize(prototype)!=old[entry] or manager_sha!=json.loads((ROOT/'audit/security-patches.json').read_text())[entry]['patched_sha256']:raise ValueError('Shipped prototype linkage differs')
 hashes={name:sha(ROOT/name) for name in SOURCES};lock=runtime_manifest();runtimes=[];seen=set();records=[]
 for root in a.runtime:
  matches=[]
  for arch in ('aarch64','x64'):
   try:verify_runtime(root,lock['architectures'][arch]);matches.append(arch)
   except ValueError:pass
  if len(matches)!=1 or matches[0] in seen:raise ValueError('Runtime identity differs')
  seen.add(matches[0]);runtimes.append((root,matches[0]))
 if seen!={'aarch64','x64'}:raise ValueError('Both locked architectures required')
 with tempfile.TemporaryDirectory(prefix='raid-stop-admission-experiment-') as temporary:
  tmp=Path(temporary);stub=tmp/'stub';stub.mkdir()
  historical=json.loads((ROOT/'audit/stop-admission-clean-stop.json').read_text())
  historical_hashes={}
  for label,builder in (('admission',stop_admission_fixtures),('exposure',stop_exposure_fixtures)):
   folder=tmp/('historical-'+label);folder.mkdir()
   for policy,jar in builder.build(reference,folder).items():
    expected={r['fixture_jar_sha256'] for r in historical['observations'] if r['scenario'].startswith(label+':') and r['policy']==policy}
    if expected!={sha(jar)}:raise ValueError('Historical default fixture bytes differ from frozen audit22 evidence')
    historical_hashes[label+'-'+policy]=sha(jar)
  run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(reference),'-d',str(stub),'tests/java/stopfixture/AcpxConnection.java'])
  shadows={str(v.relative_to(stub)):sha(v) for v in stub.rglob('*.class')}
  if set(shadows)!={'com/apple/xsr/net/AcpxConnection.class','com/apple/xsr/net/AcpxConnection$1.class'}:raise ValueError('Memory shadow class allowlist differs')
  for label,builder,kinds in [('admission',stop_admission_fixtures,('sync','async')),('exposure',stop_exposure_fixtures,('sync','async','sync-interrupted','sync-queue','async-queue','sync-flag','async-flag','sync-mutating','async-mutating')),('active',None,('sync','async'))]:
   directory=tmp/label;directory.mkdir();fixtures=directory/'fixtures';fixtures.mkdir();name='StopAdmissionObservation' if label=='admission' else 'StopExposureObservation' if label=='exposure' else 'StopActiveObservation'
   run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(stub)+':'+str(reference),'-d',str(fixtures),'tests/java/fixture/OfflineGuard.java','tests/java/fixture/FixtureIdentity.java','tests/java/com/apple/xsr/net/'+name+'.java'])
   classes={str(v.relative_to(fixtures)):sha(v) for v in fixtures.rglob('*.class')}
   if set(classes)!={'fixture/OfflineGuard.class','fixture/FixtureIdentity.class','com/apple/xsr/net/'+name+'.class'}:raise ValueError('Compiled fixture allowlist differs')
   variants=builder.build(reference,directory,basis=candidate) if builder is not None else {'legacy':reference,'guarded':candidate}
   for policy,jar in variants.items():
    with zipfile.ZipFile(jar) as z:app={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith('.class') and (n.startswith('compat/') or n in ('com/apple/xsr/net/CommunicationsManager.class','com/apple/xsr/net/CommunicationsManager$SyncSender.class','com/apple/xsr/net/CommunicationsManager$Transaction.class'))}
    rows=[]
    for mapping,location in ((classes,fixtures),(shadows,stub),(app,jar)):rows.extend(n[:-6].replace('/','.')+'\t'+str(location)+'\t'+h for n,h in sorted(mapping.items()))
    idfile=directory/'identity.tsv';idfile.write_text('\n'.join(rows)+'\n')
    for root,arch in runtimes:
     for execution in ('-Xint','-Xcomp'):
      for kind in kinds:
       jit=directory/(policy+'-'+arch+'-'+execution[1:]+'-'+kind+'-jit.xml')
       flags=[execution]+(['-XX:+UnlockDiagnosticVMOptions','-XX:+LogCompilation','-XX:LogFile='+str(jit),'-XX:CompileCommand=quiet','-XX:CompileCommand=compileonly,com/apple/xsr/net/CommunicationsManager.dispatchLoop'] if execution=='-Xcomp' else [])
       lines=run_jdk(root/'Contents/Home','java',flags+['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(tmp),'-Dfixture.identitymanifest='+str(idfile),'-cp',str(fixtures)+':'+str(stub)+':'+str(jar),'com.apple.xsr.net.'+name,kind]+([policy] if label!='active' else []),timeout=35,require_empty_stderr=True).splitlines()
       expected='PASS stop-'+label+' '+kind+' '+policy+' attempts='+('0' if policy=='guarded' else '1')+' memory only; forbidden_attempts=0'
       if label=='active':expected='PASS stop-active '+kind+' characterization; claimed_before_serialization_completes=true stop_before_release=true attempts=1 real_reply_preserved=true no_replay=true forbidden_attempts=0'
       if lines!=[expected]:raise ValueError('Exact stop experiment outcome differs')
       compiled=[]
       if execution=='-Xcomp':
        log=ET.parse(jit).getroot();compiled=[dict(n.attrib) for n in log.iter('nmethod') if 'CommunicationsManager dispatchLoop ()V' in n.get('method','')]
        failures=[dict(n.attrib) for task in log.iter('task') if 'CommunicationsManager dispatchLoop ()V' in task.get('method','') for n in task.iter('failure')]
        if not compiled or failures:raise ValueError('Dispatch compilation not verified '+label+':'+kind+' '+arch+' '+policy+' nmethods='+str(len(compiled))+' reasons='+','.join(n.get('reason','unknown') for n in failures))
       records.append({'architecture':arch,'execution':execution,'scenario':label+':'+kind,'policy':policy,'fixture_jar_sha256':sha(jar),'identity_manifest_sha256':sha(idfile),'fixture_classes':classes,'shadow_classes':shadows,'dispatch_compilation':compiled,'execution_flags':flags,'lines':lines})
  # The product prototype is checked independently without a test-only hook.
  from stop_admission_patch import plan
  with zipfile.ZipFile(reference) as z:data=plan(z.read('com/apple/xsr/net/CommunicationsManager.class'))
  prototype=tmp/'prototype.jar'
  with zipfile.ZipFile(prototype,'w') as z:z.writestr('com/apple/xsr/net/CommunicationsManager.class',data)
  normalize_stop_admission(disassemble_entries(a.jdk,prototype,['com/apple/xsr/net/CommunicationsManager.class'],verbose=True),True)
 for root,arch in runtimes:verify_runtime(root,lock['architectures'][arch])
 verify_jdk(a.jdk)
 if state()!=initial or sha(reference)!=REFERENCE or sha(candidate)!=a.candidate_sha256 or any(sha(ROOT/name)!=h for name,h in hashes.items()):raise ValueError('Experiment source changed during execution')
 print(json.dumps({'qualification':not a.development,'purpose':'Local stop-admission software qualification; not release, controller or native GUI acceptance','fixture_commit':initial[0],'fixture_dirty':initial[1],'candidate_sha256':sha(candidate),'candidate_manager_sha256':manager_sha,'jar_delta_from_reference':sorted(n for n in old.keys()|new.keys() if old.get(n)!=new.get(n)),'historical_default_fixture_hashes':historical_hashes,'application_reference_sha256':REFERENCE,'source_commit':manifest['source_commit'],'source_dirty':manifest['source_dirty'],'application_reference_source_commit':reference_manifest['source_commit'],'compiler_tree_sha256':compiler['tree_sha256'],'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'source_hashes':hashes,'observations':records,'compilation_policy':'Xcomp variants compile only dispatchLoop and require its installed nmethod; dispatchLoop is the only Java method selected by compileonly; unrelated compiled VM helpers and native wrappers are not inventoried. Xint variants use full interpreter. This is method compilation evidence, not native GUI or whole-application compiled execution qualification.','limits':'Memory-only forced seams with actual Manager/SyncSender classes but synthetic constructor bypass. Admission/exposure hook variants retain every non-Manager entry of the actual candidate; their legacy Manager is the exact audit21 predecessor. Hook reversal recovers the intended Manager bytes. Active controls use unmodified audit21 reference and shipped candidate. Separate HttpConnection/helper and private Acpx delta is independently validated; no hooks enter product packaging. No controller, real credentials/profiles, mounted volume, native GUI, installed app or TCP receipt claim. Guard-only stop branch targets280 and constructs unsent response independently of connectionFailureSent; artificial stale-flag controls supplement source and original reported-failure gates. After-admission controls use the actual shipped JAR without a hook; deadlines unresolved.'},indent=2))
if __name__=='__main__':main()
