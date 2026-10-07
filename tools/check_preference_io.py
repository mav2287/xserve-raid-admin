#!/usr/bin/env python3
"""Qualify exact original save-stream ownership using disposable synthetic files."""
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,zipfile
from collections import Counter
from pathlib import Path
from audit_support import ROOT,JAVA_FLAGS,isolated_env,verify_python,verify_jdk,sha,run_jdk
from baseline import write_jar
from preference_io_patch import ENTRY,ORIGINAL_SHA,PATCHED_SHA,plan,normalize,strip_entries
from preference_io_structure import check_disassembly
from inventory import disassemble_entries
from class_patch import ClassFile
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact,EXPECTED as EXPECTED_BUILD

REFERENCE_SHA='7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158'
CANDIDATE_SHA='e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62'
RESULT='PASS preference write; cases=18; success_exception_error_fd_delta=0; interrupts_preserved=true; synthetic_files_only=true'

def entries(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or any(n.endswith('/') for n in names):raise ValueError('Preference JAR shape differs')
        return {n:z.read(n) for n in names}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',required=True,type=Path);p.add_argument('--build',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--development',action='store_true');a=p.parse_args()
    verify_python();compiler=verify_jdk(a.jdk)
    state=lambda:(subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
    initial=state()
    if initial[1] and not a.development:raise ValueError('Clean preference source required')
    java=[ROOT/n for n in ('tests/java/preferencefixture/PreferenceLifetimeObservation.java','tests/java/preferencefixture/PreferenceWriteObservation.java','tests/java/fixture/FixtureIdentity.java')]
    paths=sorted((ROOT/'tools').glob('*.py'))+sorted((ROOT/'patches').rglob('*.java'))+java+[ROOT/n for n in ('tests/test_preference_io.py','audit/preference-io-patches.json','audit/expected-build.json','audit/python-lock.json','audit/jdk-lock.json','audit/runtime-lock.json','original/RAID_Admin_original.jar')]
    sources={str(f.relative_to(ROOT)):sha(f) for f in paths}
    if a.output.exists() or a.output.is_symlink():raise ValueError('New preference output required')
    reference=ROOT/'build/model-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(reference)!=REFERENCE_SHA:raise ValueError('Pinned audit26 reference required')
    identity,product=check_artifact(a.build)
    if identity!=json.loads(EXPECTED_BUILD.read_text())['expected'] or product['source_commit']!=initial[0] or (product['source_dirty'] and not a.development):raise ValueError('Preference candidate build differs')
    jar=(a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar').resolve();candidate_sha=sha(jar);before=entries(reference);after=entries(jar)
    if candidate_sha!=CANDIDATE_SHA:raise ValueError('Preference deterministic JAR identity differs')
    if strip_entries(after)!=before or normalize(after[ENTRY])!=before[ENTRY]:raise ValueError('Preference candidate differs beyond exact extension')
    lock=json.loads((ROOT/'audit/preference-io-patches.json').read_text())
    if hashlib.sha256(after[ENTRY]).hexdigest()!=PATCHED_SHA or lock['patched_sha256']!=PATCHED_SHA or lock['original_sha256']!=ORIGINAL_SHA:raise ValueError('Preference class lock differs')
    units=subprocess.run([sys.executable,'-E','-s','-m','unittest','discover','-s','tests','-p','test_preference_io.py'],cwd=ROOT,env=isolated_env(),capture_output=True,timeout=60)
    if units.returncode or units.stdout or not re.search(rb'Ran 5 tests in [0-9.]+s\n\nOK\n$',units.stderr):raise ValueError('Preference units failed; raw withheld')
    a.output.mkdir(parents=True);probes=a.output/'probes';probes.mkdir()
    run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(jar),'-d',str(probes)]+list(map(str,java)))
    probehashes={str(f.relative_to(probes)):sha(f) for f in probes.rglob('*.class')}
    if set(probehashes)&set(after):raise ValueError('Preference probe shadows candidate')
    def manifest(target,name,values):
        path=a.output/name
        products={n:hashlib.sha256(v).hexdigest() for n,v in values.items() if n.endswith('.class') and (n.startswith('compat/') or n.startswith('com/apple/util/prefs/') or n.startswith('com/apple/util/plist/'))}
        path.write_text(''.join(n[:-6].replace('/','.')+'\t'+str(loc.resolve())+'\t'+h+'\n' for mapping,loc in ((probehashes,probes),(products,target)) for n,h in sorted(mapping.items())))
        return path
    candidate_ids=manifest(jar,'candidate-identity.tsv',after);reference_ids=manifest(reference,'reference-identity.tsv',before)
    candidate_ids_sha=sha(candidate_ids);reference_ids_sha=sha(reference_ids)
    disassemblies={}
    old=disassemble_entries(a.jdk,reference,[ENTRY],verbose=True);new=disassemble_entries(a.jdk,jar,[ENTRY],verbose=True);check_disassembly(old,new)
    for name,text in [('reference-preference.javap',old),('candidate-preference.javap',new)]:
        file=a.output/name;file.write_text(text);disassemblies[name]=sha(file)
    helper='compat/PreferenceIO.class';helper_code=ClassFile(after[helper])
    if helper_code.data[6:8]!=b'\x00\x34':raise ValueError('Preference helper version differs')
    helper_text=disassemble_entries(a.jdk,jar,[helper],verbose=True)
    calls=re.findall(r'^\s+\d+: invoke\w+\s+#\d+(?:,\s*\d+)?\s+// (?:InterfaceMethod|Method) ([^\n]+)$',helper_text,re.M)
    required=['java/io/FileOutputStream."<init>":(Ljava/io/File;)V','java/io/OutputStreamWriter."<init>":(Ljava/io/OutputStream;Ljava/lang/String;)V','com/apple/util/plist/PropertyListUtilities.writeXML:(Ljava/lang/Object;Ljava/io/Writer;)V','java/io/OutputStreamWriter.flush:()V']
    allowed=required+['java/lang/Object."<init>":()V','java/io/File."<init>":(Ljava/lang/String;)V']+['java/io/OutputStream.close:()V']*4+['java/lang/Throwable.addSuppressed:(Ljava/lang/Throwable;)V']*2
    if Counter(calls)!=Counter(allowed) or re.search(r'java/nio|java/lang/Thread',helper_text):raise ValueError('Preference helper stream semantics differ')
    helper_file=a.output/'preference-helper.javap';helper_file.write_text(helper_text);disassemblies[helper_file.name]=sha(helper_file)
    runtime_lock=runtime_manifest();runtimes=[]
    for folder,arch in [('arm64','aarch64'),('x64','x64')]:
        runtime=ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(runtime,runtime_lock['architectures'][arch]);runtimes.append((runtime,arch))
    def argv(mode,target,ids,directory,main):
        return [mode,'-Xverify:all','-Xms256m','-Xmx256m','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Dfixture.directory='+directory,'-Dfixture.reference='+str(reference.resolve()),'-Dfixture.identitymanifest='+str(ids.resolve()),'-cp',str(probes.resolve())+':'+str(target.resolve()),main]
    rows=[];controls=[];savedmask=os.umask(0o022)
    try:
        for runtime,arch in runtimes:
            for mode in ('-Xint','-Xcomp'):
                for mask in (0o022,0o077):
                    os.umask(mask)
                    with tempfile.TemporaryDirectory(prefix='synthetic-reference-',dir=a.output) as directory:
                        flags=argv(mode,reference,reference_ids,directory,'PreferenceLifetimeObservation');result=run_jdk(runtime/'Contents/Home','java',flags,timeout=120,require_empty_stderr=True)
                        expected='OBSERVE original preference IO; store_fd_delta=32; load_fd_delta=0; new_file_mode='+format(0o666&~mask,'o')+'; gc_during_measurement=0; real_profile_access=none\n'
                        if result!=expected:raise ValueError('Original preference characterization differs')
                        rows.append({'architecture':arch,'mode':mode,'umask':mask,'phase':'reference','candidate_sha256':REFERENCE_SHA,'flags':flags,'result':result.strip()})
                    with tempfile.TemporaryDirectory(prefix='synthetic-candidate-',dir=a.output) as directory:
                        flags=argv(mode,jar,candidate_ids,directory,'PreferenceWriteObservation');result=run_jdk(runtime/'Contents/Home','java',flags,timeout=120,require_empty_stderr=True)
                        if result!=RESULT+'\n':raise ValueError('Preference differential differs')
                        rows.append({'architecture':arch,'mode':mode,'umask':mask,'phase':'candidate','candidate_sha256':candidate_sha,'flags':flags,'result':result.strip()})
        os.umask(0o022)
        source=(ROOT/'patches/compat/PreferenceIO.java').read_text()
        identity_folder=a.output/'identity-helper';identity_folder.mkdir();identity_source=identity_folder/'PreferenceIO.java';identity_source.write_text(source);identity_classes=identity_folder/'classes';identity_classes.mkdir()
        run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(reference),'-d',str(identity_classes),str(identity_source)])
        identity_hashes={str(f.relative_to(identity_classes)):sha(f) for f in identity_classes.rglob('*.class')}
        if identity_hashes!=lock['helpers']:raise ValueError('Preference mutation pipeline identity differs')
        variants={
            'wrong-charset':source.replace('"UTF-8"','"ISO-8859-1"'),
            'close-writer-on-error':source.replace('PropertyListUtilities.writeXML(dictionary, writer);\n            writer.flush();','try { PropertyListUtilities.writeXML(dictionary, writer); writer.flush(); } finally { writer.close(); }'),
            'append-instead-of-truncate':source.replace('new FileOutputStream(new File(identifier))','new FileOutputStream(new File(identifier), true)'),
            'no-close':source.replace('new FileOutputStream(new File(identifier))','new FileOutputStream(new File(identifier)) { public void close() {} }'),
            'no-close-on-failure':source.replace('        try (OutputStream','        final boolean[] complete = {false};\n        try (OutputStream').replace('new FileOutputStream(new File(identifier))','new FileOutputStream(new File(identifier)) { public void close() throws IOException { if(complete[0]) super.close(); } }').replace('writer.flush();','writer.flush();complete[0]=true;'),
            'interruptible-stream':source.replace('new FileOutputStream(new File(identifier))','java.nio.channels.Channels.newOutputStream(java.nio.file.Files.newByteChannel(new File(identifier).toPath(), java.nio.file.StandardOpenOption.WRITE, java.nio.file.StandardOpenOption.CREATE, java.nio.file.StandardOpenOption.TRUNCATE_EXISTING))'),
            'clear-interrupt':source.replace('        try (OutputStream','        Thread.interrupted();\n        try (OutputStream'),
            'error-only-leak':source.replace('try (OutputStream output = new FileOutputStream(new File(identifier))) {','OutputStream output = new FileOutputStream(new File(identifier));\n        try {').replace('        }\n    }','        } catch (Exception failure) { output.close(); throw failure; }\n        output.close();\n    }'),
        }
        fixture=(ROOT/'tests/java/preferencefixture/PreferenceWriteObservation.java').read_text().splitlines()
        line_for=lambda token:next(i+1 for i,line in enumerate(fixture) if token in line)
        expected_codes={'wrong-charset':'bytes-kind-1','close-writer-on-error':'bytes-kind-5','append-instead-of-truncate':'existing-truncation','no-close':'success-fd','no-close-on-failure':'exception-fd','interruptible-stream':'interrupt-bytes-true','clear-interrupt':'interrupt-candidate-true','error-only-leak':'error-fd'}
        expected_lines={'wrong-charset':line_for('check(Arrays.equals(Files.readAllBytes(a)'), 'close-writer-on-error':line_for('check(Arrays.equals(Files.readAllBytes(a)'), 'append-instead-of-truncate':line_for('Backend now=new Backend(candidate,existing)'), 'no-close':line_for('long collections=gc()'), 'no-close-on-failure':line_for('now.state(bad(false)'), 'interruptible-stream':line_for('check(Arrays.equals(Files.readAllBytes(interruptOld)'), 'clear-interrupt':line_for('now.save();check(Thread.interrupted()'), 'error-only-leak':line_for('"error-fd"')}
        for name,text in variants.items():
            if text==source:raise ValueError('Preference negative mutation absent')
            folder=a.output/('negative-'+name);folder.mkdir();file=folder/'PreferenceIO.java';file.write_text(text);classes=folder/'classes';classes.mkdir()
            run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(reference),'-d',str(classes),str(file)])
            changed=dict(after);changed.update({str(f.relative_to(classes)):f.read_bytes() for f in classes.rglob('*.class')});target=folder/'candidate.jar';write_jar(target,changed);ids=manifest(target,'negative-'+name+'.tsv',changed)
            for runtime,arch in runtimes:
                with tempfile.TemporaryDirectory(prefix='synthetic-negative-',dir=folder) as directory:
                    flags=argv('-Xint',target,ids,directory,'PreferenceWriteObservation')
                    result=subprocess.run([str(runtime/'Contents/Home/bin/java')]+JAVA_FLAGS+flags,env=isolated_env(),capture_output=True,timeout=120)
                    check_line=line_for('static void check(boolean ok,String code)');expected=('Exception in thread "main" java.lang.AssertionError: preference write differential: '+expected_codes[name]+'\n\tat PreferenceWriteObservation.check(PreferenceWriteObservation.java:'+str(check_line)+')\n\tat PreferenceWriteObservation.main(PreferenceWriteObservation.java:'+str(expected_lines[name])+')\n').encode()
                    if result.returncode!=1 or result.stdout or result.stderr!=expected:raise ValueError('Preference negative did not fail at intended assertion; raw withheld')
                    controls.append({'architecture':arch,'mode':'-Xint','mutation':name,'flags':flags,'candidate_sha256':sha(target),'identity_manifest_sha256':sha(ids),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),'fixture_line':expected_lines[name],'assertion_code':expected_codes[name],'result':'expected preference differential assertion'})
    finally:os.umask(savedmask)
    for runtime,arch in runtimes:verify_runtime(runtime,runtime_lock['architectures'][arch])
    verify_jdk(a.jdk)
    if len(rows)!=16 or len(controls)!=16 or {(r['architecture'],r['mode'],r['umask'],r['phase']) for r in rows}!={(arch,mode,mask,phase) for _,arch in runtimes for mode in ('-Xint','-Xcomp') for mask in (0o022,0o077) for phase in ('reference','candidate')}:raise ValueError('Preference run counts differ')
    if state()!=initial or any(sha(ROOT/name)!=value for name,value in sources.items()) or sha(reference)!=REFERENCE_SHA or sha(jar)!=candidate_sha or sha(candidate_ids)!=candidate_ids_sha or sha(reference_ids)!=reference_ids_sha or check_artifact(a.build)!=(identity,product) or entries(jar)!=after or probehashes!={str(f.relative_to(probes)):sha(f) for f in probes.rglob('*.class')}:raise ValueError('Preference audit inputs changed')
    record={'qualification':not a.development,'source_commit':initial[0],'source_dirty':initial[1],'candidate_source_commit':product['source_commit'],'candidate_source_dirty':product['source_dirty'],'candidate_sha256':candidate_sha,'reference_sha256':REFERENCE_SHA,'sources':sources,'compiled_probe_hashes':probehashes,'class_identity_manifest_sha256':sha(candidate_ids),'reference_identity_manifest_sha256':sha(reference_ids),'disassemblies':disassemblies,'original_class_sha256':ORIGINAL_SHA,'patched_class_sha256':PATCHED_SHA,'helper_hashes':lock['helpers'],'observations':rows,'negative_controls':controls,'unit_tests':5,'compiler_tree_sha256':compiler['tree_sha256'],'runtime_trees':{arch:runtime_lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'scope':'One store window and one helper; all other audit26 JAR entries unchanged; original FileOutputStream, serializer, UTF-8, explicit flush, path/mode/link/interrupt/monitor/count/catch behavior preserved','limits':['Synthetic files only, explicit identifiers; no MacPreferences factory/Main/real profile/controller/network','Reference load characterization covers valid XML only; no load patch','Original mode/ACL/hard-link/symlink semantics remain; private new-file creation deferred due NIO interruption risk','No atomic replacement/fsync/encryption; original truncation on serialization failure remains','Arbitrary concurrent filesystem attackers or JVM exhaustion not qualified','x64 is Rosetta, not physical Intel; Xcomp requested only']}
    record.update(unit_stderr_sha256=hashlib.sha256(units.stderr).hexdigest(),class_major_version=int.from_bytes(after[ENTRY][6:8],'big'),helper_major_version=int.from_bytes(after[helper][6:8],'big'),mutation_pipeline_identity_hashes=identity_hashes)
    record['limits']+=['New raw close can throw on success; original catch still swallows it','Helper opens before allocating Writer, unlike original new-expression allocation order; OOM at Writer allocation can now leave a truncated file']
    (a.output/'observations.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');print('PASS preference IO gate; runs=8; cases=18; original_controls=8; negative_controls=16; units=5')

if __name__=='__main__':main()
