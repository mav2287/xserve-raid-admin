#!/usr/bin/env python3
"""Observe APFS aliases and prove fixtures reject wrong hardlink destinations."""
import argparse,json,hashlib,subprocess,tempfile,re
from pathlib import Path
from audit_support import ROOT,sha,JAVA_FLAGS,isolated_env,verify_jdk,verify_python,run_jdk
from runtime import runtime_manifest,verify_runtime
from secure_build import state,command,verify_native_inputs

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-clean',action='store_true');a=p.parse_args();verify_python();verify_jdk(a.jdk);initial=state()
 if a.output.exists() or not a.output.resolve().is_relative_to((ROOT/'build').resolve()):raise ValueError('New name fixture output required')
 source=ROOT/'modernization/private-preferences';native=(source/'native/private_file.c').read_text();manifest=json.loads((a.build/'provenance.json').read_text());jar=a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
 if sha(jar)!=manifest['jar_sha256'] or (a.require_clean and (initial['dirty'] or manifest['source_dirty'])):raise ValueError('Name product identity/source differs')
 verify_native_inputs(manifest);files=sorted((source/'tests').glob('*.java'));inputs={str(f.relative_to(ROOT)):sha(f) for f in files+sorted((ROOT/'tools').glob('*.py'))+[source/'native/private_file.c']};a.output.mkdir();classes=a.output/'classes';classes.mkdir();run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(jar),'-d',str(classes)]+list(map(str,files)));probes={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}
 marker='s->target_present = 1; s->target_device = target.st_dev; s->target_inode = target.st_ino;'
 if native.count(marker)!=1:raise ValueError('Wrong-target mutation window differs')
 mutated=native.replace(marker,'''/* TEST ONLY: deliberately redirect a save to another link of the same inode. */
        if (!strcmp(s->base, "hard-target")) {
            char *wrong = strdup("hard-backup");
            if (!wrong) { int cleaned = consume(s, 0); fail_cleanup(env, "atomic-allocation", 0, cleaned); return; }
            free(s->base); s->base = wrong;
        }
        '''+marker)
 clang=command(['/usr/bin/xcrun','--find','clang']).decode().strip();sdk=command(['/usr/bin/xcrun','--show-sdk-path']).decode().strip();lock=runtime_manifest();rows=[];negatives=[];outputs={};runtime_inputs=[]
 def layout(folder,lib):
  resources=folder/'RAID Admin.app/Contents/Resources';resources.mkdir(parents=True);candidate=resources/'RAID_Admin.jar';candidate.write_bytes(jar.read_bytes());frameworks=resources.parent/'Frameworks';frameworks.mkdir();library=frameworks/'libPrivatePreference.dylib';library.write_bytes(lib.read_bytes());outputs[str(candidate.relative_to(a.output))]=sha(candidate);outputs[str(library.relative_to(a.output))]=sha(library);return candidate.resolve(),library.resolve()
 def execute(runtime,candidate,library,scenario,mode):
  with tempfile.TemporaryDirectory(prefix='name-targets-',dir=a.output) as directory:
   root=Path(directory).resolve();argv=[runtime/'Contents/Home/bin/java']+JAVA_FLAGS+[mode,'-Xverify:all','-Xms256m','-Xmx256m','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(root/'fake-home'),'-Dfixture.directory='+str(root),'-Dfixture.candidate='+str(candidate),'-Dfixture.allowed.library='+str(library),'-Dfixture.scenario='+scenario,'-cp',str(classes.resolve())+':'+str(candidate),'atomiccaller.NameGuardObservation'];return subprocess.run(list(map(str,argv)),cwd=root,env=isolated_env(),capture_output=True,timeout=120)
 for folder,arch,cpu in [('arm64','aarch64','arm64'),('x64','x64','x86_64')]:
  runtime=ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(runtime,lock['architectures'][arch]);runtime_inputs.append((runtime,arch));normal=a.build/manifest['native_helpers'][arch]['path']
  if sha(normal)!=manifest['native_helpers'][arch]['sha256']:raise ValueError('Normal native changed')
  candidate,library=layout(a.output/(arch+'-normal-layout'),normal)
  for scenario in ['alias','hard']:
   for mode in ['-Xint','-Xcomp']:
    result=execute(runtime,candidate,library,scenario,mode);expected=('PASS name guard '+scenario+'; requested_target=true; foreign_inode_protected=true\n').encode()
    if result.returncode or result.stdout!=expected or result.stderr:raise RuntimeError('Name product fixture failed; raw diagnostics withheld')
    rows.append({'architecture':arch,'mode':mode,'scenario':scenario,'native_sha256':sha(normal),'stdout':result.stdout.decode().strip(),'scope':'Alias is observed filesystem behavior; hardlink backup bytes/inode are asserted'})
  folder=a.output/(arch+'-wrong-target');folder.mkdir();c=folder/'private_file.c';c.write_text(mutated);bad=folder/'libPrivatePreference.dylib';flags=[clang,'-target',cpu+'-apple-macos11.0','-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fvisibility=hidden','-dynamiclib','-Wl,-install_name,@rpath/libPrivatePreference.dylib','-I'+str(a.jdk/'include'),'-I'+str(a.jdk/'include/darwin'),c];command(flags+['-o',bad]);repeat=folder/'repeat.dylib';command(flags+['-o',repeat])
  if sha(bad)!=sha(repeat):raise ValueError('Wrong-target native repeat differs')
  outputs[str(c.relative_to(a.output))]=sha(c);outputs[str(bad.relative_to(a.output))]=sha(bad);candidate,library=layout(a.output/(arch+'-wrong-target-layout'),bad);result=execute(runtime,candidate,library,'hard','-Xint');prefix=b'Exception in thread "main" java.lang.AssertionError: name-guard:hard-target-bytes\n'
  if result.returncode!=1 or result.stdout or not result.stderr.startswith(prefix) or not re.fullmatch(rb'(?:\tat atomiccaller\.NameGuardObservation\.(?:check|main)\(NameGuardObservation\.java:\d+\)\n){2}',result.stderr[len(prefix):]):raise ValueError('Wrong-target negative failed unexpectedly')
  negatives.append({'architecture':arch,'mutation':'save-to-other-hardlink','assertion':'name-guard:hard-target-bytes','native_sha256':sha(bad),'mutated_source_sha256':sha(c),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
 for runtime,arch in runtime_inputs:verify_runtime(runtime,lock['architectures'][arch])
 verify_jdk(a.jdk);verify_native_inputs(manifest)
 if state()!=initial or sha(jar)!=manifest['jar_sha256'] or any(sha(ROOT/n)!=h for n,h in inputs.items()) or any(sha(a.output/n)!=h for n,h in outputs.items()) or probes!={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}:raise ValueError('Name fixture inputs changed')
 record={'qualification':False,'scope':'Actual public private-save helper; APFS alias observation and wrong-hardlink rejection control; disposable files only','source_commit':initial['commit'],'source_dirty':initial['dirty'],'clean_execution':a.require_clean,'product_jar_sha256':sha(jar),'inputs':inputs,'outputs':outputs,'probe_hashes':probes,'observations':rows,'negative_controls':negatives,'limits':['Alias spelling is environment-specific, not a product guard','No GUI/hardware/production profile; x64 uses Rosetta']};(a.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS name fixtures; observations='+str(len(rows))+'; negatives='+str(len(negatives)))
if __name__=='__main__':main()
