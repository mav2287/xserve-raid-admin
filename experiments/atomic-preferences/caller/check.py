#!/usr/bin/env python3
"""Exercise the preserved preference caller using a nonshipping adapter JAR."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from audit_support import JAVA_FLAGS, isolated_env, run_jdk, sha, verify_jdk, verify_python
from runtime import runtime_manifest, verify_runtime

REFERENCE_SHA='e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62'
APPLE_SHA='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
RESULT='PASS atomic caller; cases=19; actual_synchronize=true; failure_retains_original=true\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--jdk',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--require-clean',action='store_true');args=parser.parse_args()
    verify_python();compiler=verify_jdk(args.jdk)
    build=ROOT/'build'
    if build.is_symlink() or not args.output.resolve().is_relative_to(build.resolve()) or args.output.resolve()==build.resolve():raise ValueError('Caller output must be inside the real repository build directory')
    if args.output.exists() or args.output.is_symlink():raise ValueError('New caller output required')
    clean=json.loads((ROOT/'audit/atomic-preference-clean.json').read_text())
    if clean['qualification'] or clean['source_dirty'] or not clean['clean_experimental_execution']:raise ValueError('Clean experiment evidence required')
    reference=ROOT/'build/preference-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar';apple=ROOT/'original/RAID_Admin_original.jar'
    if sha(reference)!=REFERENCE_SHA or sha(apple)!=APPLE_SHA:raise ValueError('Pinned reference required')
    sources={str(p.relative_to(ROOT)):sha(p) for p in sorted((HERE.parent).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/audit_support.py',ROOT/'tools/runtime.py',ROOT/'audit/atomic-preference-clean.json',ROOT/'audit/runtime-lock.json',ROOT/'audit/jdk-lock.json',ROOT/'audit/python-lock.json']})
    commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT))
    if args.require_clean:
        if dirty:raise ValueError('Clean caller source required')
        for name,expected in sources.items():
            data=subprocess.check_output(['/usr/bin/git','show',commit+':'+name],cwd=ROOT,env=isolated_env())
            if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Caller source differs from Git')
    args.output.mkdir(parents=True);classes=args.output/'classes';classes.mkdir();adapter=args.output/'adapter';adapter.mkdir()
    prior=ROOT/'build/atomic-preferences-clean-1/classes'
    for name,expected in clean['probe_hashes'].items():
        if sha(prior/name)!=expected:raise ValueError('Pinned atomic probe bytes differ')
    run_jdk(args.jdk,'javac',['-source','8','-target','8','-cp',str(prior)+':'+str(reference),'-d',str(adapter),str(HERE/'PreferenceIO.java')])
    run_jdk(args.jdk,'javac',['-source','8','-target','8','-d',str(classes),str(HERE/'AtomicCallerObservation.java')])
    for path in [reference,apple]:
        with zipfile.ZipFile(path) as archive:
            if 'META-INF/INDEX.LIST' in archive.namelist() or any(name.startswith('META-INF/versions/') for name in archive.namelist()):raise ValueError('Reference extends class loading through JAR index or versions')
            if len(archive.namelist())!=len(set(archive.namelist())):raise ValueError('Duplicate reference entry')
            if any(line.lower().startswith('class-path:') for line in archive.read('META-INF/MANIFEST.MF').decode().splitlines()):raise ValueError('Reference manifest extends classpath')
    with zipfile.ZipFile(reference) as archive:base={name:archive.read(name) for name in archive.namelist()}
    with zipfile.ZipFile(apple) as archive:apple_backend_sha=hashlib.sha256(archive.read('com/apple/util/prefs/FileBasedPreferences.class')).hexdigest()
    backend_sha=hashlib.sha256(base['com/apple/util/prefs/FileBasedPreferences.class']).hexdigest()
    if apple_backend_sha!='9a9a41cf9982b5413dddec7f73c84bd644617b417e4602b53a551589de968d6d' or backend_sha!='76935f031ec1555f7e2f267d74d32be46de8f39257d84f1fc34ae102fbdf3b5a':raise ValueError('Backend bytecode differs')
    entries=dict(base);entries['compat/PreferenceIO.class']=(adapter/'compat/PreferenceIO.class').read_bytes()
    helpers=['atomicfixture/AtomicPreferenceFile'+suffix+'.class' for suffix in ['', '$Library', '$Session']]
    for name in helpers:
        entries[name]=(prior/name).read_bytes()
        if hashlib.sha256(entries[name]).hexdigest()!=clean['probe_hashes'][name]:raise ValueError('Copied helper differs from clean experiment')
    if set(entries)-set(base)!=set(helpers) or {name for name in base if entries[name]!=base[name]}!={'compat/PreferenceIO.class'}:raise ValueError('Caller JAR delta differs')
    candidate=args.output/'caller.jar'
    with zipfile.ZipFile(candidate,'w') as archive:
        for name,value in sorted(entries.items()):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=(0o100644<<16);info.compress_type=zipfile.ZIP_STORED;archive.writestr(info,value)
    candidate_sha=sha(candidate);probe_hashes={str(p.relative_to(classes)):sha(p) for p in classes.rglob('*.class')}
    def argv_for(runtime,root,library,mode,jar,probes):
        return [str(runtime/'Contents/Home/bin/java')]+JAVA_FLAGS+[mode,'-Xverify:all','-Xms256m','-Xmx256m','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(root/'home'),'-Dfixture.directory='+str(root),'-Dfixture.atomic.library='+str(library),'-Dfixture.apple.original='+str(apple),'-Dfixture.caller.candidate='+str(jar.resolve()),'-cp',str(probes.resolve()),'atomiccaller.AtomicCallerObservation']
    def save_jar(path,values):
        with zipfile.ZipFile(path,'w') as archive:
            for name,value in sorted(values.items()):
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=(0o100644<<16);info.compress_type=zipfile.ZIP_STORED;archive.writestr(info,value)
    mutant_guards={};variants={}
    original_entries=dict(entries);original_entries['compat/PreferenceIO.class']=base['compat/PreferenceIO.class']
    original_jar=args.output/'audit27-helper.jar';save_jar(original_jar,original_entries)
    variants['audit27-helper']=(original_jar,classes,'actual-helper-chain',False)
    variants['unset-library']=(candidate,classes,'native-library-ready',True)
    for name,body,code in [
        ('swallow-error','try { atomicfixture.AtomicPreferenceFile.write(identifier,value); } catch(Error ignored) { }','catch-error-identity'),
        ('wrap-error','try { atomicfixture.AtomicPreferenceFile.write(identifier,value); } catch(Error failure) { throw new AssertionError("fixture-wrapper",failure); }','catch-error-identity'),
        ('suppress-error','try { atomicfixture.AtomicPreferenceFile.write(identifier,value); } catch(Error failure) { failure.addSuppressed(new java.io.IOException("fixture-suppressed")); throw failure; }','error-unmodified'),
        ('inplace','try(java.io.FileOutputStream output=new java.io.FileOutputStream(identifier)){java.io.OutputStreamWriter writer=new java.io.OutputStreamWriter(output,"UTF-8");com.apple.util.plist.PropertyListUtilities.writeXML(value,writer);writer.flush();}','actual-helper-chain'),
    ]:
        folder=args.output/name;folder.mkdir();source=folder/'PreferenceIO.java'
        source.write_text('package compat;public final class PreferenceIO {public static void write(String identifier,Object value)throws java.io.IOException{'+body+'}}\n')
        target=folder/'classes';target.mkdir();run_jdk(args.jdk,'javac',['-source','8','-target','8','-cp',str(prior)+':'+str(reference),'-d',str(target),str(source)])
        mutated=dict(entries);mutated['compat/PreferenceIO.class']=(target/'compat/PreferenceIO.class').read_bytes()
        jar=folder/'caller.jar';save_jar(jar,mutated);variants[name]=(jar,classes,code,False)
        mutant_guards[str(source)]=sha(source)
    observation=(HERE/'AtomicCallerObservation.java').read_text()
    for name,old_text,new_text,code in [
        ('parent-loader','new URLClassLoader(new URL[]{candidate}, null)','new URLClassLoader(new URL[]{candidate}, ClassLoader.getSystemClassLoader())','loader-isolated'),
        ('swapped-loaders','new URLClassLoader(new URL[]{reference}, null); URLClassLoader modern = new URLClassLoader(new URL[]{candidate}, null)','new URLClassLoader(new URL[]{candidate}, null); URLClassLoader modern = new URLClassLoader(new URL[]{reference}, null)','class-origin')
    ]:
        if observation.count(old_text)!=1:raise ValueError('Caller mutation target not unique')
        folder=args.output/name;folder.mkdir();source=folder/'AtomicCallerObservation.java';source.write_text(observation.replace(old_text,new_text));target=folder/'classes';target.mkdir()
        run_jdk(args.jdk,'javac',['-source','8','-target','8','-d',str(target),str(source)])
        variants[name]=(candidate,target,code,False);mutant_guards[str(source)]=sha(source)
    for jar,probes,code,unset in variants.values():
        mutant_guards[str(jar)]=sha(jar)
        for path in probes.rglob('*.class'):mutant_guards[str(path)]=sha(path)
    lock=runtime_manifest();rows=[];runtimes=[];negatives=[]
    for folder,arch in [('arm64','aarch64'),('x64','x64')]:
        runtime=ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(runtime,lock['architectures'][arch]);runtimes.append((runtime,arch))
        library=ROOT/('build/atomic-preferences-clean-1/'+arch+'-1/libAtomicPreference.dylib')
        if sha(library)!=clean['libraries'][arch]['sha256']:raise ValueError('Pinned native library differs')
        for mode in ['-Xint','-Xcomp']:
            with tempfile.TemporaryDirectory(prefix='caller-disposable-',dir=args.output) as directory:
                root=Path(directory).resolve()
                argv=argv_for(runtime,root,library,mode,candidate,classes)
                result=subprocess.run(argv,cwd=ROOT,env=isolated_env(),capture_output=True,timeout=120,umask=0o022)
                if result.returncode or result.stderr or result.stdout.decode()!=RESULT:raise RuntimeError('Caller experiment failed; raw output withheld')
                expected={'observed-old','observed-new','existing','existing-original','measured'}
                expected.update('original-'+str(i) for i in range(5));expected.update('candidate-'+str(i) for i in range(5))
                expected.update(['linked-target-false','linked-false','old-linked-target-false','old-linked-false','linked-true','old-linked-target-true','old-linked-true'])
                expected.update(prefix+str(i) for prefix in ['failed-original-','failed-candidate-'] for i in [10,11,12])
                expected.update(prefix+value for prefix in ['interrupt-old-','interrupt-new-'] for value in ['true','false'])
                if {str(p.relative_to(root)) for p in root.rglob('*')}!=expected:raise ValueError('Caller recursive directory listing differs')
                rows.append({'architecture':arch,'mode':mode,'umask':0o022,'result':result.stdout.decode().strip()})
        for name,(jar,probes,code,unset) in variants.items():
            with tempfile.TemporaryDirectory(prefix='caller-negative-',dir=args.output) as directory:
                root=Path(directory).resolve();argv=argv_for(runtime,root,library,'-Xint',jar,probes)
                if unset:argv=[item for item in argv if not item.startswith('-Dfixture.atomic.library=')]
                result=subprocess.run(argv,cwd=ROOT,env=isolated_env(),capture_output=True,timeout=120,umask=0o022)
                expected=('Exception in thread "main" java.lang.AssertionError: atomic-caller:'+code+'\n').encode()
                frames=result.stderr[len(expected):].decode() if result.stderr.startswith(expected) else ''
                if result.returncode!=1 or result.stdout or not re.fullmatch(r'(?:\tat atomiccaller\.AtomicCallerObservation\.(?:check|origin|main)\(AtomicCallerObservation\.java:\d+\)\n){2,3}',frames):raise ValueError('Caller negative failed unexpectedly; raw output withheld')
                negatives.append({'architecture':arch,'mode':'-Xint','umask':0o022,'mutation':name,'assertion_code':code,'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),'jar_sha256':sha(jar),'probe_hashes':{str(p.relative_to(probes)):sha(p) for p in probes.rglob('*.class')}})
        if sha(library)!=clean['libraries'][arch]['sha256']:raise ValueError('Native library changed')
    for runtime,arch in runtimes:verify_runtime(runtime,lock['architectures'][arch])
    verify_jdk(args.jdk)
    if any(sha(prior/name)!=expected for name,expected in clean['probe_hashes'].items()):raise ValueError('Prior helper/probe inputs changed')
    if len(rows)!=4 or len(negatives)!=16 or any(sha(Path(path))!=expected for path,expected in mutant_guards.items()) or sha(reference)!=REFERENCE_SHA or sha(apple)!=APPLE_SHA or sha(candidate)!=candidate_sha or any(sha(ROOT/name)!=expected for name,expected in sources.items()) or probe_hashes!={str(p.relative_to(classes)):sha(p) for p in classes.rglob('*.class')}:raise ValueError('Caller inputs changed')
    if subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT).decode().strip()!=commit or bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT))!=dirty:raise ValueError('Caller source commit changed')
    record={'qualification':False,'clean_experimental_execution':args.require_clean and not dirty,'source_commit':commit,'source_dirty':dirty,'scope':'Nonshipping FBC synchronize caller development; explicit disposable identifiers only','compiler_tree_sha256':compiler['tree_sha256'],'sources':sources,'apple_reference_sha256':APPLE_SHA,'audit27_reference_sha256':REFERENCE_SHA,'candidate_sha256':candidate_sha,'apple_backend_sha256':apple_backend_sha,'candidate_backend_sha256':backend_sha,'candidate_delta_scope':'ZIP entry content; archive metadata normalized','adapter_sha256':sha(adapter/'compat/PreferenceIO.class'),'candidate_delta':{'modified':['compat/PreferenceIO.class'],'added':helpers},'probe_hashes':probe_hashes,'observations':rows,'negative_controls':negatives,'mutant_guard_sha256':mutant_guards,'limits':['No application release integration or complete native ownership qualification','Original 18-case scenario types re-expectated plus zero-count case; 16 caller-specific interpreted negatives; factory/Main, GUI and real profiles still unqualified','x64 is Rosetta, not physical Intel; no hardware/production volume access']}
    (args.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS nonshipping atomic caller experiment; runs=4; cases=19; actual_synchronize=true; caller_negative_controls=16')
if __name__=='__main__':main()
