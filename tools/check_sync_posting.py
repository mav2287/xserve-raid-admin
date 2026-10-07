#!/usr/bin/env python3
"""Bounded memory-only synchronous posting differential; never starts the app."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from audit_support import ROOT, sha, verify_jdk, verify_python, run_jdk, isolated_env
from baseline import verify_original, write_jar
from class_patch import assert_preserved, assert_sync_preenqueue, normalize_current_extensions
from runtime import runtime_manifest, verify_runtime
from verify_builds import check_artifact

ENTRY='com/apple/xsr/net/CommunicationsManager$SyncSender.class'
TAIL=[
    'sync normal clones=2 attempts=1 waited=true response_identity=true',
    'sync immediate-before-wait response_identity=true',
    'sync stopped before_clone=true queue=0',
    'sync interrupted residual_queue=1 stopped=false cancellation=unfixed',
    'PASS sync preenqueue observations; guarded_operations=0',
]
def expected(fixed):
    return ['sync callback fixed_exception=true second_clone='+('false' if fixed else 'true')+
            ' queued='+('0' if fixed else '1')+' request_attempts=2 forbidden_restart='+('blocked' if fixed else 'sent')]+TAIL

def check_lines(lines,fixed):
    if lines!=expected(fixed):raise ValueError('Sync posting vector differs; raw output withheld')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jdk',required=True,type=Path)
    p.add_argument('--runtime',required=True,action='append',type=Path)
    p.add_argument('--candidate-sha256',required=True)
    p.add_argument('--development',action='store_true')
    p.add_argument('candidate',type=Path)
    a=p.parse_args();verify_python();lock=verify_jdk(a.jdk)
    commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    if dirty and not a.development:raise ValueError('Clean fixture commit required')
    original=ROOT/'original/RAID_Admin_original.jar';verify_original(original)
    if a.candidate.is_symlink() or not a.candidate.is_file() or a.candidate.resolve()==original.resolve() or sha(a.candidate)!=a.candidate_sha256:raise ValueError('Candidate identity differs')
    identity,manifest=check_artifact(a.candidate.resolve().parents[3])
    if identity!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected'] or a.candidate_sha256!=json.loads((ROOT/'audit/stopped-post-recovery-expected.json').read_text())['candidate_jar_sha256']:raise ValueError('Candidate differs from reviewed complete artifact')
    if not a.development and manifest['source_dirty']:raise ValueError('Clean application source required')
    with zipfile.ZipFile(original) as z:before=z.read(ENTRY)
    with zipfile.ZipFile(a.candidate) as z:entries={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    assert_preserved(before,entries[ENTRY],'<init>','(Lcom/apple/xsr/net/CommunicationsManager;Lcom/apple/xsr/net/RequestMessage;)V')
    assert_sync_preenqueue(before,entries[ENTRY])
    sources=[ROOT/name for name in ('tests/java/fixture/OfflineGuard.java','tests/java/com/apple/xsr/net/TransportObservation.java','tests/java/com/apple/xsr/net/HeaderObservation.java','patches/sun/io/MalformedInputException.java','tools/check_sync_posting.py','tools/class_patch.py','tools/socket_configuration_patch.py','tools/connection_publication_patch.py','tools/sync_ownership_patch.py','tools/worker_exit_patch.py','tools/stop_admission_patch.py','tools/stop_admission_structure.py','tools/baseline.py','tools/audit_support.py','tools/runtime.py','tools/verify_builds.py','audit/expected-build.json','audit/stopped-post-recovery-expected.json','audit/runtime-lock.json')]
    hashes={str(x.relative_to(ROOT)):sha(x) for x in sources}
    runtimes=[];seen=set();runtime_lock=runtime_manifest()
    for root in a.runtime:
        arch=None
        for key in ('aarch64','x64'):
            try:verify_runtime(root,runtime_lock['architectures'][key])
            except ValueError:continue
            arch=key;break
        if arch is None or arch in seen:raise ValueError('Distinct pinned runtime required')
        seen.add(arch);runtimes.append((root,arch))
    if seen!={'aarch64','x64'}:raise ValueError('Both pinned architectures required')
    observations=[]
    with tempfile.TemporaryDirectory(prefix='raid-sync-posting-') as tmp:
        run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(a.candidate.resolve()),'-d',tmp]+[str(x) for x in sources if x.suffix=='.java'])
        mutant=Path(tmp)/'restored-constructor.jar';entries['com/apple/xsr/net/CommunicationsManager.class']=normalize_current_extensions(entries['com/apple/xsr/net/CommunicationsManager.class']);entries[ENTRY]=before;write_jar(mutant,entries)
        for root,arch in runtimes:
            for execution in ('-Xint','-Xcomp'):
                for fixed,jar in ((False,original),(True,a.candidate)):
                    output=run_jdk(root/'Contents/Home','java',['-Xverify:all',execution,'-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',tmp+':'+str(jar.resolve()),'com.apple.xsr.net.TransportObservation','sync-preenqueue-'+('candidate' if fixed else 'original')],timeout=20)
                    check_lines(output.splitlines(),fixed)
                    observations.append({'architecture':arch,'execution':execution,'candidate':fixed,'jar_sha256':sha(jar),'lines':output.splitlines()})
            output=run_jdk(root/'Contents/Home','java',['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-cp',tmp+':'+str(mutant),'com.apple.xsr.net.TransportObservation','verify-sync-preenqueue'],timeout=20)
            if output.splitlines()!=['PASS verified preenqueue bypass fails queue fixture; guarded_operations=0']:raise ValueError('Sync negative control differs')
            observations.append({'architecture':arch,'restored_constructor_mutant_sha256':sha(mutant),'semantic_negative_control':True})
            verify_runtime(root,runtime_lock['architectures'][arch])
    if any(sha(ROOT/name)!=value for name,value in hashes.items()):raise ValueError('Fixture input changed')
    final_dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    if not a.development and final_dirty:raise ValueError('Clean fixture changed')
    print(json.dumps({'source_commit':manifest['source_commit'],'source_dirty':manifest['source_dirty'],'fixture_commit':commit,'fixture_dirty':dirty,'qualification':not a.development,'candidate_sha256':sha(a.candidate),'original_sha256':sha(original),'compiler_tree_sha256':lock['tree_sha256'],'source_hashes':hashes,'runtime_trees':{arch:runtime_lock['architectures'][arch]['tree_sha256'] for _,arch in runtimes},'observations':observations,'limits':'Defense in depth: live worker callback deliberately catches IllegalStateException. Stop on second scripted response bounds original continuation; exact second body compared internally. ImmediateManager is a synchronous callback seam, not a production subclass. This gate checks preenqueue behavior; ownership cancellation and terminal worker completion are in check_guarded_worker. Its restored-constructor control also restores the reviewed audit.20 Manager because new Manager code requires the claim method. GUI reachability and controllers remain unqualified. No sockets, profiles, app launch or production volumes.'},indent=2))

if __name__=='__main__':main()
