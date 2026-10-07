#!/usr/bin/env python3
"""Offline qualification of integrated browser actions and exact qualified-core preservation."""
import argparse,hashlib,json,re,sys,tempfile,zipfile,subprocess
from audit_support import JAVA_FLAGS, isolated_env
from class_patch import ClassFile,u2
from help_structure import check_operand
from sync_ownership_patch import method_code,compose
from pathlib import Path
from audit_support import ROOT,verify_jdk,verify_python,sha,run_jdk
from baseline import write_jar
from verify_builds import check_artifact, EXPECTED as EXPECTED_BUILD
from help_patch import TARGETS,plan,normalize
from runtime import verify_runtime,runtime_manifest
from inventory import disassemble_entries
BASE_SHA='9592145c933f611888a00cb159340a86f99d427672483701212023078f823553'
EXPECTED='PASS help boundary; cases=62; legacy_browser_load_attempts=0; legacy_control_attempts=1; guard_control_rejections=3; forbidden_operations=0'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--development',action='store_true');a=p.parse_args()
    verify_python();compiler=verify_jdk(a.jdk)
    if a.output.exists():raise ValueError('Output exists')
    base=ROOT/'build/connection-publication-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(base)!=BASE_SHA:raise ValueError('Immutable qualified audit24 required')
    inputs=[Path(__file__).resolve(),ROOT/'tools/help_patch.py',ROOT/'tools/help_structure.py',ROOT/'tools/class_patch.py',ROOT/'tools/sync_ownership_patch.py',ROOT/'tools/baseline.py',ROOT/'tools/audit_support.py',ROOT/'tools/runtime.py',ROOT/'tools/inventory.py',ROOT/'tests/test_help_patch.py',ROOT/'patches/compat/HelpLauncher.java',ROOT/'tests/java/helpfixture/HelpObservation.java',ROOT/'tests/java/fixture/OfflineGuard.java',ROOT/'tests/java/fixture/FixtureIdentity.java',ROOT/'audit/jdk-lock.json',ROOT/'audit/python-lock.json',ROOT/'audit/runtime-lock.json',ROOT/'original/RAID_Admin_original.jar']
    inputs += [ROOT/'audit/help-patches.json',ROOT/'audit/expected-build.json',ROOT/'tools/verify_builds.py']
    sources={str(f.relative_to(ROOT)):sha(f) for f in inputs}
    state=lambda:(subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
    initial=state()
    if initial[1] and not a.development:raise ValueError('Clean source required')
    identity,product=check_artifact(a.build)
    if identity!=json.loads(EXPECTED_BUILD.read_text())['expected'] or (product['source_dirty'] and not a.development):raise ValueError('Integrated build differs')
    unit=subprocess.run([sys.executable,'-E','-s','-m','unittest','discover','-s','tests','-p','test_help_patch.py'],cwd=ROOT,env=isolated_env(),capture_output=True,timeout=60)
    if unit.returncode or unit.stdout or not re.search(rb'Ran 5 tests in [0-9.]+s\n\nOK\n$',unit.stderr):raise ValueError('Help unit gate failed; output withheld')

    a.output.mkdir(parents=True);helper=a.output/'helper';probes=a.output/'probes';helper.mkdir();probes.mkdir()
    run_jdk(a.jdk,'javac',['-source','8','-target','8','-d',str(helper),str(ROOT/'patches/compat/HelpLauncher.java')])
    with zipfile.ZipFile(base) as z:entries={n:z.read(n) for n in z.namelist()}
    before=dict(entries)
    browser_refs=[];reflection_strings=[];browser_classes=[];browser_descriptors=[]
    for name,data in before.items():
        if not name.endswith('.class'):continue
        c=ClassFile(data)
        for index,(tag,value) in c.pool.items():
            if tag==7 and c.pool[u2(value,0)][1]==b'edu/stanford/ejalbert/BrowserLauncher':browser_classes.append(name)
            if tag==1 and b'Ledu/stanford/ejalbert/BrowserLauncher;' in value:browser_descriptors.append(name)
            if tag in (9,10,11):
                _,owner=c.pool[u2(value,0)];_,text=c.pool[u2(owner,0)]
                if text==b'edu/stanford/ejalbert/BrowserLauncher' and name!='edu/stanford/ejalbert/BrowserLauncher.class':
                    browser_refs.append({'entry':name,'pool_index':index,'tag':tag})
            if tag==8 and c.pool[u2(value,0)][1] in (b'edu.stanford.ejalbert.BrowserLauncher',b'edu/stanford/ejalbert/BrowserLauncher'):
                reflection_strings.append(name)
    if {(r['entry'],r['pool_index'],r['tag']) for r in browser_refs}!={(name,spec[4],10) for name,spec in TARGETS.items()} or reflection_strings!=['edu/stanford/ejalbert/BrowserLauncher.class']:raise ValueError('Uncovered legacy browser reference')
    if set(browser_classes)!=set(TARGETS)|{'edu/stanford/ejalbert/BrowserLauncher.class'} or browser_descriptors:raise ValueError('Uncovered browser type/descriptor reference')
    hypertext=['com/apple/gui/HyperTextPane.class','com/apple/gui/HyperTextPane$Link.class','com/apple/gui/HyperTextPane$1.class']
    hypertext_file=a.output/'hypertext.javap';hypertext_file.write_text(disassemble_entries(a.jdk,base,hypertext,verbose=True))
    resources={n:hashlib.sha256(v).hexdigest() for n,v in before.items() if re.fullmatch(r'com/apple/xsr/resources/GlobalResources(?:_[a-z]{2}(?:_[A-Z]{2})?)?\.properties',n)}
    expected_locales={'','da','de','en','en_AU','en_GB','es','fi','fr','it','ja','ko','nl','no','pt','sv','zh','zh_TW'}
    actual_locales={n.rsplit('/',1)[1][len('GlobalResources'):-len('.properties')].lstrip('_') for n in resources}
    if actual_locales!=expected_locales:raise ValueError('Locale bundle inventory differs')
    for entry in TARGETS:
        entries[entry]=plan(entry,entries[entry])
        if normalize(entry,entries[entry])!=before[entry]:raise ValueError("Exact UI reversal differs")
    additions={str(f.relative_to(helper)):f.read_bytes() for f in helper.rglob('*.class')}
    if set(additions)!= {'compat/HelpLauncher.class','compat/HelpLauncher$Opener.class','compat/HelpLauncher$Reporter.class','compat/HelpLauncher$UnsupportedBrowse.class','compat/HelpLauncher$1.class','compat/HelpLauncher$2.class','compat/HelpLauncher$2$1.class'}:raise ValueError('Help class inventory differs')
    if any(ClassFile(b).data[6:8]!=b'\x00\x34' for b in additions.values()):raise ValueError('Helper class version differs')
    if set(entries)&set(additions):raise ValueError('Helper shadows baseline')
    entries.update(additions);jar=a.output/'help-candidate.jar';write_jar(jar,entries)
    with zipfile.ZipFile(jar) as z:
        if len(z.namelist())!=len(entries) or {n:z.read(n) for n in z.namelist()}!=entries:raise ValueError('Serialized overlay differs')
    if {n for n in entries if entries[n]!=before.get(n)}!=set(TARGETS)|set(additions):raise ValueError('Unexpected overlay change')
    actual=a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(actual)!=sha(jar):raise ValueError('Integrated candidate differs from exact qualified-core overlay')
    jar=actual.resolve()
    # Independent javap check: exactly one instruction operand changes in each existing action.
    disassemblies={}
    for entry,spec in TARGETS.items():
        old=disassemble_entries(a.jdk,base,[entry],verbose=True);new=disassemble_entries(a.jdk,jar,[entry],verbose=True)
        check_operand(entry,old,new)
        path=a.output/(entry.split('/')[-1]+'.javap');path.write_text(new);disassemblies[path.name]=sha(path)
    run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(jar),'-d',str(probes)]+[str(ROOT/n) for n in ['tests/java/helpfixture/HelpObservation.java','tests/java/fixture/OfflineGuard.java','tests/java/fixture/FixtureIdentity.java']])
    probehashes={str(f.relative_to(probes)):sha(f) for f in probes.rglob('*.class')}
    if set(probehashes)&set(entries):raise ValueError('Probe shadows candidate')
    classhashes={n:hashlib.sha256(b).hexdigest() for n,b in entries.items() if n.endswith('.class') and (n in TARGETS or n.startswith('compat/HelpLauncher') or n=='com/apple/xsr/Resources.class')}
    manifest=a.output/'identity.tsv';manifest.write_text('\n'.join(n[:-6].replace('/','.')+'\t'+str(loc.resolve())+'\t'+h for hashes,loc in [(probehashes,probes),(classhashes,jar)] for n,h in sorted(hashes.items()))+'\n')
    artifact_sha=sha(jar); manifest_sha=sha(manifest); rows=[];negative=[];lock=runtime_manifest()
    for folder,arch in [('arm64','aarch64'),('x64','x64')]:
        root=ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(root,lock['architectures'][arch])
        for mode in ['-Xint','-Xcomp']:
            flags=[mode,'-Xverify:all','-Djava.awt.headless=true','-Dfixture.identitymanifest='+str(manifest.resolve()),'-Dfixture.baseline='+str(base.resolve()),'-Dfixture.candidate='+str(jar.resolve()),'-cp',str(jar.resolve())+':'+str(probes.resolve()),'compat.HelpObservation']
            out=run_jdk(root/'Contents/Home','java',flags,timeout=60,require_empty_stderr=True)
            if out.splitlines()!=[EXPECTED]:raise ValueError('Unexpected Help result; output withheld')
            rows.append({'architecture':arch,'mode':mode,'result':EXPECTED,'flags':flags})
        for entry,spec in TARGETS.items():
            c=ClassFile(entries[entry]);b,e=method_code(c,spec[1],spec[2]);at=b+14+spec[3]
            mutant=dict(entries);mutant[entry]=compose(entries[entry],c,[(at,at+3,b'\x57\x00\x00')],c.pool_count)
            mutated=a.output/('missing-'+entry.split('/')[-1]+'.jar');write_jar(mutated,mutant)
            ids=a.output/('missing-'+entry.split('/')[-1]+'.tsv')
            hashes={n:hashlib.sha256(v).hexdigest() for n,v in mutant.items() if n in classhashes}
            ids.write_text('\n'.join(n[:-6].replace('/','.')+'\t'+str(loc.resolve())+'\t'+h for mapping,loc in [(probehashes,probes),(hashes,mutated)] for n,h in sorted(mapping.items()))+'\n')
            flags=['-Xint','-Xverify:all','-Djava.awt.headless=true','-Dfixture.identitymanifest='+str(ids.resolve()),'-Dfixture.baseline='+str(base.resolve()),'-Dfixture.candidate='+str(mutated.resolve()),'-cp',str(mutated.resolve())+':'+str(probes.resolve()),'compat.HelpObservation']
            r=subprocess.run([str(root/'Contents/Home/bin/java')]+JAVA_FLAGS+flags,env=isolated_env(),capture_output=True,timeout=60)
            frames=re.findall(rb'^\s+at (compat.HelpObservation.*?)$',r.stderr,re.M)
            if r.returncode==0 or r.stdout or not r.stderr.startswith(b'Exception in thread "main" java.lang.AssertionError: Help observation differs\n') or frames[:2]!=[b'compat.HelpObservation.check(HelpObservation.java:14)',b'compat.HelpObservation.observedStderr(HelpObservation.java:42)'] or b'VerifyError' in r.stderr:
                raise ValueError('Negative Help control failed outside intended assertion; raw withheld')
            negative.append({'architecture':arch,'mode':'-Xint','mutation':'missing-invocation','entry':entry,'candidate_sha256':sha(mutated),'identity_manifest_sha256':sha(ids),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'frames':[x.decode() for x in frames],'result':'expected fixture assertion'})
        verify_runtime(root,lock['architectures'][arch])
    verify_jdk(a.jdk)
    if sha(jar)!=artifact_sha or sha(manifest)!=manifest_sha or probehashes!={str(f.relative_to(probes)):sha(f) for f in probes.rglob('*.class')}:raise ValueError('Fixture/artifact changed')
    if initial!=state():raise ValueError('Source state changed')
    if sources!={str(f.relative_to(ROOT)):sha(f) for f in inputs} or sha(base)!=BASE_SHA:raise ValueError('Inputs changed')
    record={'unit_stderr_sha256':hashlib.sha256(unit.stderr).hexdigest(),'qualification':not a.development,'source_commit':initial[0],'source_dirty':initial[1],'candidate_source_commit':product['source_commit'],'candidate_source_dirty':product['source_dirty'],'scope':'Integrated Help actions and helper; exact unchanged qualified audit24 core bytes; not controller or release acceptance','candidate_sha256':sha(jar),'qualified_baseline_sha256':BASE_SHA,'sources':sources,'compiled_helper_hashes':{n:hashlib.sha256(b).hexdigest() for n,b in additions.items()},'compiled_probe_hashes':probehashes,'browser_class_reference_entries':browser_classes,'browser_descriptor_reference_entries':browser_descriptors,'browser_constant_pool_references':browser_refs,'browser_reflection_string_entries':reflection_strings,'hypertext_disassembly_sha256':sha(hypertext_file),'resource_bundle_sha256':resources,'class_identity_manifest_sha256':sha(manifest),'disassemblies':disassemblies,'observations':rows,'negative_controls':negative,'limits':['x64 executed under Rosetta, not physical Intel','No Desktop.browse invocation or browser launch','No complete application startup or production profile access','UnsupportedOperationDialog constructor bypassed using Unsafe; only hyperlink method exercised','Old BrowserLauncher references retained in unused constant pool; loading denied in child action loader','Xcomp requested, no full-VM compilation claim','Remote content availability unverified'],'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for arch in ('aarch64','x64')},'compiler_tree_sha256':compiler['tree_sha256']}
    (a.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS integrated Help boundary; four runtime/mode variants; no browser/controller')
if __name__=='__main__':main()
