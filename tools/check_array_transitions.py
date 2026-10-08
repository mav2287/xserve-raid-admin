#!/usr/bin/env python3
"""Guarded audit29 mixed drive/array/radio transitions; no native GUI or controller."""
import argparse,hashlib,json,subprocess,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_support import ROOT,run_jdk,JAVA_FLAGS,isolated_env,sha,verify_jdk,verify_python
from array_info_build import check_array_info_artifact
from runtime import verify_runtime,runtime_manifest
from secure_build import state

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 verify_python();verify_jdk(a.jdk);initial=state();out=a.output.resolve()
 if initial['dirty'] or out.exists() or not out.is_relative_to((ROOT/'build').resolve()):raise ValueError('Clean source and fresh build output required')
 identity,product,_=check_array_info_artifact(a.build);jar=(a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar').resolve()
 if sha(jar)!='d616359dbea9fa8c9bd61f107b86e65b3563353f833a35430b314036d1a03fc6':raise ValueError('Exact audit29 required')
 out.mkdir();classes=out/'classes';classes.mkdir();(out/'fake-home').mkdir()
 src=[ROOT/'tests/java/uifixture/ArrayInfoTransitionObservation.java',ROOT/'tests/java/fixture/OfflineGuard.java',ROOT/'tests/java/fixture/FixtureIdentity.java']
 inputs={str(x.relative_to(ROOT)):sha(x) for x in src+[Path(__file__).resolve(),ROOT/'tools/audit_support.py',ROOT/'audit/jdk-lock.json',ROOT/'audit/python-lock.json',ROOT/'audit/runtime-lock.json']}
 run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(jar),'-d',str(classes)]+list(map(str,src)))
 probes={str(x.relative_to(classes)):sha(x) for x in sorted(classes.rglob('*.class'))}
 lines=['\t'.join([n.replace('/','.').removesuffix('.class'),str(classes),h]) for n,h in probes.items()]
 with zipfile.ZipFile(jar) as z:
  names=[n for n in z.namelist() if n.endswith('.class') and (n.startswith('com/apple/xsr/SystemInfoPane') or n.startswith('com/apple/xsr/DriveSelectionPanel') or n.startswith('com/apple/xsr/ArraySelectionPanel') or n in ['compat/ArrayInfoSelection.class','com/apple/xsr/Resources.class','com/apple/gui/GUIFactory.class','com/apple/xsr/SelectableLabel.class','com/apple/xsr/SelectableStatusLabel.class'])]
  for n in names:lines.append('\t'.join([n.replace('/','.').removesuffix('.class'),str(jar),hashlib.sha256(z.read(n)).hexdigest()]))
 manifest=out/'identity.tsv';manifest.write_text('\n'.join(lines)+'\n');rows=[]
 for arch,expected in [('aarch64','aarch64'),('x64','x86_64')]:
  runtime=ROOT/f'build/secure-release-{arch}-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk';spec=runtime_manifest()['architectures'][arch];verify_runtime(runtime,spec)
  for offscreen in ['false','true']:
   argv=[str(runtime/'Contents/Home/bin/java')]+JAVA_FLAGS+['-Xint','-Xverify:all','-Xms128m','-Xmx256m','-Djava.awt.headless=true','-Draid.admin.gui=false','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(out/'fake-home'),'-Dfixture.fixed=true','-Dfixture.requireFixed=true','-Dfixture.offscreen='+offscreen,'-Dfixture.expectedArch='+expected,'-Dfixture.identitymanifest='+str(manifest),'-cp',str(classes)+':'+str(jar),'uifixture.ArrayInfoTransitionObservation']
   r=subprocess.run(argv,cwd=out,env=isolated_env(),capture_output=True,timeout=120)
   text='PASS array transitions; rounds=300; offscreen='+offscreen+'; fixed=true; valid_ids_preserved=true; raw_detail_selection_preserved=true; setter_once=true; radio_card_preserved=true; mode_transition=true; model_unchanged=true; forbidden_operations=0'
   (out/f'{arch}-{offscreen}.stdout').write_bytes(r.stdout);(out/f'{arch}-{offscreen}.stderr').write_bytes(r.stderr)
   if r.returncode or r.stdout.decode().strip()!=text or r.stderr:raise ValueError('Transition fixture failed; inspect fixed-code build diagnostics')
   rows.append({'architecture':arch,'mode':'-Xint','offscreen':offscreen,'rounds':300,'stdout':text,'empty_stderr':True,'runtime_tree_sha256':spec['tree_sha256']})
  verify_runtime(runtime,spec)
 if state()!=initial or any(sha(ROOT/n)!=h for n,h in inputs.items()) or check_array_info_artifact(a.build)[0]!=identity or {str(x.relative_to(classes)):sha(x) for x in classes.rglob('*.class')}!=probes:raise ValueError('Inputs or artifact changed')
 record={'qualification':False,'fixture_commit':initial['commit'],'fixture_dirty':False,'product_source_commit':product['source_commit'],'product_jar_sha256':sha(jar),'inputs':inputs,'probes':probes,'identity_manifest_sha256':sha(manifest),'runs':rows,'limits':['Interpreted headless only; x64 is Rosetta, not physical Intel','OffScreenImage with RGBdefault is not native CGL surface upload or presentation','Synthetic detail labels; no real model, profiles, controller or app Main','Passing transitions does not qualify native paint latency']}
 (out/'results.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS 4 guarded mixed transition runs; 300 rounds each; native display latency unqualified')
if __name__=='__main__':main()
