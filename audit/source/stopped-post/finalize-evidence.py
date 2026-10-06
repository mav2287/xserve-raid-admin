import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
sys.path.insert(0,'tools')
from audit_support import ROOT,sha,tree,modes,digest,isolated_env,verify_python
import platform
verify_python()
from runtime import runtime_manifest,verify_runtime
from verify_builds import check_artifact
from class_patch import AUDIT19_MANAGER_SHA256,assert_stop_lock_order,normalize_stopped_admission
commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],text=True,env=isolated_env()).strip()
assert not subprocess.check_output(['/usr/bin/git','status','--porcelain'],env=isolated_env())
records={name:Path('build/stopped-post-clean-'+name+'.json') for name in ('security','transport','runtime','resources','shared','factory','posting','connect','characterization','lock','admission')}
checked=0
for role,p in records.items():
 assert p.stat().st_size and not p.with_suffix('.stderr').stat().st_size
 d=json.loads(p.read_text());assert d['fixture_commit']==commit and d['fixture_dirty'] is False
 if 'source_dirty' in d:assert d['source_dirty'] is False
 if role!='characterization' and 'source_commit' in d:assert d['source_commit']==commit
 if 'application_source_commit' in d:assert d['application_source_commit']==commit
 if role!='characterization' and 'candidate_sha256' in d:assert d['candidate_sha256']==json.loads(Path('audit/stopped-post-recovery-expected.json').read_text())['candidate_jar_sha256']
 if 'qualification' in d:assert d['qualification'] is True
 for field in ('fixture_sources','verifier_sources','source_hashes','harness_sources','sources'):
  for name,value in d.get(field,{}).items():
   committed=subprocess.check_output(['/usr/bin/git','show',commit+':'+name],env=isolated_env());assert hashlib.sha256(committed).hexdigest()==value==sha(ROOT/name);checked+=1
 if 'tool_sha256' in d:assert d['tool_sha256']==sha(ROOT/('tools/check_transport.py' if role=='transport' else 'tools/check_architectures.py'))
char=json.loads(records['characterization'].read_text());assert char['source_commit']==json.loads(Path('audit/sync-preenqueue-final-integrity.json').read_text())['source_commit']
assert len(char['observations'])==8
for row in char['observations']:
 if row['jar_sha256']==char['candidate_sha256']:assert row['manager_class_sha256']=='7c07f4c31a6104f52ee151e07141296d5b59ef33fa5105b895c6504c58ac2a1c'
connect=json.loads(records['connect'].read_text());assert len(connect['observations'])==42
assert sum('semantic_negative_control' in r for r in connect['observations'])==6
assert json.loads(records['runtime'].read_text())['required_connect_failure_stop']
identity,manifest=check_artifact(Path('build/stopped-post-clean-3'));second,manifest2=check_artifact(Path('build/stopped-post-clean-4'));assert identity==second==json.loads(Path('audit/expected-build.json').read_text())['expected'];assert manifest['source_commit']==manifest2['source_commit']==commit and not manifest['source_dirty'] and not manifest2['source_dirty']
jar=Path('build/stopped-post-clean-3/RAID Admin.app/Contents/Resources/RAID_Admin.jar');oldjar=Path('build/stop-lock-clean-3/RAID Admin.app/Contents/Resources/RAID_Admin.jar');original=Path('original/RAID_Admin_original.jar');entry='com/apple/xsr/net/CommunicationsManager.class'
with zipfile.ZipFile(jar) as a,zipfile.ZipFile(oldjar) as b,zipfile.ZipFile(original) as o:
 changed=sorted(n for n in set(a.namelist())|set(b.namelist()) if (a.read(n) if n in a.namelist() else None)!=(b.read(n) if n in b.namelist() else None));assert changed==['com/apple/xsr/net/CommunicationsManager.class','compat/StoppedDelivery$Callback.class','compat/StoppedDelivery.class'];assert hashlib.sha256(b.read(entry)).hexdigest()==AUDIT19_MANAGER_SHA256;assert normalize_stopped_admission(a.read(entry))==b.read(entry);assert_stop_lock_order(o.read(entry),a.read(entry))
installed=Path('/Applications/RAID Admin.app');reference=Path('../audit/reference/RAID Admin.app');assert tree(installed)==tree(reference) and modes(installed)==modes(reference);assert original.stat().st_mode&0o777==0o444
intake=json.loads(Path('audit/intake-provenance.json').read_text());assert tree(installed)==intake['bundle_file_hashes']['installed'];assert digest(tree(installed))==intake['bundle_tree_hashes']['installed']
bundles={};runtime_scopes={};lock=runtime_manifest()
for arch in ('aarch64','x64'):
 first=Path('build/stopped-post-bundled-'+arch+'-1');second=Path('build/stopped-post-bundled-'+arch+'-2');x=json.loads((first/'provenance.json').read_text());y=json.loads((second/'provenance.json').read_text());assert {k:v for k,v in x.items() if k!='source_provenance_sha256'}=={k:v for k,v in y.items() if k!='source_provenance_sha256'};assert x['source_provenance_sha256']==sha(Path('build/stopped-post-clean-3/provenance.json')) and y['source_provenance_sha256']==sha(Path('build/stopped-post-clean-4/provenance.json'));assert x['source_commit']==y['source_commit']==commit and not x['source_dirty'] and not y['source_dirty']
 assert tree(first/'RAID Admin.app')==tree(second/'RAID Admin.app')==x['files'];assert modes(first/'RAID Admin.app')==modes(second/'RAID Admin.app')==x['file_modes']
 runtime=first/'RAID Admin.app/Contents/PlugIns/Runtime.jdk';verify_runtime(runtime,lock['architectures'][arch]);verify_runtime(second/'RAID Admin.app/Contents/PlugIns/Runtime.jdk',lock['architectures'][arch])
 runtime_scopes[arch]={'Runtime.jdk files only':digest(tree(runtime)),'Runtime.jdk/Contents/Home files only':digest(tree(runtime/'Contents/Home')),'Runtime.jdk files and file_modes':digest({'files':tree(runtime),'file_modes':modes(runtime)})}
 assert runtime_scopes[arch]['Runtime.jdk files and file_modes']==lock['architectures'][arch]['tree_sha256']
 diagnostic=json.loads(Path('build/stopped-post-diagnostics-'+arch+'.json').read_text());assert diagnostic['source_commit']==commit and diagnostic['matches_build_manifest'] and diagnostic['matches_reviewed_artifact'] and diagnostic['event']['result']=='pass' and diagnostic['bundled_jre']['architecture']==arch and diagnostic['bundle_tree_sha256']==x['bundle_tree_sha256']
 bundles[arch]={'first':str(first),'second':str(second),'manifest':x,'second_manifest':y,'verification_output':Path('build/stopped-post-bundle-'+arch+'-2.stdout').read_text().splitlines()}
Path('build/stopped-post-bundle-results.json').write_text(json.dumps({'source_commit':commit,'source_dirty':False,'results':bundles,'controller_contact':False,'installed_application_modified':False,'action_scope_attestation':'Reviewed fixture/orchestration source and guarded gate results; no global packet-capture claim.'},indent=2)+'\n')
tests=json.loads(Path('build/stopped-post-clean-tests.json').read_text());assert tests['fixture_commit']==commit and not tests['fixture_dirty'] and tests['passed'] and tests['tests']==124
for n,h in tests['sources'].items():assert sha(ROOT/n)==h==hashlib.sha256(subprocess.check_output(['/usr/bin/git','show',commit+':'+n],env=isolated_env())).hexdigest();checked+=1
statuses={role:json.loads(Path('build/stopped-post-status-'+role+'.json').read_text()) for role in records}
assert all(row['exit']==0 and row['stderr_bytes']==0 for row in statuses.values())
runner={'source_commit':commit,'fixture_commit':commit,'source_dirty':False,'fixture_dirty':False,'gates':statuses,'gate_output_sha256':{role:sha(p) for role,p in records.items()},'bundle_statuses':{arch:json.loads(Path('build/stopped-post-status-bundle-'+arch+'.json').read_text()) for arch in ('aarch64','x64')},'python_tests':{'exit_code':tests['exit_code'],'passed':tests['passed'],'tests':tests['tests']}}
assert all(row['exit_code']==0 for rows in runner['bundle_statuses'].values() for row in rows)
Path('build/stopped-post-run-results.json').write_text(json.dumps(runner,indent=2)+'\n')
lock_results=json.loads(records['lock'].read_text());assert len(lock_results['observations'])==20 and sum(row['exact_deadlock_pair'] for row in lock_results['observations'])==10
supplemental={name:Path('build/'+name+'.json') for name in ('stopped-post-clean-tests','stopped-post-bundle-results','stopped-post-diagnostics-aarch64','stopped-post-diagnostics-x64','stopped-post-run-results')}
result={'source_commit':commit,'fixture_commit':commit,'source_dirty':False,'fixture_dirty':False,'historical_characterization_source_commit':char['source_commit'],'records':{n:sha(p) for n,p in records.items()},'record_files':{n:p.name for n,p in records.items()},'supplemental_records':{n:sha(p) for n,p in supplemental.items()},'candidate_jar_sha256':sha(jar),'original_jar_sha256':sha(original),'original_mode':oct(original.stat().st_mode&0o777),'installed_jar_sha256':sha(installed/'Contents/Resources/RAID_Admin.jar'),'installed_matches_reference_files_and_modes':True,'fixture_sources_match_committed_bytes':True,'checked_source_hash_entries':checked,'python_tests_passed':124,'connection_stop_records':42,'interpreted_compiled_connection_positives':36,'semantic_mutants_per_architecture':3,'historical_characterization_records':8,'changed_jar_entries_from_audit19':changed,'architectures':['aarch64','x64'],'x64_execution':'Rosetta, not physical Intel','controller_contact':False,'production_or_mounted_volume_tests':False,'installed_application_modified':False,'runtime_hash_scopes':runtime_scopes,'integrity_checker_scope':'record/source/byte/hash assertions; controller_contact, production_or_mounted_volume_tests and installed_application_modified are action-scope attestations from reviewed fixture sources/guarded results, not global packet capture'}
result['audit19_reference_jar_sha256']=sha(oldjar)
with zipfile.ZipFile(jar) as a,zipfile.ZipFile(oldjar) as b:
 result['changed_entry_sha256_from_audit19']={n:{'before':(hashlib.sha256(b.read(n)).hexdigest() if n in b.namelist() else None),'after':hashlib.sha256(a.read(n)).hexdigest()} for n in changed}
 assert a.read('META-INF/MANIFEST.MF')==b.read('META-INF/MANIFEST.MF')
 result['manifest_entry_unchanged_from_audit19']={'entry':'META-INF/MANIFEST.MF','byte_identical':True,'sha256':hashlib.sha256(a.read('META-INF/MANIFEST.MF')).hexdigest()}
assert sha(oldjar)==json.loads(Path('audit/stop-lock-final-integrity.json').read_text())['candidate_jar_sha256']
result['lock_observation_records']=20;result['exact_deadlock_controls']=10;result['interpreted_compiled_lock_positives']=8;result['site_attribution_cross_controls']=2
result['runtime_hash_scope_definitions']={'Runtime.jdk files only':'Fresh file-content-map digest excluding modes','Runtime.jdk/Contents/Home files only':'Fresh Home file-content-map digest excluding modes','Runtime.jdk files and file_modes':'Fresh digest({files: file-content map, file_modes: mode map}); matches exact vendor lock/gate/package digest; directory modes separately verified'}
admission=json.loads(records['admission'].read_text());assert len(admission['observations'])==40
for row in admission['observations']:
 assert row['manager_class_sha256']==(AUDIT19_MANAGER_SHA256 if row['variant']=='audit19-Manager-restored' else json.loads(Path('audit/security-patches.json').read_text())[entry]['patched_sha256'])
 if row['variant']=='candidate':assert row['jar_sha256']==sha(jar)
positive={(row['architecture'],row['execution'],row['scenario']) for row in admission['observations'] if row['variant']=='candidate'}
assert len(positive)==32 and positive=={(arch,execution,mode) for arch in ('aarch64','x64') for execution in ('-Xint','-Xcomp') for mode in ('async','sync','worker','concurrent','edt','null-clone','throwing','boundary')}
recovery=json.loads(records['runtime'].read_text());assert len(recovery['observations'])==2
assert all(len(row['recovery_regression'])==143 for row in recovery['observations']);assert {row['runtime_tree_sha256'] for row in recovery['observations']}=={runtime_scopes[arch]['Runtime.jdk/Contents/Home files only'] for arch in ('aarch64','x64')}
factory=json.loads(records['factory'].read_text());assert len(factory['observations'])==4 and all(row['rows']==116 and row['guarded_operations']==0 for row in factory['observations']);assert {(row['jar_sha256'],row['architecture']) for row in factory['observations']}=={(digest,arch) for digest in (sha(jar),sha(original)) for arch in ('aarch64','x64')}
for role in ('transport','shared'):
 assert {row['jar_sha256'] for row in json.loads(records[role].read_text())['observations']}=={sha(jar),sha(original)}
posting=json.loads(records['posting'].read_text());assert len(posting['observations'])==10
result['recovery_lines_per_architecture']=143;result['factory_rows_per_observation']=116;result['factory_differential_observations']=4;result['synchronous_posting_observation_records']=10
result['installed_intake_file_map_pinned']=True;result['installed_intake_file_map_digest']=digest(tree(installed));result['installed_reference_files_modes_digest']=digest({'files':tree(reference),'file_modes':modes(reference)});result['installed_reference_mode_scope']='Modes match preserved external reference; content independently pinned to tracked intake map. Initial reference modes were not separately hash-pinned in intake.'
result['action_scope_attestation']='No Main/native GUI/controller/production volume operations performed: reviewed fixture entrypoints plus OfflineGuard zero-denial assertions. Not independently established by packet capture.'
result['qualification_interpreter_attestation']={'path':sys.executable,'version':platform.python_version(),'implementation':platform.python_implementation(),'python_lock_sha256':sha(Path('audit/python-lock.json')),'measurement_phase':'Final ledger verification; each qualification entrypoint invokes verify_python, corrected bundle/test orchestration explicitly selects sys.executable. Path not separately captured at every gate start.'}

assert sum(row['variant']=='candidate' for row in admission['observations'])==32
assert sum(row['variant']=='audit19-Manager-restored' for row in admission['observations'])==4
assert sum(row['variant']=='helper-removed' for row in admission['observations'])==2
assert sum(row['variant']=='logging-containment-removed' for row in admission['observations'])==2
assert sum(row['variant']=='candidate' for row in lock_results['observations'])==8
assert sum(row['variant']!='candidate' and not row['exact_deadlock_pair'] for row in lock_results['observations'])==2
assert {(row['architecture'],row['variant'],row['scenario']) for row in lock_results['observations'] if row['variant']!='candidate' and not row['exact_deadlock_pair']}=={(arch,'pc45-getter-restored','pc18') for arch in ('aarch64','x64')}
assert sum('semantic_negative_control' not in row for row in connect['observations'])==36
assert all(sum(row['architecture']==arch and 'semantic_negative_control' in row for row in connect['observations'])==3 for arch in ('aarch64','x64'))
result['checked_source_hash_entries_definition']='Count of all asserted reported source-hash entries plus Python test source entries, including repeated files; not unique-file count.'
result['supplemental_record_scope']='Bundle/run results are this independent ledger checker summaries, hashes identify those summaries; diagnostics assertions verify their pass/source/architecture/artifact claims, not new behavior tests.'
result['admission_observation_records']=40;result['interpreted_compiled_admission_positives']=32;result['restored_audit19_stranding_controls']=4;result['missing_helper_controls']=2;result['logging_containment_bypass_controls']=2
result['excluded_runs']={'development':'Dirty drafts, initial pop opcode corrected to pop2, classallowlist correction, worker-identity fixture corrections, and sourceguard-rejected run excluded. Separate dirty dev-admission-4 run passed40 checks and is not clean acceptance; earlier expanded dev-admission-3 run was rejected on source changes.','initial_package_interpreter':'One initial orchestration attempt per architecture used python3 resolved by isolated PATH to an unpinned Python; rejected before package copy. Corrected to sys.executable pinned CPython3.14.8; no source change.','historical_audit19':'Earlier lock stdout mismatch remains unexplained; audit20 does not claim a cause or fix.'}
result['limits']='External stopped async callbacks deliberately run on EDT and can precede older drain/nonEDT return, show errors/model changes, or cause extension repost event loops. Disposed AppContext can drop events; scheduling/link errors propagate outside queue. Production logger emits only its existing limited ERROR signal. Constructor bypass, absent connection, headless EventQueue and arbitrary third-party callback limits are in admission record. Active send/shutdown races, interruption orphaning, abnormal unstopped worker exit, native GUI, physical Intel, production controller/volume behavior and signing/notarization remain unqualified.'
Path('build/stopped-post-final-integrity.json').write_text(json.dumps(result,indent=2)+'\n');print('Final integrity verified',sha(Path('build/stopped-post-final-integrity.json')))
