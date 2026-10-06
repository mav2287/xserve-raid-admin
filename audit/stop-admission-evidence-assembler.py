"""Independent evidence assembly; consumes completed records, never runs app/controller."""
import hashlib,json,re,stat,subprocess,sys,zipfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
os.chdir(ROOT)
from audit_support import ROOT,sha,tree,modes,digest,isolated_env,verify_python
from verify_builds import check_artifact
from verify_bundles import check_bundle
from runtime import runtime_manifest
APP_COMMIT='1e659d5f8cf590a912eece9fc6e5ce12a54ae5f9'
QA_COMMIT='73ffa4efbfbab852c7d6990f5087d180b53751bb'
JAR='202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd'
ORIGINAL='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
LEGACY='948c1d8587b43b7b004f193dd5d5eced4ffa8c6d7fd53943c029149f2245b28a'
REF20='f6e545bbd90e7f9616df448f09cc4a889b909fa8e79a8183af8fa96a71d9f859'
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
def require(value,message):
 if not value:raise ValueError(message)
def blob(commit,name):return hashlib.sha256(git('show',commit+':'+name)).hexdigest()
ARCHIVAL={ 'audit/stop-admission-'+n for n in ('clean-'+k+'.json' for k in ('security','transport','runtime','resources','shared','factory','posting','connect','historical-characterization','lock','admission','worker','stop','tests','packages','diagnostics-aarch64','diagnostics-x64')) } | {'audit/stop-admission-'+n for n in ('evidence-assembler.py','final-integrity.json','sbom.json','pre-review-integrity.json','pre-review-evidence-assembler.py','pre-review-stop.json','pre-review-tests.json','unit-runner.py','clean-tests.stdout','clean-tests.stderr')}
verify_python()
assembly_status=git('status','--porcelain').decode().splitlines()
require(git('rev-parse','HEAD').decode().strip()==QA_COMMIT and all(line.startswith('?? ') and line[3:] in ARCHIVAL for line in assembly_status),'Pinned QA checkout with only explicit archival files required')
paths={k:Path('build/stop-admission-final-'+k+'.json') for k in ('security','transport','runtime','resources','shared','factory','posting','connect','characterization','lock','admission','worker','stop')}
raw_records={k:p.read_bytes() for k,p in paths.items()};records={k:json.loads(value) for k,value in raw_records.items()};checked=0
for key,d in records.items():
 fc=d['fixture_commit'];require(fc==(QA_COMMIT if key=='stop' else APP_COMMIT) and d['fixture_dirty'] is False,'Fixture state differs: '+key)
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
nested_counts={}
def outcomes(value, label):
 if isinstance(value,dict):
  for name,data in value.items():
   if name in ('lines','results') and isinstance(data,list):
    require(bool(data) and isinstance(data[-1],str) and data[-1].startswith('PASS'),'Missing PASS outcome: '+label)
    require(not any(line.startswith(('FAIL','ERROR')) for line in data),'Failure outcome: '+label)
   elif name=='result' and isinstance(data,str):require(data=='PASS','Policy result differs: '+label)
   else:outcomes(data,label+'/'+name)
 elif isinstance(value,list):
  for row in value:outcomes(row,label)
for key,data in records.items():
 outcomes(data,key)
 nested_counts[key]={name:len(rows) for name,rows in data.items() if name.endswith('observations') and isinstance(rows,list)}
for row in records['security']['observations']:require(row[-1].startswith('PASS'),'Security PASS missing')
require(nested_counts=={'security': {'observations': 2}, 'transport': {'observations': 6, 'parser_observations': 4, 'allocation_observations': 4, 'header_observations': 4, 'worker_failure_observations': 12, 'operation_failure_observations': 4, 'terminal_io_observations': 6, 'null_io_observations': 2, 'io_observations': 4}, 'runtime': {'observations': 2}, 'resources': {'observations': 8, 'policy_observations': 6}, 'shared': {'observations': 4}, 'factory': {'observations': 4}, 'posting': {'observations': 10}, 'connect': {'observations': 46}, 'characterization': {'observations': 8}, 'lock': {'observations': 20}, 'admission': {'observations': 40}, 'worker': {'observations': 120}, 'stop': {'observations': 104}},'Nested matrix coverage differs')
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
require({(r['architecture'],r['jar_sha256']) for r in records['factory']['observations']}=={(a,j) for a in ('aarch64','x64') for j in (ORIGINAL,JAR)},'Factory artifact Cartesian coverage differs')
for r in records['factory']['observations']:require(r['rows']==116 and r['invoked_per_sweep']==58 and r['excluded_per_sweep']==1 and r['guarded_operations']==0,'Factory coverage differs')
for directory,arch in (('arm64','aarch64'),('x64','x64')):
 root=ROOT/('build/stop-admission-bundled-'+arch+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk')
 from runtime import verify_runtime
 verify_runtime(root,runtime_manifest()['architectures'][arch])
 home_hash=digest(tree(root/'Contents/Home'))
 matched=[r for r in records['runtime']['observations'] if 'architecture='+('x86_64' if arch=='x64' else arch) in r['api']]
 require(len(matched)==1 and matched[0]['runtime_tree_sha256']==home_hash,'Runtime Home observation binding differs')
reviewed_recovery=json.loads((ROOT/'audit/stopped-post-recovery-expected.json').read_text())
require(reviewed_recovery['candidate_jar_sha256']==JAR,'Runtime recovery candidate differs')
require(sum('method=run;' in line for line in reviewed_recovery['lines'])==1 and sum('callback-drain-unqualified' in line for line in reviewed_recovery['lines'])==2,'Runtime recovery adaptation differs')
expected_recovery=[line.replace('method=run;','method=dispatchLoop;').replace('queued=1; callback-drain-unqualified','queued=0; callbacks=2; terminal-drain') for line in reviewed_recovery['lines']]
for r in records['runtime']['observations']:
 require(r['parity']=='PASS' and r['recovery_regression']==expected_recovery and len(expected_recovery)==143,'Runtime recovery differs')
 for name,value in r.items():
  if name.endswith('_regression'):
   require((isinstance(value,str) and value.startswith('PASS')) or (isinstance(value,list) and value and value[-1].startswith('PASS')),'Runtime regression PASS missing')
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
run=json.loads((ROOT/'build/stop-admission-reviewed-tests-run.json').read_text());require(run['returncode']==0 and run['execution_commit']==QA_COMMIT and run['execution_worktree_status']==assembly_status,'Reviewed unit execution provenance differs')
require(run['stdout_sha256']==sha(ROOT/'build/stop-admission-reviewed-tests.stdout') and run['stderr_sha256']==sha(ROOT/'build/stop-admission-reviewed-tests.stderr'),'Reviewed unit output differs')
text=(ROOT/'build/stop-admission-reviewed-tests.stderr').read_text();require(re.fullmatch(r'\.{137}\n-+\nRan 137 tests in [0-9.]+s\n\nOK\n',text) is not None,'Unit tests did not pass')
unit_sources={str(p.relative_to(ROOT)):sha(p) for folder in ('tests','tools') for p in (ROOT/folder).rglob('*.py')}
require(all(blob(QA_COMMIT,n)==h for n,h in unit_sources.items()),'Unit sources differ')
require(run['source_hashes']==unit_sources,'Unit inputs differ from run metadata')
require(run['tests_passed']==137 and run['runner']=='audit/stop-admission-unit-runner.py' and run['runner_sha256']==sha(ROOT/run['runner']),'Unit runner identity/count differs')
require(sha(ROOT/'audit/stop-admission-clean-tests.stdout')==run['stdout_sha256'] and sha(ROOT/'audit/stop-admission-clean-tests.stderr')==run['stderr_sha256'],'Archived unit output differs')
unit=dict(run,fixture_commit=QA_COMMIT,source_inputs_match_clean_commit=True,execution_worktree_dirty=bool(assembly_status),execution_worktree_scope='Archival-only working tree; exact files and run inputs recorded')
reference_jar=ROOT/'build/worker-exit-clean-3/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
require(sha(reference_jar)=='9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562','Audit21 reference JAR differs')
with zipfile.ZipFile(ROOT/'build/worker-exit-clean-3/RAID Admin.app/Contents/Resources/RAID_Admin.jar') as z:old={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(ROOT/'build/stop-admission-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar') as z:new={n:z.read(n) for n in z.namelist()}
require(set(old)<=set(new),'Audit.21 entries removed')
changed={n:{'before':hashlib.sha256(old[n]).hexdigest() if n in old else None,'after':hashlib.sha256(new[n]).hexdigest()} for n in new if old.get(n)!=new[n]}
require(set(changed)=={'com/apple/xsr/net/CommunicationsManager.class'},'Audit21 entry delta differs')
sbom={'format':'project inventory schema 1 (not asserted SPDX/CycloneDX conformant)','scope':'Complete audit.22 application JAR entry hashes; original dependency inventory unchanged in sbom.json; runtimes separately inventoried in runtime-lock.json','jar_sha256':JAR,'application_source_commit':APP_COMMIT,'third_party_dependencies_added':[],'files':{n:hashlib.sha256(v).hexdigest() for n,v in new.items() if not n.endswith('/')},'qualification_ledger':'stop-admission-final-integrity.json'}
require(len(sbom['files'])==3061,'Candidate entry count differs')
stop=records['stop'];reference_manifest=json.loads((reference_jar.parents[3]/'provenance.json').read_text())
historical_reference=json.loads((ROOT/'audit/worker-exit-final-integrity.json').read_text())
require(historical_reference['candidate_jar_sha256']==sha(reference_jar) and historical_reference['application_source_commit']==stop['application_reference_source_commit'],'Tracked audit21 reference binding differs')
require(stop['application_reference_sha256']==sha(reference_jar) and stop['application_reference_source_commit']==reference_manifest['source_commit'] and not reference_manifest['source_dirty'],'Stop reference source linkage differs')
scenarios=['admission:'+k for k in ('sync','async')]+['exposure:'+k for k in ('sync','async','sync-interrupted','sync-queue','async-queue','sync-flag','async-flag','sync-mutating','async-mutating')]+['active:'+k for k in ('sync','async')]
require({(r['architecture'],r['execution'],r['scenario'],r['policy']) for r in stop['observations']}=={(a,e,k,p) for a in ('aarch64','x64') for e in ('-Xint','-Xcomp') for k in scenarios for p in ('legacy','guarded')},'Stop Cartesian coverage differs')
require(stop['candidate_manager_sha256']=='f2960fbf802500891e23a916441f8b7c586d9ae70d6dba5760d40bc9acf04059' and stop['jar_delta_from_reference']==['com/apple/xsr/net/CommunicationsManager.class'],'Shipped guard linkage differs')
require(sum(bool(r['dispatch_compilation']) for r in stop['observations'])==52,'Installed dispatch compilation coverage differs')
require(sum(r['scenario'].startswith('active:') for r in stop['observations'])==16,'After-admission control coverage differs')
import tempfile
from stop_admission_fixtures import build as admission_build
from stop_exposure_fixtures import build as exposure_build
hook_hashes={}
with tempfile.TemporaryDirectory(prefix='raid-stop-evidence-hooks-') as tmp:
 for label,builder in (('admission',admission_build),('exposure',exposure_build)):
  directory=Path(tmp)/label;directory.mkdir()
  hook_hashes[label]={policy:sha(jar) for policy,jar in builder(reference_jar,directory).items()}
active_counts={}
for row in stop['observations']:
 label,kind=row['scenario'].split(':',1);policy=row['policy']
 expected_jar=(JAR if policy=='guarded' else stop['application_reference_sha256']) if label=='active' else hook_hashes[label][policy]
 require(row['fixture_jar_sha256']==expected_jar,'Stop fixture reconstruction differs')
 expected='PASS stop-'+label+' '+kind+' '+policy+' attempts='+('0' if policy=='guarded' else '1')+' memory only; forbidden_attempts=0'
 if label=='active':
  expected='PASS stop-active '+kind+' characterization; claimed_before_serialization_completes=true stop_before_release=true attempts=1 real_reply_preserved=true no_replay=true forbidden_attempts=0'
  active_counts[policy]=active_counts.get(policy,0)+1
 require(row['lines']==[expected],'Exact stop outcome differs')
 if row['execution']=='-Xcomp':
  flags=row['execution_flags'];require(len(flags)==6 and flags[:3]==['-Xcomp','-XX:+UnlockDiagnosticVMOptions','-XX:+LogCompilation'] and flags[4:]==['-XX:CompileCommand=quiet','-XX:CompileCommand=compileonly,com/apple/xsr/net/CommunicationsManager.dispatchLoop'] and flags[3].startswith('-XX:LogFile='),'Targeted compilation flags differ')
  log=Path(flags[3].split('=',1)[1]);require(log.parent.name==label and log.name==policy+'-'+row['architecture']+'-Xcomp-'+kind+'-jit.xml','Compilation log identity differs')
  require(bool(row['dispatch_compilation']) and all(n.get('method')=='com/apple/xsr/net/CommunicationsManager dispatchLoop ()V' for n in row['dispatch_compilation']),'Dispatch compilation events differ')
 else:require(row['execution']=='-Xint' and row['execution_flags']==['-Xint'] and not row['dispatch_compilation'],'Interpreter compilation metadata differs')
require(active_counts=={'legacy':8,'guarded':8},'Actual candidate/reference control split differs')
pre_review=json.loads((ROOT/'audit/stop-admission-pre-review-integrity.json').read_text())
require(sha(ROOT/'audit/stop-admission-pre-review-evidence-assembler.py')==pre_review['integrity_generator_sha256'],'Preserved pre-review generator differs')
for name in ('stop','tests'):
 require(sha(ROOT/('audit/stop-admission-pre-review-'+name+'.json'))==pre_review['records']['audit/stop-admission-clean-'+name+'.json'],'Preserved pre-review record differs')
# Nothing is written to the audit record until all independent assertions pass.
archived={}
for key,path in paths.items():
 dest=ROOT/('audit/stop-admission-clean-'+('historical-characterization' if key=='characterization' else key)+'.json');dest.write_bytes(raw_records[key]);archived[str(dest.relative_to(ROOT))]=sha(dest)
for key,data in [('tests',unit),('packages',packages),('sbom',sbom),('diagnostics-aarch64',diagnostics['aarch64']),('diagnostics-x64',diagnostics['x64'])]:
 dest=ROOT/('audit/stop-admission-sbom.json' if key=='sbom' else 'audit/stop-admission-clean-'+key+'.json');dest.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');archived[str(dest.relative_to(ROOT))]=sha(dest)
archived['audit/stop-admission-unit-runner.py']=sha(ROOT/'audit/stop-admission-unit-runner.py')
for channel in ('stdout','stderr'):archived['audit/stop-admission-clean-tests.'+channel]=sha(ROOT/('audit/stop-admission-clean-tests.'+channel))
ledger={'application_source_commit':APP_COMMIT,'fixture_commits':{k:d['fixture_commit'] for k,d in records.items()},'evidence_assembly_commit':QA_COMMIT,'all_sources_clean':True,'source_cleanliness_scope':'Recorded application, fixture and packager sources clean; assembler checkout has only explicitly listed archival files','evidence_assembly_worktree_status':assembly_status,'assembly_correction':'Claude review tightened PASS, hook reconstruction, reference/runtime/factory identity and unit execution checks; pre-review ledger and generator preserved separately. Historical audit21 and earlier records untouched.','integrity_generator':'audit/stop-admission-evidence-assembler.py','candidate_version':'1.5.1-modern.audit.22','candidate_jar_sha256':JAR,'original_jar_sha256':ORIGINAL,'original_mode':'0444','audit20_worker_reference_sha256':REF20,'audit21_reference_sha256':'9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562','changed_entries_from_audit21':changed,'records':archived,'superseded_pre_review':{n:sha(ROOT/n) for n in ('audit/stop-admission-pre-review-integrity.json','audit/stop-admission-pre-review-evidence-assembler.py','audit/stop-admission-pre-review-stop.json','audit/stop-admission-pre-review-tests.json')},'superseded_record_scope':'Pre-review ledger paths for stop/tests/generator refer to their exact bytes now preserved under pre-review filenames; all other record bytes retained.','gate_observation_counts':counts,'nested_observation_counts':nested_counts,'stop_test_jar_hashes':hook_hashes,'stop_after_admission_controls':active_counts,'stop_compiled_vectors':52,'jit_evidence_scope':'Parsed dispatchLoop nmethod metadata and exact compileonly flags verified; temporary raw XML logs not archived. Only dispatchLoop selected by compileonly; other compiled code, native wrappers and VM helpers not recorded. Earlier gate prose about other methods interpreted describes intent, not proof of absence.','audit21_reference_source_commit':stop['application_reference_source_commit'],'historical_characterization_identity':{'source_commit':records['characterization']['source_commit'],'jar_sha256':LEGACY},'worker_legacy_execution_modes':sorted({r['execution'] for r in worker['observations'] if r['policy']=='legacy'}),'generator_provenance_scope':'Generator exact bytes are bound by hash and archived in the later documentation commit; assembly commit identifies the QA checkout, not generator availability there. Stop and unit records use QA commit; application and twelve other gates retain their individually pinned application commit.','checked_source_hash_entries':checked,'checked_source_hash_definition':'Each gate source-map entry and tool hash, including repeated names, verified against its own clean fixture commit and current bytes. Historical application source is separate and remains pinned. Unit test sources also bound to QA commit.','python_tests_passed':137,'runtime_hash_scopes':{'gate_lock':'Runtime.jdk files plus file modes; directory modes separately verified','architecture_matrix':'Runtime.jdk/Contents/Home file-content map only','package':'application files plus file and directory modes'},'packages':packages,'installed_jar_sha256':sha(installed/'Contents/Resources/RAID_Admin.jar'),'installed_contents_intake_pinned':True,'installed_reference_files_and_modes_match':True,'installed_intake_map_digest':digest(intake['bundle_file_hashes']['installed']),'x64_execution':'Rosetta on arm64 host, not physical Intel','controller_contact':False,'production_or_mounted_volume_tests':False,'installed_application_modified':False,'action_scope_attestation':'Agent/tool history attestation, not packet or hardware evidence. All feature gates use headless guards, memory transport or no transport; diagnostics perform no discovery or launch.','excluded_runs':['Preliminary development sources before independent assertions/send-entry counters','PrintCompilation stdout interleaving','Full-Xcomp stale compilation task with no installed dispatch nmethod','Initial integrated diagnostics using obsolete audit21 golden; corrected explicitly before source commit'],'limits':'Native GUI, physical Intel, controller compatibility and release readiness unqualified. VME, ThreadDeath, allocation and metadata failure completion best-effort. Slow replies and connect/write/whole-operation deadlines unresolved. Final stop admission is qualified only in memory fixtures; no atomic stop-versus-TCP cancellation. After admission, wait for actual outcome or report unconfirmed; no same-worker replay. Async fatal-exit callbacks move to EDT; disposed AppContext unqualified. Outbound mutability, status/empty-ack ambiguity and GUI firmware-file binding open. HTTP remains plaintext. Original cache-disable/firmware flow unchanged.','integrity_generator_sha256':sha(Path(__file__))}
(ROOT/'audit/stop-admission-evidence-assembler.py').write_bytes(Path(__file__).read_bytes())
dest=ROOT/'audit/stop-admission-final-integrity.json';dest.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n');print('PASS independent stop-admission evidence assembly; '+str(checked)+' source hash entries; ledger '+sha(dest))
