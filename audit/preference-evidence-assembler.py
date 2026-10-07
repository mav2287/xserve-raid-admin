"""Bind completed local audit27 results to immutable artifacts and actual Git inputs."""
import argparse,hashlib,json,re,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import sha,isolated_env,verify_python
from verify_builds import entries
from preference_io_patch import strip_entries,ENTRY,ORIGINAL_SHA,PATCHED_SHA
from model_diagnostic_patch import ORIGINAL_SHA as MODEL_ORIGINAL, PATCHED_SHA as MODEL_PATCHED
verify_python()
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--product-commit',required=True);a=p.parse_args()
CORE='4735f4165340cbca6dc30a83f200f4a31ac6dc15'
PIN='e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62'
REFERENCE='7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158'
def require(value):
    if not value:raise ValueError('Audit27 evidence binding failed; details withheld')
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
require(a.product_commit==CORE)
require(git('rev-parse','HEAD').decode().strip()==a.commit and not git('status','--porcelain'))
require(subprocess.run(['/usr/bin/git','merge-base','--is-ancestor',CORE,a.commit],cwd=ROOT,env=isolated_env(),capture_output=True).returncode==0)
changes=git('diff','--name-only',CORE,a.commit).decode().splitlines()
require(all(n=='audit/preference-evidence-assembler.py' or n.endswith(('.md','.txt')) for n in changes))
runner=ROOT/'audit/preference-gate-runner.py';assembler=Path(__file__).resolve()
require(hashlib.sha256(git('show',a.commit+':'+str(assembler.relative_to(ROOT)))).hexdigest()==sha(assembler))
jar=ROOT/'build/preference-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
reference=ROOT/'build/model-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
require(sha(jar)==PIN and sha(reference)==REFERENCE and strip_entries(entries(jar))==entries(reference))
actual,prior=entries(jar),entries(reference)
preference_lock=json.loads((ROOT/'audit/preference-io-patches.json').read_text())
helper_lock=preference_lock['helpers']
require(helper_lock=={'compat/PreferenceIO.class':'51d208b2a0aa3a1607b53fce1050bbbfe5687ec3c7df983d975b921718eb90a3'})
require(ENTRY=='com/apple/util/prefs/FileBasedPreferences.class' and preference_lock['entry']==ENTRY and preference_lock['original_sha256']==ORIGINAL_SHA and preference_lock['patched_sha256']==PATCHED_SHA)
require(set(actual)==set(prior)|set(helper_lock) and {n for n in actual if actual[n]!=prior.get(n)}=={ENTRY}|set(helper_lock))
require({n:hashlib.sha256(actual[n]).hexdigest() for n in helper_lock}==helper_lock)
require(hashlib.sha256(actual[ENTRY]).hexdigest()==PATCHED_SHA and hashlib.sha256(prior[ENTRY]).hexdigest()==ORIGINAL_SHA)
reference_artifacts={
 'original/RAID_Admin_original.jar':'5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449',
 'build/help-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar':'59087dceed5865b08cef4db0b554a0822837618a07e59b6fd92a2b25880e6393',
 'build/connection-publication-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar':'9592145c933f611888a00cb159340a86f99d427672483701212023078f823553',
 'build/socket-configuration-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar':'2fccbee50eb868a04b415085511e0b52e6a13682543858d6f653b7f1f5fcadad',
 'build/stop-admission-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar':'202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd',
 'build/worker-exit-clean-3/RAID Admin.app/Contents/Resources/RAID_Admin.jar':'9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562',
 'build/stopped-post-clean-3/RAID Admin.app/Contents/Resources/RAID_Admin.jar':'f6e545bbd90e7f9616df448f09cc4a889b909fa8e79a8183af8fa96a71d9f859',
 'build/model-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar':REFERENCE,
}
for name,pin in reference_artifacts.items():require(sha(ROOT/name)==pin)
from runtime import runtime_manifest,verify_runtime
runtime_lock=runtime_manifest()
for folder,arch in [('arm64','aarch64'),('x64','x64')]:
    verify_runtime(ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk'),runtime_lock['architectures'][arch])

summary=json.loads((ROOT/'build/preference-gate-run-summary.json').read_text())
names={'security','transport','resources','shared','posting','runtime','factory','connect','lock','admission','worker','stop','socket','publication','help','model','preference'}
require(summary['execution_commit']==CORE and summary['execution_dirty'] is False and len(summary['rows'])==17 and {r['gate'] for r in summary['rows']}==names)
require(set(summary['sources'])=={'audit/preference-gate-runner.py','audit/preference-gate-commands.json','tools/audit_support.py','audit/python-lock.json'} and summary['sources']['audit/preference-gate-runner.py']==sha(runner))
commands=json.loads((ROOT/'audit/preference-gate-commands.json').read_text())
files=['build/preference-gate-run-summary.json','build/preference-clean-unit.json','build/preference-clean-unit.stdout','build/preference-clean-unit.stderr']
for row in summary['rows']:
    require(row['accepted'] is True and row['returncode']==0 and row['stderr_bytes']==0 and row['stderr_sha256']==hashlib.sha256(b'').hexdigest())
    require(row['argv']==shlex.split(commands[row['gate']]))
    path='build/preference-clean-'+row['gate']+('-boundary/observations.json' if row['gate'] in ('help','model','preference') else '.json')
    require(row['record']==path and sha(ROOT/path)==row['record_sha256'])
    if row['gate'] not in ('help','model','preference'):require(row['stdout_sha256']==row['record_sha256'])
    else:
        line={'preference':'PASS preference IO gate; runs=8; cases=18; original_controls=8; negative_controls=16; units=5','help':'PASS integrated Help boundary; four runtime/mode variants; no browser/controller','model':'PASS model diagnostic gate; four runtime/mode variants; sixteen behavioral negative controls; no controller/profile'}[row['gate']]
        require(row['stdout_sha256']==hashlib.sha256((line+'\n').encode()).hexdigest())
    files.append(path)
files+=['build/preference-clean-'+str(i)+'/provenance.json' for i in (1,2)]
for arch in ('aarch64','x64'):
    files+=['build/preference-bundled-'+arch+'-'+str(i)+'/provenance.json' for i in (1,2)]
    files+=['build/releases/audit27/RAID-Admin-'+arch+suffix for suffix in ('.zip','.archive.json','-repeat.zip','-repeat.archive.json','.spdx.json','-repeat.spdx.json')]
    require(sha(ROOT/('build/releases/audit27/RAID-Admin-'+arch+'.zip'))==sha(ROOT/('build/releases/audit27/RAID-Admin-'+arch+'-repeat.zip')))
    require(sha(ROOT/('build/releases/audit27/RAID-Admin-'+arch+'.spdx.json'))==sha(ROOT/('build/releases/audit27/RAID-Admin-'+arch+'-repeat.spdx.json')))
    for number,suffix in ((1,''),(2,'-repeat')):
        base='build/releases/audit27/RAID-Admin-'+arch+suffix
        bundle=ROOT/('build/preference-bundled-'+arch+'-'+str(number)+'/provenance.json')
        archive=json.loads((ROOT/(base+'.archive.json')).read_text());metadata=json.loads(bundle.read_text())
        spdx=json.loads((ROOT/(base+'.spdx.json')).read_text());provenance=json.loads(spdx['creationInfo']['comment'])
        require(archive['architecture']==metadata['bundled_runtime']['architecture']==arch)
        require(metadata['source_commit']==metadata['packager_commit']==provenance['source_commit']==provenance['packager_commit']==CORE)
        require(archive['archive_sha256']==sha(ROOT/(base+'.zip')) and archive['bundle_provenance_sha256']==sha(bundle))
        require(archive['bundle_tree_sha256']==metadata['bundle_tree_sha256']==provenance['bundle_tree_sha256'])
        require(archive['source_provenance_sha256']==sha(ROOT/('build/preference-clean-'+str(number)+'/provenance.json')))
        require(metadata['source_provenance_sha256']==archive['source_provenance_sha256'])
        require(metadata['files']['Contents/Resources/RAID_Admin.jar']==PIN)
        packages=[p for p in spdx['packages'] if p['SPDXID']=='SPDXRef-jar'];require(len(packages)==1)
        require([c['checksumValue'] for c in packages[0]['checksums'] if c['algorithm']=='SHA256']==[PIN])
        require(provenance['negative_controls']==12)
records={};proofs=[]
def walk(value,record,commit):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('sources','source_hashes','input_hashes','verifier_sources','fixture_sources','harness_sources') and isinstance(item,dict):
                for name,h in item.items():
                    require(isinstance(name,str) and not Path(name).is_absolute() and '..' not in Path(name).parts and isinstance(h,str) and len(h)==64)
                    path=ROOT/name;require(path.is_file() and not path.is_symlink())
                    require(sha(path)==h and hashlib.sha256(git('show',commit+':'+name)).hexdigest()==h)
                    proofs.append({'record':record,'source':name,'sha256':h,'verified_commit':commit})
            if key in ('source_dirty','fixture_dirty','candidate_source_dirty','execution_dirty','packager_dirty','dirty'):require(item is False)
            walk(item,record,commit)
    elif isinstance(value,list):
        for item in value:walk(item,record,commit)
for name in files:
    path=ROOT/name;require(path.is_file() and not path.is_symlink());records[name]=sha(path)
    if not name.endswith('.json'):continue
    data=json.loads(path.read_text())
    commit=data.get('fixture_commit',data.get('execution_commit',data.get('packager_commit',data.get('source_commit'))))
    if 'execution_state' in data:commit=data['execution_state']['commit']
    if 'creationInfo' in data:commit=json.loads(data['creationInfo']['comment'])['execution_state']['commit']
    require(commit==CORE)
    prior=len(proofs);walk(data,name,commit)
    if 'creationInfo' in data:walk(json.loads(data['creationInfo']['comment']),name,commit)
    require(len(proofs)>prior)
    if name.startswith('build/preference-clean-') and name.endswith('.json'):
        require(len(proofs)>prior)
        for key in ('candidate_sha256','jar_sha256','candidate_jar_sha256'):
            if key in data:require(data[key]==PIN)
        for key in ('source_commit','fixture_commit','execution_commit','candidate_source_commit','application_source_commit'):
            if key in data:require(data[key]==CORE)
        if 'qualification' in data:require(data['qualification'] is True)
        if 'observations' in data:require(bool(data['observations']))
        if name in ('build/preference-clean-factory.json','build/preference-clean-shared.json','build/preference-clean-transport.json'):require(any(row.get('jar_sha256')==PIN for row in data['observations']))
        elif name in [r['record'] for r in summary['rows']]:require(any(data.get(k)==PIN for k in ('candidate_sha256','jar_sha256','candidate_jar_sha256')))
        if name in ('build/preference-clean-1/provenance.json','build/preference-clean-2/provenance.json'):require(data['files']['Contents/Resources/RAID_Admin.jar']==PIN)
unit=json.loads((ROOT/'build/preference-clean-unit.json').read_text());require(unit['tests_passed']==175 and unit['stdout_sha256']==records['build/preference-clean-unit.stdout'] and unit['stderr_sha256']==records['build/preference-clean-unit.stderr'])
require(unit['command']==[sys.executable,'-E','-s','-m','unittest','discover','-s','tests'])
require(unit['runner_sha256']==sha(ROOT/'audit/preference-unit-runner.py')==hashlib.sha256(git('show',CORE+':audit/preference-unit-runner.py')).hexdigest())
require(re.fullmatch(rb'\.{175}\n-+\nRan 175 tests in [0-9.]+s\n\nOK\n',(ROOT/'build/preference-clean-unit.stderr').read_bytes()) is not None)
model=json.loads((ROOT/'build/preference-clean-model-boundary/observations.json').read_text());require(len(model['observations'])==4 and len(model['negative_controls'])==16 and model['unit_tests']==5)
require({(r['architecture'],r['mode']) for r in model['observations']}=={(arch,mode) for arch in ('aarch64','x64') for mode in ('-Xint','-Xcomp')})
require(all(r['result']=='PASS model diagnostic redaction; cases=40; original_differential=true; product_loader=true; getters_flags_observers_preserved=true; forbidden_operations=0' for r in model['observations']))
require(all(r['result']=='expected model differential assertion' for r in model['negative_controls']))
require(model['candidate_sha256']==PIN)
require(model['qualified_baseline_sha256']=='59087dceed5865b08cef4db0b554a0822837618a07e59b6fd92a2b25880e6393' and model['original_model_sha256']==MODEL_ORIGINAL and model['patched_model_sha256']==MODEL_PATCHED)
require({(r['architecture'],r['phase'],r['mutation']) for r in model['negative_controls']}=={(arch,phase,mutation) for arch in ('aarch64','x64') for phase in ('both','product') for mutation in ('original','monitor-read-retained','management-read-retained','wrong-token')})
preference=json.loads((ROOT/'build/preference-clean-preference-boundary/observations.json').read_text())
require(len(preference['observations'])==16 and len(preference['negative_controls'])==16 and preference['unit_tests']==5)
require(preference['reference_sha256']==REFERENCE and preference['original_class_sha256']==ORIGINAL_SHA and preference['patched_class_sha256']==PATCHED_SHA and preference['helper_hashes']==helper_lock)
for row in preference['observations']:
    require(row['candidate_sha256']==(PIN if row['phase']=='candidate' else REFERENCE))
    expected='PASS preference write; cases=18; success_exception_error_fd_delta=0; interrupts_preserved=true; synthetic_files_only=true' if row['phase']=='candidate' else 'OBSERVE original preference IO; store_fd_delta=32; load_fd_delta=0; new_file_mode='+format(0o666&~row['umask'],'o')+'; gc_during_measurement=0; real_profile_access=none'
    require(row['result']==expected)
expected_codes={'wrong-charset':'bytes-kind-1','close-writer-on-error':'bytes-kind-5','append-instead-of-truncate':'existing-truncation','no-close':'success-fd','no-close-on-failure':'exception-fd','interruptible-stream':'interrupt-bytes-true','clear-interrupt':'interrupt-candidate-true','error-only-leak':'error-fd'}
for row in preference['negative_controls']:
    require(row['mode']=='-Xint' and row['candidate_sha256'] not in (PIN,REFERENCE))
    require(row['result']=='expected preference differential assertion' and row['assertion_code']==expected_codes[row['mutation']])
for mutation in expected_codes:require(len({r['candidate_sha256'] for r in preference['negative_controls'] if r['mutation']==mutation})==1)
require(preference['runtime_trees']==model['runtime_trees']=={arch:runtime_lock['architectures'][arch]['tree_sha256'] for arch in ('aarch64','x64')})
for row in model['negative_controls']:
    require(row['mode']=='-Xint')
    require(row['model_sha256']==MODEL_ORIGINAL if row['mutation']=='original' else row['model_sha256'] not in (MODEL_ORIGINAL,MODEL_PATCHED))
require(preference['class_major_version']==47 and preference['helper_major_version']==52 and preference['mutation_pipeline_identity_hashes']==helper_lock)
require({(r['architecture'],r['mode'],r['umask'],r['phase']) for r in preference['observations']}=={(arch,mode,mask,phase) for arch in ('aarch64','x64') for mode in ('-Xint','-Xcomp') for mask in (18,63) for phase in ('candidate','reference')})
require({(r['architecture'],r['mutation']) for r in preference['negative_controls']}=={(arch,mutation) for arch in ('aarch64','x64') for mutation in ('wrong-charset','close-writer-on-error','append-instead-of-truncate','no-close','no-close-on-failure','interruptible-stream','clear-interrupt','error-only-leak')})
require(not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==a.commit)
record={'schema':1,'scope':'Audit27 local software qualification and unsigned archives/SBOMs; hardware/native full GUI/physical Intel/signing acceptance deferred or unverified','execution_commit':a.commit,'execution_dirty':False,'candidate_gate_execution_commits':[CORE],'product_build_package_release_commit':CORE,'candidate_regression_gates':17,'unit_tests':175,'jar_sha256':PIN,'preserved_audit26_jar_sha256':REFERENCE,'model_qualified_baseline_audit25_sha256':'59087dceed5865b08cef4db0b554a0822837618a07e59b6fd92a2b25880e6393','records':records,'reference_artifacts':reference_artifacts,'fixture_runtime_trees':{arch:runtime_lock['architectures'][arch]['tree_sha256'] for arch in ('aarch64','x64')},'source_proofs':proofs,'assembler_sha256':sha(assembler),'assembler_dependency_sha256':{'tools/runtime.py':sha(ROOT/'tools/runtime.py'),'audit/runtime-lock.json':sha(ROOT/'audit/runtime-lock.json')},'gate_runner_sha256':sha(runner),'gate_summary_sha256':sha(ROOT/'build/preference-gate-run-summary.json'),'limits':['No controller contact or production/mounted-volume tests','No firmware or destructive/controller-setting operation','No installed application modification','No actual browser invocation or complete Main/native GUI acceptance','x64 is Rosetta, not physical Intel','Unsigned/unnotarized; redistribution rights unresolved','Password memory/getters/persistence and other documented gaps remain','HTTP remains plaintext','Synthetic preference fixtures only; no real preferences; load bytecode unchanged; existing modes/ACL/link and at-rest gaps retained','Raw close can newly throw; allocation-order/OOM and close-failure injection remain documented limits','No atomic replacement/fsync/encryption; original truncation on serialization failure remains; concurrent filesystem attackers and JVM exhaustion not qualified; Xcomp requested only']}
with (ROOT/'build/preference-final-integrity.json').open('x') as out:out.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print('PASS audit27 evidence binding; seventeen candidate gates, 175 units, paired packages/archives/SBOMs')
