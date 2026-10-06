"""Independent evidence assembly; consumes completed records, never runs app/controller."""
import hashlib,json,re,stat,subprocess,sys,zipfile
from pathlib import Path
sys.path.insert(0,'tools')
from audit_support import ROOT,sha,tree,modes,digest,isolated_env
from verify_builds import check_artifact
from verify_bundles import check_bundle
from runtime import runtime_manifest
APP_COMMIT='1e659d5f8cf590a912eece9fc6e5ce12a54ae5f9'
QA_COMMIT=APP_COMMIT
JAR='202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd'
ORIGINAL='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
LEGACY='948c1d8587b43b7b004f193dd5d5eced4ffa8c6d7fd53943c029149f2245b28a'
REF20='f6e545bbd90e7f9616df448f09cc4a889b909fa8e79a8183af8fa96a71d9f859'
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
def require(value,message):
 if not value:raise ValueError(message)
def blob(commit,name):return hashlib.sha256(git('show',commit+':'+name)).hexdigest()
require(git('rev-parse','HEAD').decode().strip()==QA_COMMIT and not git('status','--porcelain'),'Clean pinned QA checkout required before archival')
paths={k:Path('build/stop-admission-final-'+k+'.json') for k in ('security','transport','runtime','resources','shared','factory','posting','connect','characterization','lock','admission','worker','stop')}
records={k:json.loads(p.read_text()) for k,p in paths.items()};checked=0
for key,d in records.items():
 fc=d['fixture_commit'];require(fc in (APP_COMMIT,QA_COMMIT) and d['fixture_dirty'] is False,'Fixture state differs: '+key)
 if 'qualification' in d:require(d['qualification'] is True,'Nonqualification record: '+key)
 if 'source_dirty' in d:require(d['source_dirty'] is False,'Dirty application: '+key)
 if 'source_commit' in d:require(d['source_commit']==('47166edbffb5bc07bc045d12fdf90b6b79d77f81' if key=='characterization' else APP_COMMIT),'Application commit differs: '+key)
 if 'application_source_commit' in d:require(d['application_source_commit']==APP_COMMIT,'Resource source differs')
 if 'candidate_sha256' in d:require(d['candidate_sha256']==(LEGACY if key=='characterization' else JAR),'Candidate differs: '+key)
 for group in ('source_hashes','verifier_sources','fixture_sources','sources','harness_sources'):
  for name,value in d.get(group,{}).items():
   require(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) and not Path(name).is_absolute() and '..' not in Path(name).parts,'Source hash shape differs')
   require(blob(fc,name)==value and sha(ROOT/name)==value,'Record source changed: '+key+' '+name);checked+=1
 if 'tool_sha256' in d:
  name='tools/check_architectures.py' if key=='runtime' else 'tools/check_transport.py'
  require(d['tool_sha256']==blob(fc,name)==sha(ROOT/name),'Tool hash differs');checked+=1
 if 'runtime_trees' in d:require(d['runtime_trees']=={a:r['tree_sha256'] for a,r in runtime_manifest()['architectures'].items()},'Runtime lock differs: '+key)
 if key not in ('security','runtime'):
  observed={r['architecture'] for r in d['observations']};require(observed=={'aarch64','x64'},'Architecture coverage differs: '+key)
counts={'security':2,'transport':6,'runtime':2,'resources':8,'shared':4,'factory':4,'posting':10,'connect':46,'characterization':8,'lock':20,'admission':40,'worker':120,'stop':104}
require({k:len(d['observations']) for k,d in records.items()}==counts,'Gate coverage differs')
worker=records['worker'];require(worker['reference_sha256']==REF20,'Ownership predecessor differs')
wkeys=[]
for r in worker['observations']:
 require(r['jar_sha256']==(REF20 if r['policy']=='legacy' else JAR),'Worker variant differs')
 require(r['execution'] in ('-Xint','-Xcomp') and r['lines'][-1].endswith(('guarded_operations=0','guarded_operations=0; production transport unqualified')),'Worker result shape differs')
 wkeys.append((r['architecture'],r['execution'],r['policy'],r['scenario'],tuple(r['lines'])))
require(len(set(wkeys))==120,'Worker vector uniqueness differs')
require(sum(r['policy']=='legacy' for r in worker['observations'])==24,'Legacy callback controls differ')
require(sum(r['scenario'].startswith('WorkerCompletionBatchObservation') for r in worker['observations'])==4,'Mixed completion coverage differs')
require(sum(r.get('fixture_assertion_control',False) for r in records['connect']['observations'])==4,'Assertion oracle coverage differs')
require({(r['architecture'],r['execution']) for r in records['connect']['observations'] if r.get('fixture_assertion_control')}=={(a,e) for a in ('aarch64','x64') for e in ('-Xint','-Xcomp')},'Assertion oracle Cartesian coverage differs')
for r in records['factory']['observations']:require(r['rows']==116 and r['invoked_per_sweep']==58 and r['excluded_per_sweep']==1 and r['guarded_operations']==0,'Factory coverage differs')
for directory,arch in (('arm64','aarch64'),('x64','x64')):
 root=ROOT/('build/logging-bundled-'+directory+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk')
 from runtime import verify_runtime
 verify_runtime(root,runtime_manifest()['architectures'][arch])
 home_hash=digest(tree(root/'Contents/Home'))
 matched=[r for r in records['runtime']['observations'] if 'architecture='+('x86_64' if arch=='x64' else arch) in r['api']]
 require(len(matched)==1 and matched[0]['runtime_tree_sha256']==home_hash,'Runtime Home observation binding differs')
for r in records['runtime']['observations']:require(r['parity']=='PASS' and len(r['recovery_regression'])==143,'Runtime recovery differs')
first,p1=check_artifact(ROOT/'build/stop-admission-clean-1');second,p2=check_artifact(ROOT/'build/stop-admission-clean-2')
require(first==second and p1['source_commit']==p2['source_commit']==APP_COMMIT and p1['source_dirty'] is p2['source_dirty'] is False,'Paired source builds differ')
require(first==json.loads((ROOT/'audit/expected-build.json').read_text())['expected'],'Expected build differs')
require(sha(ROOT/'build/stop-admission-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar')==JAR,'JAR differs')
require(sha(ROOT/'original/RAID_Admin_original.jar')==ORIGINAL and stat.S_IMODE((ROOT/'original/RAID_Admin_original.jar').stat().st_mode)==0o444,'Immutable original differs')
installed=Path('/Applications/RAID Admin.app');reference=ROOT.parent/'audit/reference/RAID Admin.app';intake=json.loads((ROOT/'audit/intake-provenance.json').read_text())
require(tree(installed)==tree(reference)==intake['bundle_file_hashes']['installed'],'Installed intake contents changed')
require(modes(installed)==modes(reference),'Installed reference modes differ')
packages={};diagnostics={}
for arch in ('aarch64','x64'):
 a=ROOT/('build/stop-admission-bundled-'+arch+'-1');b=ROOT/('build/stop-admission-bundled-'+arch+'-2')
 require(check_bundle(a,ROOT/'build/stop-admission-clean-1')==check_bundle(b,ROOT/'build/stop-admission-clean-2'),'Repeated bundle differs')
 ma=json.loads((a/'provenance.json').read_text());mb=json.loads((b/'provenance.json').read_text())
 require(ma['source_commit']==mb['source_commit']==APP_COMMIT and ma['source_dirty'] is mb['source_dirty'] is False and not ma['packager_dirty'] and not mb['packager_dirty'],'Package source state differs')
 require(ma['packager_commit'] in (APP_COMMIT,QA_COMMIT) and mb['packager_commit']==ma['packager_commit'],'Package commit differs')
 require(ma['source_provenance_sha256']==sha(ROOT/'build/stop-admission-clean-1/provenance.json') and mb['source_provenance_sha256']==sha(ROOT/'build/stop-admission-clean-2/provenance.json'),'Source provenance file hash differs')
 require(ma['bundled_runtime']['signature_verification']==mb['bundled_runtime']['signature_verification']=='vendor signature verified after byte-only copy; never re-signed','Vendor signature attestation differs')
 require({k:v for k,v in ma.items() if k!='source_provenance_sha256'}=={k:v for k,v in mb.items() if k!='source_provenance_sha256'},'Package metadata differs beyond source provenance')
 packages[arch]={'bundle_tree_sha256':ma['bundle_tree_sha256'],'packager_commit':ma['packager_commit'],'vendor_signature_verified':True,'application_signing':ma['application_signing'],'application_notarization':ma['application_notarization'],'source_provenance_hashes':[ma['source_provenance_sha256'],mb['source_provenance_sha256']]}
 diag=json.loads((ROOT/('build/stop-admission-diagnostics-'+arch+'.json')).read_text())
 require(diag['compatibility_version']=='1.5.1-modern.audit.22' and diag['source_commit']==APP_COMMIT and diag['matches_build_manifest'] and diag['matches_reviewed_artifact'] and diag['compatibility_version_matches_reviewed_artifact'] and diag['bundled_jre']['architecture']==arch and diag['bundle_tree_sha256']==ma['bundle_tree_sha256'],'Diagnostic artifact claims differ')
 require(diag['controller_discovery']=='not run; no controller traffic generated' and diag['runtime_selected']=='not evaluated; application not launched','Diagnostic operation scope differs')
 diagnostics[arch]=diag
text=(ROOT/'build/stop-admission-clean-tests.stderr').read_text();require(re.search(r'^Ran 136 tests in [0-9.]+s\n\nOK\n$',text,re.M) is not None,'Unit tests did not pass')
unit_sources={str(p.relative_to(ROOT)):sha(p) for folder in ('tests','tools') for p in (ROOT/folder).rglob('*.py')}
require(all(blob(QA_COMMIT,n)==h for n,h in unit_sources.items()),'Unit sources differ')
unit={'tests_passed':136,'fixture_commit':QA_COMMIT,'source_inputs_match_clean_commit':True,'execution_worktree_dirty':False,'execution_worktree_scope':'Clean pinned source checkout; all test/tool Python inputs checked against its commit','source_hashes':unit_sources,'stderr_sha256':sha(ROOT/'build/stop-admission-clean-tests.stderr'),'stdout_sha256':sha(ROOT/'build/stop-admission-clean-tests.stdout')}
with zipfile.ZipFile(ROOT/'build/worker-exit-clean-3/RAID Admin.app/Contents/Resources/RAID_Admin.jar') as z:old={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(ROOT/'build/stop-admission-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar') as z:new={n:z.read(n) for n in z.namelist()}
require(set(old)<=set(new),'Audit.21 entries removed')
changed={n:{'before':hashlib.sha256(old[n]).hexdigest() if n in old else None,'after':hashlib.sha256(new[n]).hexdigest()} for n in new if old.get(n)!=new[n]}
require(set(changed)=={'com/apple/xsr/net/CommunicationsManager.class'},'Audit21 entry delta differs')
sbom={'format':'project inventory schema 1 (not asserted SPDX/CycloneDX conformant)','scope':'Complete audit.22 application JAR entry hashes; original dependency inventory unchanged in sbom.json; runtimes separately inventoried in runtime-lock.json','jar_sha256':JAR,'application_source_commit':APP_COMMIT,'third_party_dependencies_added':[],'files':{n:hashlib.sha256(v).hexdigest() for n,v in new.items() if not n.endswith('/')},'qualification_ledger':'stop-admission-final-integrity.json'}
require(len(sbom['files'])==3061,'Candidate entry count differs')
stop=records['stop'];require(stop['candidate_manager_sha256']=='f2960fbf802500891e23a916441f8b7c586d9ae70d6dba5760d40bc9acf04059' and stop['jar_delta_from_reference']==['com/apple/xsr/net/CommunicationsManager.class'],'Shipped guard linkage differs')
require(sum(bool(r['dispatch_compilation']) for r in stop['observations'])==52,'Installed dispatch compilation coverage differs')
require(sum(r['scenario'].startswith('active:') for r in stop['observations'])==16,'After-admission actual candidate coverage differs')
# Nothing is written to the audit record until all independent assertions pass.
archived={}
for key,path in paths.items():
 dest=ROOT/('audit/stop-admission-clean-'+('historical-characterization' if key=='characterization' else key)+'.json');dest.write_bytes(path.read_bytes());archived[str(dest.relative_to(ROOT))]=sha(dest)
for key,data in [('tests',unit),('packages',packages),('sbom',sbom),('diagnostics-aarch64',diagnostics['aarch64']),('diagnostics-x64',diagnostics['x64'])]:
 dest=ROOT/('audit/stop-admission-sbom.json' if key=='sbom' else 'audit/stop-admission-clean-'+key+'.json');dest.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');archived[str(dest.relative_to(ROOT))]=sha(dest)
ledger={'application_source_commit':APP_COMMIT,'fixture_commits':{k:d['fixture_commit'] for k,d in records.items()},'evidence_assembly_commit':QA_COMMIT,'all_sources_clean':True,'source_cleanliness_scope':'Clean pinned application, fixture, packager and assembly checkout before archival writes','assembly_correction':'Historical records preserved; this assembler writes distinct audit22 records after all assertions pass.','integrity_generator':'audit/stop-admission-evidence-assembler.py','candidate_version':'1.5.1-modern.audit.22','candidate_jar_sha256':JAR,'original_jar_sha256':ORIGINAL,'original_mode':'0444','audit20_worker_reference_sha256':REF20,'audit21_reference_sha256':'9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562','changed_entries_from_audit21':changed,'records':archived,'gate_observation_counts':counts,'checked_source_hash_entries':checked,'checked_source_hash_definition':'Each gate source-map entry and tool hash, including repeated names, verified against its own clean fixture commit and current bytes. Historical application source is separate and remains pinned. Unit test sources also bound to QA commit.','python_tests_passed':136,'runtime_hash_scopes':{'gate_lock':'Runtime.jdk files plus file modes; directory modes separately verified','architecture_matrix':'Runtime.jdk/Contents/Home file-content map only','package':'application files plus file and directory modes'},'packages':packages,'installed_jar_sha256':sha(installed/'Contents/Resources/RAID_Admin.jar'),'installed_contents_intake_pinned':True,'installed_reference_files_and_modes_match':True,'installed_intake_map_digest':digest(intake['bundle_file_hashes']['installed']),'x64_execution':'Rosetta on arm64 host, not physical Intel','controller_contact':False,'production_or_mounted_volume_tests':False,'installed_application_modified':False,'action_scope_attestation':'Agent/tool history attestation, not packet or hardware evidence. All feature gates use headless guards, memory transport or no transport; diagnostics perform no discovery or launch.','excluded_runs':['Preliminary development sources before independent assertions/send-entry counters','PrintCompilation stdout interleaving','Full-Xcomp stale compilation task with no installed dispatch nmethod','Initial integrated diagnostics using obsolete audit21 golden; corrected explicitly before source commit'],'limits':'Native GUI, physical Intel, controller compatibility and release readiness unqualified. VME, ThreadDeath, allocation and metadata failure completion best-effort. Slow replies and connect/write/whole-operation deadlines unresolved. Final stop admission is qualified only in memory fixtures; no atomic stop-versus-TCP cancellation. After admission, wait for actual outcome or report unconfirmed; no same-worker replay. Async fatal-exit callbacks move to EDT; disposed AppContext unqualified. Outbound mutability, status/empty-ack ambiguity and GUI firmware-file binding open. HTTP remains plaintext. Original cache-disable/firmware flow unchanged.','integrity_generator_sha256':sha(Path(__file__))}
(ROOT/'audit/stop-admission-evidence-assembler.py').write_bytes(Path(__file__).read_bytes())
dest=ROOT/'audit/stop-admission-final-integrity.json';dest.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n');print('PASS independent stop-admission evidence assembly; '+str(checked)+' source hash entries; ledger '+sha(dest))
