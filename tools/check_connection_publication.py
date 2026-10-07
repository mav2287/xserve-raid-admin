#!/usr/bin/env python3
"""Memory-only actual Acpx publication regression and verifier-valid negative controls."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
from audit_support import ROOT,JAVA_FLAGS,sha,verify_python,verify_jdk,run_jdk,isolated_env
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact,entries
from baseline import write_jar,verify_original
from inventory import disassemble_entries
from class_patch import ClassFile,word
from sync_ownership_patch import compose,method_code,code_attribute
from connection_publication_patch import ENTRY,CODE,normalize
from connection_publication_structure import check_publication
REFERENCE='2fccbee50eb868a04b415085511e0b52e6a13682543858d6f653b7f1f5fcadad'
JAVA=('tests/java/connectionfixture/ConnectionPublicationObservation.java','tests/java/connectionfixture/CachedConfigurationObservation.java','tests/java/fixture/OfflineGuard.java','tests/java/fixture/FixtureIdentity.java')
SOURCES=JAVA+('tools/check_connection_publication.py','tools/connection_publication_patch.py','tools/help_patch.py','tools/model_diagnostic_patch.py','audit/model-diagnostic-patches.json','audit/help-patches.json','tools/connection_publication_structure.py','tools/audit_support.py','tools/runtime.py','tools/baseline.py','tools/inventory.py','tools/verify_builds.py','tools/class_patch.py','tools/sync_ownership_patch.py','tools/worker_exit_patch.py','tools/stop_admission_patch.py','tools/socket_configuration_patch.py','audit/expected-build.json','audit/jdk-lock.json','audit/runtime-lock.json','audit/python-lock.json','audit/security-patches.json','tests/test_connection_publication.py','tests/fixtures/connection-publication-candidate-acpx.javap')
FRAMES={'early-publication': ['ConnectionPublicationObservation.check(ConnectionPublicationObservation.java:32)', 'ConnectionPublicationObservation.unpublished(ConnectionPublicationObservation.java:34)', 'ConnectionPublicationObservation$MemoryImpl.connect(ConnectionPublicationObservation.java:47)'], 'missing-publication': ['ConnectionPublicationObservation.check(ConnectionPublicationObservation.java:32)', 'ConnectionPublicationObservation.main(ConnectionPublicationObservation.java:151)'], 'missing-open': ['ConnectionPublicationObservation.check(ConnectionPublicationObservation.java:32)', 'ConnectionPublicationObservation.main(ConnectionPublicationObservation.java:151)'], 'missing-persistent': ['ConnectionPublicationObservation.check(ConnectionPublicationObservation.java:32)', 'ConnectionPublicationObservation.lambda$request$0(ConnectionPublicationObservation.java:101)', 'ConnectionPublicationObservation.main(ConnectionPublicationObservation.java:163)']}

def state():
    return (subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jdk',required=True,type=Path);p.add_argument('--runtime',required=True,action='append',type=Path)
    p.add_argument('--candidate',required=True,type=Path);p.add_argument('--candidate-sha256',required=True)
    p.add_argument('--reference',required=True,type=Path);p.add_argument('--development',action='store_true');a=p.parse_args()
    verify_python();compiler=verify_jdk(a.jdk);initial=state()
    if initial[1] and not a.development:raise ValueError('Clean gate source required')
    candidate=a.candidate.resolve();reference=a.reference.resolve()
    if a.candidate.is_symlink() or a.reference.is_symlink() or sha(candidate)!=a.candidate_sha256 or sha(reference)!=REFERENCE:raise ValueError('Pinned artifact identity differs')
    identity,manifest=check_artifact(candidate.parents[3])
    if identity!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected'] or (manifest['source_dirty'] and not a.development):raise ValueError('Product source or expected identity differs')
    original=ROOT/'original/RAID_Admin_original.jar';verify_original(original)
    before,after=entries(reference),entries(candidate)
    from help_patch import strip_entries
    core=strip_entries(after)
    if before.keys()!=core.keys() or {n for n in before if before[n]!=core[n]}!={ENTRY} or normalize(after[ENTRY])!=before[ENTRY]:raise ValueError('Private method-only predecessor reversal differs')
    check_publication(disassemble_entries(a.jdk,candidate,[ENTRY],verbose=True))
    hashes={n:sha(ROOT/n) for n in SOURCES};artifacts={str(j):sha(j) for j in (candidate,reference,original)}
    lock=runtime_manifest();runtimes={};rows=[];negative=[]
    for root in a.runtime:
        matching=[]
        for arch in ('aarch64','x64'):
            try:verify_runtime(root,lock['architectures'][arch])
            except ValueError:continue
            matching.append(arch)
        if len(matching)!=1 or matching[0] in runtimes:raise ValueError('Distinct locked runtimes required')
        runtimes[matching[0]]=root.resolve()
    if set(runtimes)!={'aarch64','x64'}:raise ValueError('Both architectures required')
    with tempfile.TemporaryDirectory(prefix='raid-connection-publication-') as t:
        tmp=Path(t);classes=tmp/'classes';classes.mkdir()
        run_jdk(a.jdk,'javac',['-source','8','-target','8','-d',str(classes),'-cp',str(candidate)]+[str(ROOT/n) for n in JAVA])
        probes={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}
        if probes.keys()&after.keys():raise ValueError('Probe shadows product')
        def flags(jar,kind,folder,mode):
            product={n:hashlib.sha256(v).hexdigest() for n,v in entries(jar).items() if n.endswith('.class') and (n.startswith('compat/') or n in (ENTRY,'com/apple/xsr/net/HttpConnection.class'))}
            idfile=folder/'identity.tsv';ids=[n[:-6].replace('/','.')+'\t'+str(location)+'\t'+h for mapping,location in ((probes,classes),(product,jar)) for n,h in sorted(mapping.items())]
            idfile.write_text('\n'.join(ids)+'\n')
            return [mode,'-Xverify:all','-Djava.awt.headless=true','-Duser.home='+str(folder),'-Dfixture.identitymanifest='+str(idfile),'-cp',str(jar)+':'+str(classes),kind],sha(idfile)
        for arch,root in runtimes.items():
            for mode in ('-Xint','-Xcomp'):
                for kind,jar,expected in [('ConnectionPublicationObservation',candidate,'PASS connection publication; cases=26; explicit_failure_attempts=34; native_socket_creation_forbidden=true; native_output_attempts=0'),('CachedConfigurationObservation',reference,'PASS cached connection gap characterized; calls=3; native_sockets=0; output_acquisitions=0; custom_timeout_null_socket=true')]:
                    folder=tmp/(arch+mode+kind);folder.mkdir();execution,idsha=flags(jar,kind,folder,mode)
                    out=run_jdk(root/'Contents/Home','java',execution,timeout=90,require_empty_stderr=True)
                    if out.splitlines()!=[expected]:raise ValueError('Observation differs; raw withheld')
                    rows.append({'architecture':arch,'execution_mode':mode,'jar_sha256':sha(jar),'fixture':kind,'result':expected,'execution_flags':execution,'identity_manifest_sha256':idsha})
        c=ClassFile(after[ENTRY]);b,e=method_code(c,'createConnection','()V');mutants={'early-publication':before[ENTRY]}
        for name,start,end in [('missing-publication',31,36),('missing-open',27,31),('missing-persistent',19,27)]:
            code=CODE[:start]+b'\x00'*(end-start)+CODE[end:]
            mutants[name]=compose(after[ENTRY],c,[(b,e,code_attribute(after[ENTRY][b:e],word(3)+word(2),code,word(0)+word(0)))],c.pool_count)
        for name,data in mutants.items():
            folder=tmp/name;folder.mkdir();jar=folder/'mutant.jar';contents=dict(after);contents[ENTRY]=data;write_jar(jar,contents)
            execution,idsha=flags(jar,'ConnectionPublicationObservation',folder,'-Xint')
            for arch,root in runtimes.items():
                r=subprocess.run([str(root/'Contents/Home/bin/java')]+JAVA_FLAGS+execution,env=isolated_env(),capture_output=True,timeout=30)
                first=re.search(rb'^Exception in thread "main" java.lang.AssertionError: (.*)$',r.stderr,re.M)
                frames=[s.decode() for s in re.findall(rb'^\s+at (ConnectionPublicationObservation.*?)$',r.stderr,re.M)][:len(FRAMES[name])]
                if r.returncode==0 or r.stdout or first is None or first[1]!=b'Publication assertion' or frames!=FRAMES[name] or b'VerifyError' in r.stderr:raise ValueError('Negative control failed outside exact intended assertion; raw withheld')
                negative.append({'mutation':name,'architecture':arch,'execution_mode':'-Xint','jar_sha256':sha(jar),'identity_manifest_sha256':idsha,'assertion':'Publication assertion','expected_fixture_frames':FRAMES[name],'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'verifier_or_timeout_failure':False})
    for arch,root in runtimes.items():verify_runtime(root,lock['architectures'][arch])
    verify_jdk(a.jdk);verify_original(original)
    if initial!=state() or hashes!={n:sha(ROOT/n) for n in SOURCES} or artifacts!={str(j):sha(j) for j in (candidate,reference,original)}:raise ValueError('Inputs/source state changed during gate')
    print(json.dumps({'qualification':not a.development,'candidate_acpx_sha256':hashlib.sha256(after[ENTRY]).hexdigest(),'reference_acpx_sha256':hashlib.sha256(before[ENTRY]).hexdigest(),'runtime_trees':{arch:lock['architectures'][arch]['tree_sha256'] for arch in runtimes},'source_commit':initial[0],'source_dirty':initial[1],'candidate_source_commit':manifest['source_commit'],'candidate_source_dirty':manifest['source_dirty'],'candidate_sha256':sha(candidate),'reference_sha256':REFERENCE,'compiler_tree_sha256':compiler['tree_sha256'],'sources':hashes,'probe_hashes':probes,'observations':rows,'negative_controls':negative,'limits':'Trusted memory SocketImpl fixtures; no native sockets/output, profiles, credentials, app Main, commands transmitted or controller. x64 is Rosetta; Xcomp is requested, not a whole-VM compilation claim. Write marker tests preserve original outstanding-request bookkeeping, not successful response recovery. Local publication fix is not concurrency cancellation or controller acceptance.'},indent=2))
if __name__=='__main__':main()
