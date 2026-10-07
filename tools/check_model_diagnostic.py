#!/usr/bin/env python3
"""Qualify a two-window diagnostic override without constructors, profiles or controllers."""
import argparse,hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path
from audit_support import ROOT,JAVA_FLAGS,isolated_env,verify_python,verify_jdk,sha,run_jdk
from baseline import write_jar
from class_patch import ClassFile,u2,word
from sync_ownership_patch import method_code
from preference_io_patch import strip_entries as strip_preference
from model_diagnostic_patch import ENTRY,ORIGINAL_SHA,PATCHED_SHA,TOKEN,plan,normalize
from model_diagnostic_structure import check_disassembly
from inventory import disassemble_entries
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact,EXPECTED as EXPECTED_BUILD

REFERENCE_SHA='59087dceed5865b08cef4db0b554a0822837618a07e59b6fd92a2b25880e6393'
RESULT='PASS model diagnostic redaction; cases=40; original_differential=true; product_loader=true; getters_flags_observers_preserved=true; forbidden_operations=0'
ABSTRACT='com/apple/xsr/som/AbstractSystemElement.class'

def read_entries(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or any(n.endswith('/') for n in names):raise ValueError('Model fixture JAR entries differ')
        return {n:z.read(n) for n in names}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--build',type=Path);p.add_argument('--development',action='store_true');a=p.parse_args()
    verify_python();compiler=verify_jdk(a.jdk)
    if a.output.exists() or a.output.is_symlink():raise ValueError('New output directory required')
    if not a.build and not a.development:raise ValueError('Qualified gate requires an integrated build')
    reference=ROOT/'build/help-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(reference)!=REFERENCE_SHA:raise ValueError('Pinned qualified audit25 reference required')
    # Include every local Python tool dependency, not just direct imports.
    inputs=sorted((ROOT/'tools').glob('*.py'))+sorted((ROOT/'patches').rglob('*.java'))+[ROOT/n for n in ('tests/java/modelfixture/ModelDiagnosticObservation.java','tests/java/fixture/OfflineGuard.java','tests/java/fixture/FixtureIdentity.java','tests/test_model_diagnostic.py','audit/jdk-lock.json','audit/python-lock.json','audit/runtime-lock.json','audit/expected-build.json','audit/help-patches.json','audit/model-diagnostic-patches.json','audit/preference-io-patches.json','original/RAID_Admin_original.jar')]
    sources={str(f.relative_to(ROOT)):sha(f) for f in inputs}
    state=lambda:(subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
    initial=state()
    if initial[1] and not a.development:raise ValueError('Clean source required')
    before=read_entries(reference);entries=dict(before);entries[ENTRY]=plan(before[ENTRY])
    if normalize(entries[ENTRY])!=before[ENTRY] or {n for n in entries if entries[n]!=before[n]}!={ENTRY}:raise ValueError('Exact model-only overlay differs')
    a.output.mkdir(parents=True);overlay=a.output/'model-overlay.jar';write_jar(overlay,entries)
    if read_entries(overlay)!=entries:raise ValueError('Serialized model overlay differs')
    product=None;jar=overlay
    if a.build:
        artifact_identity,product=check_artifact(a.build)
        if artifact_identity!=json.loads(EXPECTED_BUILD.read_text())['expected'] or product['source_commit']!=initial[0] or (product['source_dirty'] and not a.development):raise ValueError('Integrated model build differs')
        jar=(a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar').resolve()
        if strip_preference(read_entries(jar))!=entries:raise ValueError('Integrated candidate differs beyond exact model and preference extensions')
        entries=read_entries(jar)
    artifact_sha=sha(jar);overlay_sha=sha(overlay)
    old=disassemble_entries(a.jdk,reference,[ENTRY],verbose=True);new=disassemble_entries(a.jdk,jar,[ENTRY],verbose=True);check_disassembly(old,new)
    disassemblies={}
    for name,text in [('original-model.javap',old),('candidate-model.javap',new)]:
        path=a.output/name;path.write_text(text);disassemblies[name]=sha(path)
    nested=[ABSTRACT]+['com/apple/xsr/som/'+n+'.class' for n in ('SystemController','RaidController','PowerSupply','Battery','Fan','RaidSet','Disk','HostInterface','DiskSlot')]+['com/apple/xsr/net/IPAddress.class']
    nested_text=disassemble_entries(a.jdk,reference,nested,verbose=True);nested_path=a.output/'nested-models.javap';nested_path.write_text(nested_text);disassemblies[nested_path.name]=sha(nested_path)
    nested_hashes={n:hashlib.sha256(before[n]).hexdigest() for n in nested}
    if any(entries[n]!=before[n] for n in nested):raise ValueError('Nested model changed')
    # Only actual diagnostic methods are summarized, not arbitrary constant-pool strings.
    nested_reads={}
    for entry in nested[1:]:
        text=disassemble_entries(a.jdk,reference,[entry],verbose=False)
        match=re.search(r'^  public java.lang.String paramString\(\);\n(.*?)(?=^  \S|^\})',text,re.M|re.S)
        if not match:match=re.search(r'^  public java.lang.String toString\(\);\n(.*?)(?=^  \S|^\})',text,re.M|re.S)
        if not match:raise ValueError('Nested diagnostic inventory incomplete')
        fields=re.findall(r'// Field ([^\n]+)',match[1]);nested_reads[entry]=fields
        if any(re.search(r'password|credential|secret|community|auth',field,re.I) for field in fields):raise ValueError('Nested credential diagnostic requires review')
    units=subprocess.run([sys.executable,'-E','-s','-m','unittest','discover','-s','tests','-p','test_model_diagnostic.py'],cwd=ROOT,env=isolated_env(),capture_output=True,timeout=240)
    if units.returncode or units.stdout or not re.search(rb'Ran 5 tests in [0-9.]+s\n\nOK\n$',units.stderr):raise ValueError('Model unit gate failed; raw withheld')
    probes=a.output/'probes';probes.mkdir()
    java=[ROOT/n for n in ('tests/java/modelfixture/ModelDiagnosticObservation.java','tests/java/fixture/OfflineGuard.java','tests/java/fixture/FixtureIdentity.java')]
    run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(jar),'-d',str(probes)]+[str(f) for f in java])
    probehashes={str(f.relative_to(probes)):sha(f) for f in probes.rglob('*.class')}
    if set(probehashes)&set(entries):raise ValueError('Model probes shadow candidate')
    products={n:hashlib.sha256(v).hexdigest() for n,v in entries.items() if n.endswith('.class') and (n in (ENTRY,ABSTRACT) or n.startswith('compat/'))}
    def identity(target,name,values):
        path=a.output/name
        path.write_text('\n'.join(n[:-6].replace('/','.')+'\t'+str(loc.resolve())+'\t'+h for mapping,loc in ((probehashes,probes),(values,target)) for n,h in sorted(mapping.items()))+'\n');return path
    manifest=identity(jar,'identity.tsv',products);manifest_sha=sha(manifest)
    def flags(mode,target,ids,modelhash):
        return [mode,'-Xverify:all','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Dfixture.token='+TOKEN,'-Dfixture.candidate='+str(target.resolve()),'-Dfixture.reference='+str(reference.resolve()),'-Dfixture.modelHash='+modelhash,'-Dfixture.originalHash='+ORIGINAL_SHA,'-Dfixture.abstractHash='+nested_hashes[ABSTRACT],'-Dfixture.identitymanifest='+str(ids.resolve()),'-cp',str(target.resolve())+':'+str(probes.resolve()),'modelfixture.ModelDiagnosticObservation']
    c=ClassFile(entries[ENTRY]);b,_=method_code(c,'paramString','()Ljava/lang/String;')
    mutants={'original':before[ENTRY]}
    for pc,index,name in ((156,74,'monitor-read-retained'),(190,75,'management-read-retained')):
        value=bytearray(entries[ENTRY]);value[b+14+pc:b+18+pc]=b'\x2a\xb4'+word(index);mutants[name]=bytes(value)
    empty=[i for i,(tag,value) in c.pool.items() if tag==8 and c.pool[u2(value,0)][1]==b'']
    if len(empty)!=1:raise ValueError('Empty string negative-control pool differs')
    value=bytearray(entries[ENTRY])
    for pc in (156,190):value[b+14+pc:b+18+pc]=b'\x13'+word(empty[0])+b'\x00'
    mutants['wrong-token']=bytes(value)
    mutant_paths={}
    for name,value in mutants.items():
        copy=dict(entries);copy[ENTRY]=value;path=a.output/(name+'.jar');write_jar(path,copy)
        if read_entries(path)!=copy:raise ValueError('Serialized negative-control differs')
        hashes=dict(products);hashes[ENTRY]=hashlib.sha256(value).hexdigest()
        ids=identity(path,name+'.tsv',hashes);mutant_paths[name]=(path,ids,hashes[ENTRY],sha(path),sha(ids))
    rows=[];negative=[];lock=runtime_manifest()
    for folder,arch in (('arm64','aarch64'),('x64','x64')):
        root=ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(root,lock['architectures'][arch])
        for mode in ('-Xint','-Xcomp'):
            argv=flags(mode,jar,manifest,PATCHED_SHA);output=run_jdk(root/'Contents/Home','java',argv,timeout=60,require_empty_stderr=True)
            if output.splitlines()!=[RESULT]:raise ValueError('Model observation differs; raw withheld')
            rows.append({'architecture':arch,'mode':mode,'result':RESULT,'flags':argv})
        for name,(path,ids,modelhash,jarhash,idshash) in mutant_paths.items():
            for phase in ('both','product'):
                argv=['-Dfixture.phase='+phase]+flags('-Xint',path,ids,modelhash);r=subprocess.run([str(root/'Contents/Home/bin/java')]+JAVA_FLAGS+argv,env=isolated_env(),capture_output=True,timeout=60)
                frames=re.findall(rb'^\s+at (modelfixture.ModelDiagnosticObservation\.[^\n]+)$',r.stderr,re.M)
                if r.returncode==0 or r.stdout or not r.stderr.startswith(b'Exception in thread "main" java.lang.AssertionError: model differential\n') or len(frames)!=3 or not all(frame.startswith(prefix) for frame,prefix in zip(frames,(b'modelfixture.ModelDiagnosticObservation.check(',b'modelfixture.ModelDiagnosticObservation.modelCases(',b'modelfixture.ModelDiagnosticObservation.main('))) or b'VerifyError' in r.stderr:
                    raise ValueError('Model negative control failed outside intended assertion; raw withheld')
                if sha(path)!=jarhash or sha(ids)!=idshash:raise ValueError('Model mutant changed')
                negative.append({'architecture':arch,'mode':'-Xint','phase':phase,'flags':argv,'mutation':name,'candidate_sha256':jarhash,'model_sha256':modelhash,'identity_manifest_sha256':idshash,'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'frames':[f.decode() for f in frames],'result':'expected model differential assertion'})
        verify_runtime(root,lock['architectures'][arch])
    verify_jdk(a.jdk)
    if sha(reference)!=REFERENCE_SHA or sha(jar)!=artifact_sha or sha(overlay)!=overlay_sha or sha(manifest)!=manifest_sha or read_entries(jar)!=entries or probehashes!={str(f.relative_to(probes)):sha(f) for f in probes.rglob('*.class')}:raise ValueError('Model artifact/probe changed')
    if initial!=state() or sources!={str(f.relative_to(ROOT)):sha(f) for f in inputs}:raise ValueError('Model source state changed')
    if a.build and check_artifact(a.build)!=(artifact_identity,product):raise ValueError('Integrated model build changed')
    record={'qualification':not a.development,'source_commit':initial[0],'source_dirty':initial[1],'candidate_source_commit':product['source_commit'] if product else None,'candidate_source_dirty':product['source_dirty'] if product else None,'sources':sources,'candidate_sha256':artifact_sha,'qualified_baseline_sha256':REFERENCE_SHA,'original_model_sha256':ORIGINAL_SHA,'patched_model_sha256':PATCHED_SHA,'compiled_probe_hashes':probehashes,'class_identity_manifest_sha256':manifest_sha,'disassemblies':disassemblies,'nested_model_hashes':nested_hashes,'nested_diagnostic_field_reads':nested_reads,'observations':rows,'negative_controls':negative,'unit_tests':5,'unit_stderr_sha256':hashlib.sha256(units.stderr).hexdigest(),'compiler_tree_sha256':compiler['tree_sha256'],'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for arch in ('aarch64','x64')},'scope':'Two diagnostic password reads redacted; exact locked preference extension independently reversed for audit25 comparison','limits':['Unsafe constructor bypass; manually initialized Observable and five model maps','Only synthetic password values; no credential store reads','Actual nested model diagnostics statically inventoried, fixture child map values are controlled stubs','Candidate single product loader and candidate/reference child SOM loaders exercised; parent net/log4j dependencies remain candidate bytes','No agents, Main, native GUI, profiles, persistence or sockets','Plain password memory, getters, copy constructors and HTTP unchanged','Direct password-getter logging elsewhere is outside this diagnostic repair','x64 executed under Rosetta, not physical Intel; Xcomp requested only']}
    (a.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS model diagnostic gate; four runtime/mode variants; sixteen behavioral negative controls; no controller/profile')

if __name__=='__main__':main()
