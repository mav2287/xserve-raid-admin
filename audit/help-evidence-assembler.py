"""Bind completed local audit25 checks to artifacts and their actual Git source."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import sha,isolated_env,verify_python
verify_python()
from verify_builds import entries
from help_patch import strip_entries
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);a=p.parse_args()
CORE='82f9c4fe3de52be3baf41132d8e521911419e177'
def require(value):
    if not value:raise ValueError('Audit25 evidence binding failed')
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
require(git('rev-parse','HEAD').decode().strip()==a.commit and not git('status','--porcelain'))
jar=ROOT/'build/help-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
reference=ROOT/'build/connection-publication-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
require(sha(jar)=='59087dceed5865b08cef4db0b554a0822837618a07e59b6fd92a2b25880e6393' and sha(reference)=='9592145c933f611888a00cb159340a86f99d427672483701212023078f823553')
require(strip_entries(entries(jar))==entries(reference))
files=['build/help-clean-'+name+'.json' for name in ('security','transport','resources','shared','posting','runtime','factory','connect','lock','admission','worker','stop','socket','publication','unit')]
files+=['build/help-clean-boundary/observations.json','build/help-clean-1/provenance.json','build/help-clean-2/provenance.json']
for arch in ('aarch64','x64'):
    files += ['build/help-bundled-'+arch+'-'+str(i)+'/provenance.json' for i in (1,2)]
    files += ['build/releases/audit25/RAID-Admin-'+arch+suffix for suffix in ('.zip','.archive.json','-repeat.zip','-repeat.archive.json','.spdx.json','-repeat.spdx.json')]
    require(sha(ROOT/('build/releases/audit25/RAID-Admin-'+arch+'.zip'))==sha(ROOT/('build/releases/audit25/RAID-Admin-'+arch+'-repeat.zip')))
    require(sha(ROOT/('build/releases/audit25/RAID-Admin-'+arch+'.spdx.json'))==sha(ROOT/('build/releases/audit25/RAID-Admin-'+arch+'-repeat.spdx.json')))
records={};proofs=[]
summary=json.loads((ROOT/'build/help-gate-run-summary.json').read_text())
require(len(summary)==14 and all(row['accepted'] for row in summary if row['gate']!='stop') and [row['gate'] for row in summary if not row['accepted']]==['stop'])
rerun=json.loads((ROOT/'build/help-stop-rerun-summary.json').read_text());require(rerun['accepted'] and rerun['execution_commit']==a.commit and rerun['stdout_sha256']==sha(ROOT/'build/help-clean-stop.json'))
for row in summary:
    if row['gate']=='stop':continue
    require(sha(ROOT/('build/help-clean-'+row['gate']+'.json'))==row['stdout_sha256'])
for arch in ('aarch64','x64'):
    for number,suffix in ((1,''),(2,'-repeat')):
        base='build/releases/audit25/RAID-Admin-'+arch+suffix
        bundle=ROOT/('build/help-bundled-'+arch+'-'+str(number)+'/provenance.json')
        archive=json.loads((ROOT/(base+'.archive.json')).read_text());metadata=json.loads(bundle.read_text())
        spdx=json.loads((ROOT/(base+'.spdx.json')).read_text());provenance=json.loads(spdx['creationInfo']['comment'])
        require(archive['archive_sha256']==sha(ROOT/(base+'.zip')) and archive['bundle_provenance_sha256']==sha(bundle))
        require(archive['bundle_tree_sha256']==metadata['bundle_tree_sha256']==provenance['bundle_tree_sha256'])
        require(archive['source_provenance_sha256']==sha(ROOT/('build/help-clean-'+str(number)+'/provenance.json')))
        require(provenance['negative_controls']==12 and provenance['execution_state']['commit']==a.commit and provenance['execution_state']['dirty'] is False)

def walk(value,record,commit):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('sources','source_hashes','input_hashes','verifier_sources','fixture_sources','harness_sources') and isinstance(item,dict):
                for name,h in item.items():
                    path=ROOT/name
                    require(isinstance(h,str) and len(h)==64 and path.is_file() and not Path(name).is_absolute() and '..' not in Path(name).parts)
                    require(sha(path)==h and hashlib.sha256(git('show',commit+':'+name)).hexdigest()==h)
                    proofs.append({'record':record,'source':name,'sha256':h,'verified_commit':commit})
            if key in ('source_dirty','fixture_dirty','candidate_source_dirty','execution_dirty','packager_dirty','dirty'):require(item is False)
            walk(item,record,commit)
    elif isinstance(value,list):
        for item in value:walk(item,record,commit)
for name in files:
    path=ROOT/name;require(path.is_file());records[name]=sha(path)
    if name.endswith('.json'):
        data=json.loads(path.read_text())
        commit=data.get('fixture_commit',data.get('execution_commit',data.get('packager_commit',data.get('source_commit'))))
        if 'execution_state' in data:commit=data['execution_state']['commit']
        if 'creationInfo' in data:commit=json.loads(data['creationInfo']['comment'])['execution_state']['commit']
        require(commit in (CORE,a.commit))
        prior=len(proofs);walk(data,name,commit)
        if name.startswith('build/help-clean-') or name=='build/help-clean-boundary/observations.json':
            for key in ('candidate_sha256','jar_sha256','candidate_jar_sha256'):
                if key in data:require(data[key]==sha(jar))
            for key in ('source_commit','fixture_commit','execution_commit'):
                if key in data:require(data[key]==a.commit if name=='build/help-clean-unit.json' else data[key] in (CORE,a.commit))
        if 'creationInfo' in data and 'comment' in data['creationInfo']:
            walk(json.loads(data['creationInfo']['comment']),name,commit)
        if name.startswith('build/help-clean-') and name.endswith('.json') or name=='build/help-clean-boundary/observations.json':
            require(len(proofs)>prior)
            if 'qualification' in data:require(data['qualification'] is True)
require(json.loads((ROOT/'build/help-clean-unit.json').read_text())['tests_passed']==165)
record={'schema':1,'scope':'Audit25 local software qualification and unsigned archive/SBOM preparation; hardware/native GUI/physical Intel/signing acceptance deferred or unverified','execution_commit':a.commit,'candidate_gate_execution_commits':[CORE,a.commit],'execution_dirty':False,'jar_sha256':sha(jar),'preserved_audit24_core_sha256':sha(reference),'candidate_regression_gates':15,'unit_tests':165,'records':records,'source_proofs':proofs,'assembler_sha256':sha(Path(__file__)),'gate_runner_sha256':sha(ROOT/'build/help-gate-runner.py'),'gate_summary_sha256':sha(ROOT/'build/help-gate-run-summary.json'),'stop_rerun_summary_sha256':sha(ROOT/'build/help-stop-rerun-summary.json'),'excluded_first_stop_failure':'audit25 initial comparison still expected audit21 UI entries; no product or fixture timing change, corrected with exact locked Help reversal','limits':['No controller contact or production/mounted-volume tests','No firmware transmission or destructive/controller-setting operation','No installed application modification','No actual browser invocation or complete Main/native GUI acceptance','x64 runtime is Rosetta, not physical Intel','Unsigned/unnotarized; redistribution rights unresolved','Remaining legacy diagnostic/model security and other documented gaps are not waived','HTTP remains plaintext']}
out=ROOT/'build/help-final-integrity.json'
with out.open('x') as f:f.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print('PASS audit25 evidence binding; 15 candidate gates, 165 units, paired packages/archives/SBOMs')
