#!/usr/bin/env python3
"""Actual packaged CodeSource/runtime fixtures and launcher byte-copy stub; never Main."""
import argparse,hashlib,json,os,subprocess,tempfile,sys
from pathlib import Path
from audit_support import ROOT,JAVA_FLAGS,isolated_env,sha,tree,modes,verify_python
from runtime import verify_runtime,runtime_manifest,directory_modes
from secure_build import state
from historical_secure import check_historical_artifact

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify_python();initial=state()
 if initial['dirty'] or a.output.exists() or not a.output.resolve().is_relative_to((ROOT/'build').resolve()):raise ValueError('Clean source and new packaged fixture output required')
 identity,source,bridge=check_historical_artifact(a.build)
 apple=ROOT/'original/RAID_Admin_original.jar'
 if sha(a.reference)!=source['audit27_jar_sha256'] or sha(apple)!=source['original_jar_sha256']:raise ValueError('Packaged fixture reference JAR identity differs')
 manifest=json.loads((a.package/'provenance.json').read_text());app=a.package/'RAID Admin.app';arch=manifest['bundled_runtime']['architecture'];runtime=app/'Contents/PlugIns/Runtime.jdk';jar=app/'Contents/Resources/RAID_Admin.jar';library=app/'Contents/Frameworks/libPrivatePreference.dylib';classes=a.fixtures/'classes';fixture=json.loads((a.fixtures/'observations.json').read_text());lock=runtime_manifest()
 if sha(a.fixtures/'observations.json')!='0a5df9c77bcd1a307fc135a8521f7f9ce26eafe7180fca2379a169102c27570d':raise ValueError('Unrecognized historical clean fixture manifest')
 for name,h in fixture['inputs'].items():
  if name.startswith('/') or '..' in Path(name).parts:raise ValueError('Unsafe fixture provenance path')
  data=subprocess.check_output(['/usr/bin/git','show',fixture['source_commit']+':'+name],cwd=ROOT,env=isolated_env())
  if hashlib.sha256(data).hexdigest()!=h or sha(ROOT/name)!=h:raise ValueError('Historical fixture source differs')
 if manifest['source_dirty'] or manifest['packager_dirty'] or fixture['source_dirty'] or fixture['source_commit']!=manifest['source_commit'] or manifest['packager_commit']!=initial['commit'] or manifest['source_commit']!=source['source_commit'] or manifest['source_provenance_sha256']!=sha(a.build/'provenance.json') or manifest['jar_sha256']!=source['jar_sha256'] or manifest['historical_product_bridge']!=bridge or not fixture['clean_execution'] or fixture['product_jar_sha256']!=manifest['jar_sha256'] or {str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}!=fixture['probe_hashes']:raise ValueError('Clean packaged probe/product identity differs')
 expected_inputs={str(f.relative_to(ROOT)):sha(f) for f in sorted((ROOT/'tools').glob('*.py'))+[ROOT/'audit/sbom.json',ROOT/'audit/spdx-validator-lock.json',ROOT/'audit/runtime-lock.json',ROOT/'audit/spdx-2.3.1-schema.json',ROOT/'modernization/private-preferences/RAIDAdmin',ROOT/'packaging/AppIcon.png']}
 if manifest['input_hashes']!=expected_inputs:raise ValueError('Packaged release input closure differs')
 def verify():
  if sha(a.reference)!=source['audit27_jar_sha256'] or sha(apple)!=source['original_jar_sha256']:raise ValueError('Packaged fixture reference changed')
  if sha(jar)!=source['jar_sha256'] or sha(library)!=source['native_helpers'][arch]['sha256'] or sha(app/'Contents/MacOS/RAIDAdmin')!=sha(ROOT/'modernization/private-preferences/RAIDAdmin') or manifest['native_helper']!=source['native_helpers'][arch] or manifest['native_abi']!=source['native_abi']:raise ValueError('Actual packaged product/JNI/launcher differs from verified source')
  if tree(app)!=manifest['files'] or modes(app)!=manifest['file_modes'] or directory_modes(app)!=manifest['directory_modes']:raise ValueError('Packaged fixture bundle changed')
  verify_runtime(runtime,lock['architectures'][arch])
 verify();a.output.mkdir();rows=[]
 for mode in ['-Xint','-Xcomp']:
  for main,scenario,text,codes in [('atomiccaller.AtomicCallerObservation',None,'PASS atomic caller; cases=19; actual_synchronize=true; failure_retains_original=true',['RAID_ADMIN_PREFERENCES_SAVE_FAILED']),('securefixture.SecurePathObservation',None,'PASS secure paths; original_cases=22; aliases=3; hardlinks=2; path_limits=3; strict_encoding_fail_closed=true',['RAID_ADMIN_PREFERENCES_SAVE_FAILED']),('atomiccaller.BindingObservation','reporter','PASS secure binding reporter; fallback=false; primary_preserved=true',['RAID_ADMIN_PREFERENCES_SAVE_FAILED','RAID_ADMIN_PREFERENCES_COMMITTED_CLEANUP_FAILED']),('atomiccaller.BindingObservation','reporter-unavailable','PASS secure binding reporter-unavailable; fallback=false; primary_preserved=true',[]),('atomiccaller.SessionObservation',None,'PASS secure session; consumed_rules=true; duplicate_begin_rejected=true; native_entry_owns_cleanup=true',[])]:
   with tempfile.TemporaryDirectory(prefix='packaged-targets-',dir=a.output) as directory:
    root=Path(directory).resolve();argv=[runtime.resolve()/'Contents/Home/bin/java']+JAVA_FLAGS+[mode,'-Xverify:all','-Xms256m','-Xmx256m','-Draid.admin.gui=false','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(root/'fake-home'),'-Dfixture.directory='+str(root),'-Dfixture.allowed.library='+str(library.resolve()),'-Dfixture.reference='+str(a.reference.resolve()),'-Dfixture.apple.original='+str(apple.resolve()),'-Dfixture.candidate='+str(jar.resolve()),'-Dfixture.caller.candidate='+str(jar.resolve())]
    if scenario:argv.append('-Dfixture.scenario='+scenario)
    argv+=['-cp',str(classes.resolve())+':'+str(jar.resolve()),main];result=subprocess.run(list(map(str,argv)),cwd=root,env=isolated_env(),capture_output=True,timeout=120)
    if result.returncode or result.stdout.decode().strip()!=text or result.stderr.decode().splitlines()!=codes:raise RuntimeError('Packaged product fixture failed; diagnostics withheld')
    raw={os.path.relpath(parent+b'/'+name,os.fsencode(root)) for parent,dirs,files in os.walk(os.fsencode(root)) for name in dirs+files}
    if any(Path(os.fsdecode(n)).name.startswith('.xra-') for n in raw):raise ValueError('Packaged fixture private leftover')
    if main=='securefixture.SecurePathObservation' and not {b'alias-0/Foo',b'alias-1/\xc3\xa9',b'alias-2/e\xcc\x81'}<=raw:raise ValueError('Packaged stored aliases changed')
    rows.append({'mode':mode,'main':main,'scenario':scenario,'stdout':text,'stderr_fixed_codes':codes,'raw_directory_entry_hex':sorted(n.hex() for n in raw)})
 # Run the EXACT packaged launcher bytes only in a dummy bundle whose java is an argv stub.
 launcher=app/'Contents/MacOS/RAIDAdmin';stubrows=[]
 with tempfile.TemporaryDirectory(prefix='packaged-launcher-',dir=a.output) as directory:
  contents=Path(directory).resolve()/'RAID Admin.app/Contents';script=contents/'MacOS/RAIDAdmin';script.parent.mkdir(parents=True);script.write_bytes(launcher.read_bytes());script.chmod(0o755);target=contents/'Resources/RAID_Admin.jar';target.parent.mkdir();target.write_bytes(b'fixture');java=contents/'PlugIns/Runtime.jdk/Contents/Home/bin/java';java.parent.mkdir(parents=True)
  java.write_text('#!'+sys.executable+' -I\nimport json,os,sys\nif "-version" in sys.argv and "-jar" not in sys.argv:sys.exit(0)\nassert not any(os.environ.get(v) for v in ["JAVA_TOOL_OPTIONS","_JAVA_OPTIONS","JDK_JAVA_OPTIONS","CLASSPATH","JAVA_HOME","BASH_ENV","ENV","CDPATH"])\nprint(json.dumps(sys.argv[1:]))\n');java.chmod(0o755)
  for supplied,expected in [([],[]),(['-psn_1_2'],[]),(['command'],['command']),(['-psn_1_2','a b','','é','line\nbreak'],['a b','','é','line\nbreak']),(['-psn_1_2extra'],['-psn_1_2extra'])]:
   env=isolated_env();env.update({v:'synthetic' for v in ['JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_HOME','BASH_ENV','ENV','CDPATH']});result=subprocess.run([str(script)]+supplied,env=env,capture_output=True,timeout=30)
   if result.returncode or result.stderr:raise ValueError('Packaged launcher stub failed')
   argv=json.loads(result.stdout);index=argv.index('-jar');gui='false' if expected else 'true'
   if argv[index+1:]!=[str(target)]+expected or argv.count('-Draid.admin.gui='+gui)!=1:raise ValueError('Packaged launcher mode/argv differs')
   stubrows.append({'supplied':supplied,'forwarded':expected,'gui_mode':gui,'java_is_stub':True})
 verify()
 if state()!=initial or any(sha(ROOT/n)!=h for n,h in expected_inputs.items()) or check_historical_artifact(a.build)[0]!=identity or {str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}!=fixture['probe_hashes']:raise ValueError('Packaged fixture inputs changed')
 record={'qualification':False,'scope':'Exact packaged JAR/native/runtime CodeSource fixtures and exact launcher bytes in dummy argv-stub layout; never Main','product_source_commit':source['source_commit'],'packager_commit':initial['commit'],'source_dirty':False,'historical_product_bridge':bridge,'architecture':arch,'reference_sha256':sha(a.reference),'apple_original_sha256':sha(apple),'package_manifest_sha256':sha(a.package/'provenance.json'),'fixture_manifest_sha256':sha(a.fixtures/'observations.json'),'jar_sha256':sha(jar),'native_sha256':sha(library),'launcher_sha256':sha(launcher),'observations':rows,'launcher_observations':stubrows,'limits':['No actual GUI, production profiles, network, controllers, quarantine/Gatekeeper or physical Intel','Stub launcher execution does not establish application startup/functional acceptance']}
 (a.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS packaged product fixtures; architecture='+arch+'; runs=10; launcher_stubs=5')
if __name__=='__main__':main()
