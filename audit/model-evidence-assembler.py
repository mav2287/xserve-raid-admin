"""Bind completed local audit26 results to immutable artifacts and actual Git inputs."""
import argparse,hashlib,json,re,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import sha,isolated_env,verify_python
from verify_builds import entries
from model_diagnostic_patch import strip_entries,ENTRY,ORIGINAL_SHA,PATCHED_SHA
verify_python()
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);a=p.parse_args()
CORE='46dec9e8cfba5b9de9ce49a59b05fd5f61b4b0a6'
PIN='7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158'
REFERENCE='59087dceed5865b08cef4db0b554a0822837618a07e59b6fd92a2b25880e6393'
def require(value):
    if not value:raise ValueError('Audit26 evidence binding failed; details withheld')
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
require(git('rev-parse','HEAD').decode().strip()==a.commit and not git('status','--porcelain'))
require(subprocess.run(['/usr/bin/git','merge-base','--is-ancestor',CORE,a.commit],cwd=ROOT,env=isolated_env(),capture_output=True).returncode==0)
changes=git('diff','--name-only',CORE,a.commit).decode().splitlines()
require(all(n=='audit/model-evidence-assembler.py' or n.endswith(('.md','.txt')) for n in changes))
runner=ROOT/'audit/model-gate-runner.py';assembler=Path(__file__).resolve()
require(hashlib.sha256(git('show',a.commit+':'+str(assembler.relative_to(ROOT)))).hexdigest()==sha(assembler))
jar=ROOT/'build/model-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
reference=ROOT/'build/help-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
require(sha(jar)==PIN and sha(reference)==REFERENCE and strip_entries(entries(jar))==entries(reference))
actual,prior=entries(jar),entries(reference)
require(set(actual)==set(prior) and {n for n in actual if actual[n]!=prior[n]}=={ENTRY})
require(hashlib.sha256(actual[ENTRY]).hexdigest()==PATCHED_SHA and hashlib.sha256(prior[ENTRY]).hexdigest()==ORIGINAL_SHA)
summary=json.loads((ROOT/'build/model-gate-run-summary.json').read_text())
names={'security','transport','resources','shared','posting','runtime','factory','connect','lock','admission','worker','stop','socket','publication','help','model'}
require(summary['execution_commit']==CORE and summary['execution_dirty'] is False and len(summary['rows'])==16 and {r['gate'] for r in summary['rows']}==names)
require(set(summary['sources'])=={'audit/model-gate-runner.py','audit/model-gate-commands.json','tools/audit_support.py','audit/python-lock.json'} and summary['sources']['audit/model-gate-runner.py']==sha(runner))
commands=json.loads((ROOT/'audit/model-gate-commands.json').read_text())
files=['build/model-gate-run-summary.json','build/model-clean-unit.json','build/model-clean-unit.stdout','build/model-clean-unit.stderr']
for row in summary['rows']:
    require(row['accepted'] is True and row['returncode']==0 and row['stderr_bytes']==0 and row['stderr_sha256']==hashlib.sha256(b'').hexdigest())
    require(row['argv']==shlex.split(commands[row['gate']]))
    path='build/model-clean-'+row['gate']+('-boundary/observations.json' if row['gate'] in ('help','model') else '.json')
    require(row['record']==path and sha(ROOT/path)==row['record_sha256'])
    if row['gate'] not in ('help','model'):require(row['stdout_sha256']==row['record_sha256'])
    else:
        line={'help':'PASS integrated Help boundary; four runtime/mode variants; no browser/controller','model':'PASS model diagnostic gate; four runtime/mode variants; sixteen behavioral negative controls; no controller/profile'}[row['gate']]
        require(row['stdout_sha256']==hashlib.sha256((line+'\n').encode()).hexdigest())
    files.append(path)
files+=['build/model-clean-'+str(i)+'/provenance.json' for i in (1,2)]
for arch in ('aarch64','x64'):
    files+=['build/model-bundled-'+arch+'-'+str(i)+'/provenance.json' for i in (1,2)]
    files+=['build/releases/audit26/RAID-Admin-'+arch+suffix for suffix in ('.zip','.archive.json','-repeat.zip','-repeat.archive.json','.spdx.json','-repeat.spdx.json')]
    require(sha(ROOT/('build/releases/audit26/RAID-Admin-'+arch+'.zip'))==sha(ROOT/('build/releases/audit26/RAID-Admin-'+arch+'-repeat.zip')))
    require(sha(ROOT/('build/releases/audit26/RAID-Admin-'+arch+'.spdx.json'))==sha(ROOT/('build/releases/audit26/RAID-Admin-'+arch+'-repeat.spdx.json')))
    for number,suffix in ((1,''),(2,'-repeat')):
        base='build/releases/audit26/RAID-Admin-'+arch+suffix
        bundle=ROOT/('build/model-bundled-'+arch+'-'+str(number)+'/provenance.json')
        archive=json.loads((ROOT/(base+'.archive.json')).read_text());metadata=json.loads(bundle.read_text())
        spdx=json.loads((ROOT/(base+'.spdx.json')).read_text());provenance=json.loads(spdx['creationInfo']['comment'])
        require(archive['architecture']==metadata['bundled_runtime']['architecture']==arch)
        require(metadata['source_commit']==metadata['packager_commit']==provenance['source_commit']==provenance['packager_commit']==CORE)
        require(archive['archive_sha256']==sha(ROOT/(base+'.zip')) and archive['bundle_provenance_sha256']==sha(bundle))
        require(archive['bundle_tree_sha256']==metadata['bundle_tree_sha256']==provenance['bundle_tree_sha256'])
        require(archive['source_provenance_sha256']==sha(ROOT/('build/model-clean-'+str(number)+'/provenance.json')))
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
    if name.startswith('build/model-clean-') and name.endswith('.json'):
        require(len(proofs)>prior)
        for key in ('candidate_sha256','jar_sha256','candidate_jar_sha256'):
            if key in data:require(data[key]==PIN)
        for key in ('source_commit','fixture_commit','execution_commit','candidate_source_commit','application_source_commit'):
            if key in data:require(data[key]==CORE)
        if 'qualification' in data:require(data['qualification'] is True)
        if 'observations' in data:require(bool(data['observations']))
        if name in ('build/model-clean-factory.json','build/model-clean-shared.json','build/model-clean-transport.json'):require(any(row.get('jar_sha256')==PIN for row in data['observations']))
        elif name in [r['record'] for r in summary['rows']]:require(any(data.get(k)==PIN for k in ('candidate_sha256','jar_sha256','candidate_jar_sha256')))
        if name in ('build/model-clean-1/provenance.json','build/model-clean-2/provenance.json'):require(data['files']['Contents/Resources/RAID_Admin.jar']==PIN)
unit=json.loads((ROOT/'build/model-clean-unit.json').read_text());require(unit['tests_passed']==170 and unit['stdout_sha256']==records['build/model-clean-unit.stdout'] and unit['stderr_sha256']==records['build/model-clean-unit.stderr'])
require(unit['runner_sha256']==sha(ROOT/'audit/model-unit-runner.py')==hashlib.sha256(git('show',CORE+':audit/model-unit-runner.py')).hexdigest())
require(re.fullmatch(rb'\.{170}\n-+\nRan 170 tests in [0-9.]+s\n\nOK\n',(ROOT/'build/model-clean-unit.stderr').read_bytes()) is not None)
model=json.loads((ROOT/'build/model-clean-model-boundary/observations.json').read_text());require(len(model['observations'])==4 and len(model['negative_controls'])==16 and model['unit_tests']==5)
require(model['qualified_baseline_sha256']==REFERENCE and model['original_model_sha256']==ORIGINAL_SHA and model['patched_model_sha256']==PATCHED_SHA)
require({(r['architecture'],r['phase'],r['mutation']) for r in model['negative_controls']}=={(arch,phase,mutation) for arch in ('aarch64','x64') for phase in ('both','product') for mutation in ('original','monitor-read-retained','management-read-retained','wrong-token')})
require(not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==a.commit)
record={'schema':1,'scope':'Audit26 local software qualification and unsigned archives/SBOMs; hardware/native full GUI/physical Intel/signing acceptance deferred or unverified','execution_commit':a.commit,'execution_dirty':False,'candidate_gate_execution_commits':[CORE],'product_build_package_release_commit':CORE,'candidate_regression_gates':16,'unit_tests':170,'jar_sha256':PIN,'preserved_audit25_jar_sha256':REFERENCE,'records':records,'source_proofs':proofs,'assembler_sha256':sha(assembler),'gate_runner_sha256':sha(runner),'gate_summary_sha256':sha(ROOT/'build/model-gate-run-summary.json'),'limits':['No controller contact or production/mounted-volume tests','No firmware or destructive/controller-setting operation','No installed application modification','No actual browser invocation or complete Main/native GUI acceptance','x64 is Rosetta, not physical Intel','Unsigned/unnotarized; redistribution rights unresolved','Password memory/getters/persistence and other documented gaps remain','HTTP remains plaintext']}
with (ROOT/'build/model-final-integrity.json').open('x') as out:out.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print('PASS audit26 evidence binding; sixteen candidate gates, 170 units, paired packages/archives/SBOMs')
