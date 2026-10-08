#!/usr/bin/env python3
"""Guarded before/after information clicks, exact events and mixed icon/model transitions."""
import sys,subprocess,json,hashlib,zipfile,re,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_support import ROOT,run_jdk,isolated_env,JAVA_FLAGS,sha,verify_jdk,verify_python
from array_responsiveness_build import check_responsiveness_artifact
from secure_build import state
from runtime import runtime_manifest,verify_runtime
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
verify_python();verify_jdk(a.jdk);initial=state();root=ROOT;out=a.output.resolve()
if initial['dirty'] or out.exists() or (root/'build').is_symlink() or not out.is_relative_to((root/'build').resolve()):raise ValueError('Clean source and fresh output required')
identity,product,_=check_responsiveness_artifact(a.build);out.mkdir();(out/'fake-home').mkdir()
base=(a.build/'audit29-reference/RAID Admin.app/Contents/Resources/RAID_Admin.jar').resolve();candidate=(a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar').resolve()
classes=out/'classes';classes.mkdir();sources=[root/'tests/java/uifixture/ArrayClickObservation.java',root/'tests/java/fixture/OfflineGuard.java',root/'tests/java/fixture/FixtureIdentity.java']
run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(base),'-d',str(classes)]+list(map(str,sources)))
inputs={str(f.relative_to(root)):sha(f) for f in sources+[Path(__file__).resolve(),root/'tools/audit_support.py',root/'audit/runtime-lock.json',root/'audit/jdk-lock.json',root/'audit/python-lock.json']}
probes={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')};rows=[]
for arch,expected in [('aarch64','aarch64'),('x64','x86_64')]:
 runtime=root/f'build/secure-release-{arch}-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk';spec=runtime_manifest()['architectures'][arch];verify_runtime(runtime,spec)
 for variant,jar in [('before',base),('after',candidate)]:
  manifest=out/(arch+'-'+variant+'.tsv');lines=['\t'.join([str(p.relative_to(classes)).replace('/','.').removesuffix('.class'),str(classes),sha(p)]) for p in classes.rglob('*.class')]
  with zipfile.ZipFile(jar) as z:
   for n in z.namelist():
    if n.endswith('.class') and (n.startswith('com/apple/xsr/SystemInfoPane') or n.startswith('com/apple/xsr/DriveSelectionPanel') or n.startswith('com/apple/xsr/ArraySelectionPanel') or n.startswith('compat/InfoSelectionClick') or n in ['compat/ArrayInfoSelection.class','com/apple/xsr/Resources.class','com/apple/gui/GUIFactory.class','com/apple/xsr/SelectableLabel.class','com/apple/xsr/SelectableStatusLabel.class']):lines.append('\t'.join([n.replace('/','.').removesuffix('.class'),str(jar),hashlib.sha256(z.read(n)).hexdigest()]))
  manifest.write_text('\n'.join(lines)+'\n')
  java=root/f'build/secure-release-{arch}-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk/Contents/Home/bin/java'
  argv=[str(java)]+JAVA_FLAGS+['-Xint','-Xverify:all','-Xms128m','-Xmx256m','-Djava.awt.headless=true','-Draid.admin.gui=false','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(out/'fake-home'),'-Dfixture.responsive='+str(variant=='after').lower(),'-Dfixture.fixed=true','-Dfixture.requireFixed=true','-Dfixture.offscreen=true','-Dfixture.expectedArch='+expected,'-Dfixture.identitymanifest='+str(manifest),'-cp',str(classes)+':'+str(jar),'uifixture.ArrayClickObservation']
  r=subprocess.run(argv,cwd=out,env=isolated_env(),capture_output=True,timeout=120)
  (out/(arch+'-'+variant+'.stdout')).write_bytes(r.stdout);(out/(arch+'-'+variant+'.stderr')).write_bytes(r.stderr)
  if r.returncode or r.stderr:raise ValueError('Fixture failed '+arch+' '+variant)
  first=r.stdout.decode().splitlines()[0];m=re.fullmatch(r'OBSERVATION inside_ns=(\d+) outside_ns=(\d+) mode_ns=(\d+) trace=(.*)',first)
  if not m or len(r.stdout.decode().splitlines())!=2 or r.stdout.decode().splitlines()[1]!='PASS array transitions; rounds=300; offscreen=true; fixed=true; valid_ids_preserved=true; raw_detail_selection_preserved=true; setter_once=true; radio_card_preserved=true; mode_transition=true; model_unchanged=true; forbidden_operations=0':raise ValueError('Fixture output differs')
  rows.append(dict(arch=arch,variant=variant,runtime_tree_sha256=spec['tree_sha256'],identity_manifest_sha256=sha(manifest),jar_sha256=sha(jar),inside_ns=int(m[1]),outside_ns=int(m[2]),mode_ns=int(m[3]),trace=m[4]))
 verify_runtime(runtime,spec)
for arch in ['aarch64','x64']:
 before,after=[r for r in rows if r['arch']==arch]
 if before['trace']!=after['trace'] or min(before['inside_ns'],before['outside_ns'],before['mode_ns'],after['outside_ns'])<68000000:raise ValueError('Event parity or default press timing differs')
if state()!=initial or check_responsiveness_artifact(a.build)[0]!=identity or any(sha(root/n)!=h for n,h in inputs.items()) or {str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}!=probes:raise ValueError('Inputs changed')
(out/'results.json').write_text(json.dumps({'qualification':False,'fixture_commit':initial['commit'],'fixture_dirty':False,'product_source_commit':product['source_commit'],'inputs':inputs,'probes':probes,'runs':rows,'limits':['Headless interpreted; no native presentation qualification','x64 under Rosetta, not physical Intel','Synthetic ancestor; information-pane constructor not run','No real model, Main, profiles, controller, volumes or installed app']},indent=2)+'\n')

print('PASS four runs; exact listener press arguments; event order identical; outside/default sleeps preserved')
