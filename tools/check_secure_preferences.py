#!/usr/bin/env python3
"""Actual secure JAR/native/caller fixtures; fake homes and disposable targets only."""
import argparse,hashlib,json,os,subprocess,sys,tempfile,zipfile,re
from pathlib import Path
from audit_support import ROOT,isolated_env,sha,verify_jdk,verify_python,run_jdk,JAVA_FLAGS,tree
from runtime import runtime_manifest,verify_runtime
from secure_build import verify_native_inputs, HELPERS,BASE_SHA,entries,command,state
FAIL=b'RAID_ADMIN_PREFERENCES_SAVE_FAILED\n'
UNCONFIRMED=b'RAID_ADMIN_PREFERENCES_SAVE_UNCONFIRMED\n'
COMMITTED=b'RAID_ADMIN_PREFERENCES_COMMITTED_CLEANUP_FAILED\n'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-clean',action='store_true');a=p.parse_args();verify_python();compiler=verify_jdk(a.jdk);initial=state()
    buildroot=ROOT/'build';out=a.output.resolve()
    if buildroot.is_symlink() or a.output.exists() or a.output.is_symlink() or not out.is_relative_to(buildroot.resolve()) or out==buildroot.resolve():raise ValueError('New secure fixture output inside real build required')
    manifest=json.loads((a.build/'provenance.json').read_text());jar=a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar';base=a.build/'audit27-reference/RAID Admin.app/Contents/Resources/RAID_Admin.jar';apple=ROOT/'original/RAID_Admin_original.jar'
    if sha(jar)!=manifest['jar_sha256'] or sha(base)!=BASE_SHA or sha(apple)!='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449':raise ValueError('Secure fixture reference identity differs')
    product=entries(jar);baseline=entries(base)
    if set(product)-set(baseline)!=HELPERS-{'compat/PreferenceIO.class'} or {n for n in baseline if product[n]!=baseline[n]}!={'compat/PreferenceIO.class'} or any(hashlib.sha256(product[n]).hexdigest()!=h for n,h in manifest['helper_hashes'].items()):raise ValueError('Secure delta differs')
    for name in HELPERS:
        if any(v in product[name] for v in [b'fixture.',b'atomicfixture',b'writeWithHook']):raise ValueError('Product helper retains experimental property/hook')
    source=ROOT/'modernization/private-preferences';files=sorted((source/'tests').glob('*.java'))
    inputs={str(f.relative_to(ROOT)):sha(f) for f in sorted((ROOT/'tools').glob('*.py'))+files+[source/'native/private_file.c',ROOT/'audit/runtime-lock.json',ROOT/'audit/jdk-lock.json',ROOT/'audit/python-lock.json']}
    if a.require_clean:
        if initial['dirty'] or manifest['source_dirty']:raise ValueError('Clean secure fixture/product required')
        for n,h in inputs.items():
            if hashlib.sha256(command(['/usr/bin/git','show',initial['commit']+':'+n])).hexdigest()!=h:raise ValueError('Secure fixture source differs from Git')
    out.mkdir();classes=out/'classes';classes.mkdir();run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(jar),'-d',str(classes)]+list(map(str,files)))
    probes={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')};rows=[];runtimes=[];lock=runtime_manifest()
    verify_native_inputs(manifest)
    layout_hashes={}
    native=(source/'native/private_file.c').read_text()
    derived={}
    def compile_fault(arch,cpu,folder,changed):
        folder.mkdir();c=folder/'private_file.c';c.write_text(changed);library=folder/'libPrivatePreference.dylib';clang=command(['/usr/bin/xcrun','--find','clang']).decode().strip();sdk=command(['/usr/bin/xcrun','--show-sdk-path']).decode().strip()
        command([clang,'-target',cpu+'-apple-macos11.0','-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fvisibility=hidden','-dynamiclib','-Wl,-install_name,@rpath/libPrivatePreference.dylib','-I'+str(a.jdk/'include'),'-I'+str(a.jdk/'include/darwin'),c,'-o',library]);first=sha(library);command([clang,'-target',cpu+'-apple-macos11.0','-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fvisibility=hidden','-dynamiclib','-Wl,-install_name,@rpath/libPrivatePreference.dylib','-I'+str(a.jdk/'include'),'-I'+str(a.jdk/'include/darwin'),c,'-o',library]);
        if sha(library)!=first:raise ValueError('Derived native compilation differs')
        derived[str(library.relative_to(out))]={'sha256':first,'source_sha256':sha(c),'compiler_sha256':sha(Path(clang))};return library
    def layout(folder,library):
        resources=folder/'RAID Admin.app/Contents/Resources';resources.mkdir(parents=True);target=resources/'RAID_Admin.jar';target.write_bytes(jar.read_bytes());framework=resources.parent/'Frameworks';framework.mkdir();lib=framework/'libPrivatePreference.dylib'
        if library is not None:lib.write_bytes(library.read_bytes())
        layout_hashes[str(target.relative_to(out))]=sha(target)
        if library is not None:layout_hashes[str(lib.relative_to(out))]=sha(lib)
        return target.resolve(),lib.resolve()
    def execute(runtime,mode,candidate,library,main,scenario=None,mask=0o022):
        with tempfile.TemporaryDirectory(prefix='secure-targets-',dir=out) as directory:
            root=Path(directory).resolve();argv=[str(runtime/'Contents/Home/bin/java')]+JAVA_FLAGS+[mode,'-Xverify:all','-Xms256m','-Xmx256m','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(root/'fake-home'),'-Dfixture.directory='+str(root),'-Dfixture.allowed.library='+str(library),'-Dfixture.reference='+str(base.resolve()),'-Dfixture.apple.original='+str(apple.resolve()),'-Dfixture.candidate='+str(candidate),'-Dfixture.caller.candidate='+str(candidate),'-cp',str(classes.resolve())+':'+str(candidate),main]
            if scenario:argv=argv[:-1]+['-Dfixture.scenario='+scenario,argv[-1]]
            result=subprocess.run(argv,cwd=root,env=isolated_env(),capture_output=True,timeout=120,umask=mask)
            if result.returncode:
                code=re.search(rb'(?:secure-path|secure-binding|atomic-caller):[a-z-]+',result.stderr)
                raise RuntimeError('Secure fixture failed; assertion='+ (code.group().decode() if code else 'unclassified')+'; raw diagnostics withheld')
            if result.stderr not in [b'',FAIL,COMMITTED,FAIL+COMMITTED] or os.fsencode(str(root)) in result.stderr or b'ACP-Password' in result.stderr:raise ValueError('Uncontrolled secure diagnostic')
            raw=[]
            for parent,dirs,names in os.walk(os.fsencode(root)):
                for name in dirs+names:
                    relative=os.path.relpath(parent+b'/'+name,os.fsencode(root));raw.append(relative.hex())
                    if name.startswith(b'.xra-'):raise ValueError('Unreported private temporary remains')
            names={bytes.fromhex(v) for v in raw}
            if main=='atomiccaller.AtomicCallerObservation':
                expected={'observed-old','observed-new','existing','existing-original','measured'}
                expected.update('original-'+str(i) for i in range(5));expected.update('candidate-'+str(i) for i in range(5))
                expected.update(['linked-target-false','linked-false','old-linked-target-false','old-linked-false','linked-true','old-linked-target-true','old-linked-true'])
                expected.update(prefix+str(i) for prefix in ['failed-original-','failed-candidate-'] for i in [10,11,12])
                expected.update(prefix+v for prefix in ['interrupt-old-','interrupt-new-'] for v in ['true','false'])
                if names!={v.encode() for v in expected}:raise ValueError('Secure caller exact directory set differs')
            elif main=='securefixture.SecurePathObservation':
                for alias in [b'alias-0/Foo',b'alias-1/\xc3\xa9',b'alias-2/e\xcc\x81']:
                    if alias not in names:raise ValueError('Stored alias spelling changed')
                if any(v.startswith(b'alias-') and b'/' in v and v not in [b'alias-0/Foo',b'alias-1/\xc3\xa9',b'alias-2/e\xcc\x81'] for v in names):raise ValueError('Unexpected alias entry')
            elif main in ['atomiccaller.BindingObservation','atomiccaller.SessionObservation'] and names!={b'profile'}:raise ValueError('Secure binding exact listing differs')
            row={'mode':mode,'scenario':scenario,'main':main,'stdout':result.stdout.decode('ascii').strip(),'stderr_fixed_codes':result.stderr.decode().splitlines(),'raw_directory_entry_hex':sorted(raw),'umask_requested':mask}
            return row
    for name,arch,cpu in [('arm64','aarch64','arm64'),('x64','x64','x86_64')]:
        runtime=ROOT/('build/logging-bundled-'+name+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(runtime,lock['architectures'][arch]);runtimes.append((runtime,arch));native_record=manifest['native_helpers'][arch];library=a.build/native_record['path']
        if sha(library)!=native_record['sha256']:raise ValueError('Native product differs')
        candidate,allowed=layout(out/(arch+'-normal'),library)
        for mode in ['-Xint','-Xcomp']:
            for main,expected in [('atomiccaller.AtomicCallerObservation','PASS atomic caller; cases=19; actual_synchronize=true; failure_retains_original=true'),('securefixture.SecurePathObservation','PASS secure paths; original_cases=22; aliases=3; hardlinks=2; path_limits=3; strict_encoding_fail_closed=true')]:
                row=execute(runtime,mode,candidate,allowed,main);row['architecture']=arch
                if row['stdout']!=expected or row['stderr_fixed_codes']!=['RAID_ADMIN_PREFERENCES_SAVE_FAILED']:raise ValueError('Secure caller/path matrix differs')
                rows.append(row)
            row=execute(runtime,mode,candidate,allowed,'atomiccaller.BindingObservation','reporter');row['architecture']=arch
            if row['stdout']!='PASS secure binding reporter; fallback=false; primary_preserved=true' or row['stderr_fixed_codes']!=['RAID_ADMIN_PREFERENCES_SAVE_FAILED','RAID_ADMIN_PREFERENCES_COMMITTED_CLEANUP_FAILED']:raise ValueError('Secure reporting matrix differs')
            rows.append(row)
        for mode in ['-Xint','-Xcomp']:
            row=execute(runtime,mode,candidate,allowed,'atomiccaller.BindingObservation','reporter-unavailable');row['architecture']=arch
            if row['stdout']!='PASS secure binding reporter-unavailable; fallback=false; primary_preserved=true' or row['stderr_fixed_codes']:raise ValueError('Reporter linkage-primary preservation differs')
            rows.append(row)
        for mode in ['-Xint','-Xcomp']:
            row=execute(runtime,mode,candidate,allowed,'atomiccaller.SessionObservation');row['architecture']=arch
            if row['stdout']!='PASS secure session; consumed_rules=true; duplicate_begin_rejected=true; native_entry_owns_cleanup=true' or row['stderr_fixed_codes']:raise ValueError('Native Session lifecycle differs')
            rows.append(row)
        wrong=a.build/manifest['native_helpers']['x64' if arch=='aarch64' else 'aarch64']['path']
        if native.count('return 0x58415204;')!=1:raise ValueError('Stale mutation target differs')
        stale=compile_fault(arch,cpu,out/(arch+'-stale'),native.replace('return 0x58415204;','return 0x58415203;'))
        experimental=ROOT/('build/atomic-preferences-clean-1/'+arch+'-1/libAtomicPreference.dylib')
        if native.count('{"abort0",')!=1:raise ValueError('Registration mutation target differs')
        partial=compile_fault(arch,cpu,out/(arch+'-partial'),native.replace('{"abort0",','{"absentMethod",'))
        frozen=json.loads((ROOT/'audit/atomic-preference-clean.json').read_text())
        if sha(experimental) not in {v['library_sha256'] for v in frozen['binding_observations'] if v['scenario']=='normal' and v['architecture']==arch}:raise ValueError('Experimental native reference not pinned')
        derived[str(experimental.relative_to(ROOT))]={'sha256':sha(experimental),'source':'frozen atomic-preference-clean.json'}
        for scenario,lib in [('partial-registration',partial),('missing',None),('wrong-architecture',wrong),('stale-token',stale),('experimental',experimental)]:
            c,l=layout(out/(arch+'-'+scenario+'-layout'),lib)
            for mode in ['-Xint','-Xcomp']:
                row=execute(runtime,mode,c,l,'atomiccaller.BindingObservation',scenario);row['architecture']=arch
                if row['stdout']!='PASS secure binding '+scenario+'; fallback=false; primary_preserved=true' or row['stderr_fixed_codes']!=['RAID_ADMIN_PREFERENCES_SAVE_FAILED']:raise ValueError('Secure native binding matrix differs')
                rows.append(row)
    for n,record in derived.items():
        target=ROOT/n if n.startswith('build/') else out/n
        if sha(target)!=record['sha256']:raise ValueError('Derived library changed')
    verify_native_inputs(manifest)
    if any(sha(a.output/n)!=h for n,h in layout_hashes.items()):raise ValueError('Copied product layout changed')
    for runtime,arch in runtimes:verify_runtime(runtime,lock['architectures'][arch])
    verify_jdk(a.jdk)
    if state()!=initial or sha(jar)!=manifest['jar_sha256'] or any(sha(ROOT/n)!=h for n,h in inputs.items()) or probes!={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}:raise ValueError('Secure fixture inputs changed')
    record={'qualification':False,'scope':'Actual product helper/caller/path/binding/reporting fixture; no Main/controller/native GUI','source_commit':initial['commit'],'source_dirty':initial['dirty'],'clean_execution':a.require_clean,'product_jar_sha256':sha(jar),'product_manifest_sha256':sha(a.build/'provenance.json'),'inputs':inputs,'layout_hashes':layout_hashes,'native_input_manifest_sha256':sha(a.build/'provenance.json'),'probe_hashes':probes,'derived_libraries':derived,'observations':rows,'limits':['x64 is Rosetta, not physical Intel','No actual GUI, Gatekeeper/quarantine, other filesystems or controllers','Additional native fault/regression and package checks required']}
    (out/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS actual secure product fixtures; runs='+str(len(rows)))
if __name__=='__main__':main()
