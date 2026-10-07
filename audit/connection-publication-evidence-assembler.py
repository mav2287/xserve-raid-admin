"""Validate and archive completed audit24 evidence; no app/controller execution."""
import hashlib,json,re,stat,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import sha,tree,modes,digest,isolated_env,verify_python
from verify_builds import check_artifact
from verify_bundles import check_bundle
from runtime import runtime_manifest
APP='8c246e188929522c5420a3a3b88aed79ec80bb8e';QA=APP
JAR='9592145c933f611888a00cb159340a86f99d427672483701212023078f823553'
ORIGINAL='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
def require(value,message):
 if not value:raise ValueError(message)
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
def checked_sources(record,commit):
 count=0
 for group in ('source_hashes','verifier_sources','fixture_sources','sources','harness_sources'):
  for name,value in record.get(group,{}).items():
   require(not Path(name).is_absolute() and '..' not in Path(name).parts and re.fullmatch('[0-9a-f]{64}',value),'Source hash shape differs')
   require(hashlib.sha256(git('show',commit+':'+name)).hexdigest()==value==sha(ROOT/name),'Committed source differs: '+name);count+=1
 return count
verify_python();require(git('rev-parse','HEAD').decode().strip()==QA,'Pinned QA source required')
require(not git('status','--porcelain'),'Clean assembly checkout required')
counts={'security':2,'transport':6,'runtime':2,'resources':8,'shared':4,'factory':4,'posting':10,'connect':46,'lock':20,'admission':40,'worker':120,'stop':104,'socket':4,'publication':8}
raw={};records={};checked=0
for key,count in counts.items():
 name=key
 path=ROOT/('build/connection-publication-clean-'+name+'.json');require(not path.with_suffix('.stderr').read_bytes(),'Gate stderr not empty: '+key)
 raw[key]=path.read_bytes();d=json.loads(raw[key]);records[key]=d
 require(d.get('fixture_commit',d.get('source_commit'))==QA and d.get('fixture_dirty',d.get('source_dirty')) is False,'Fixture source differs: '+key)
 require(len(d['observations'])==count,'Observation count differs: '+key)
 if 'qualification' in d:require(d['qualification'] is True,'Development record: '+key)
 for field in ('source_dirty','application_source_dirty'):
  if field in d:require(d[field] is False,'Dirty product: '+key)
 if 'candidate_sha256' in d:require(d['candidate_sha256']==('948c1d8587b43b7b004f193dd5d5eced4ffa8c6d7fd53943c029149f2245b28a' if key=='characterization' else JAR),'Candidate differs: '+key)
 for field in ('source_commit','application_source_commit'):
  if field in d:require(d[field]==('47166edbffb5bc07bc045d12fdf90b6b79d77f81' if key=='characterization' else APP),'Product source differs: '+key)
 checked+=checked_sources(d,d.get('fixture_commit',d.get('source_commit')))
 if 'tool_sha256' in d:
  name='tools/check_architectures.py' if key=='runtime' else 'tools/check_transport.py'
  require(d['tool_sha256']==sha(ROOT/name)==hashlib.sha256(git('show',d.get('fixture_commit',d.get('source_commit'))+':'+name)).hexdigest(),'Tool identity differs');checked+=1
 if key=='security':require(all(r[-1].startswith('PASS') for r in d['observations']),'Security outcomes differ')
 else:require({r.get('architecture') for r in d['observations']}=={'aarch64','x64'} if key!='runtime' else len(d['observations'])==2,'Architecture coverage differs: '+key)
 if 'runtime_trees' in d:require(d['runtime_trees']=={a:r['tree_sha256'] for a,r in runtime_manifest()['architectures'].items()},'Runtime lock differs')
first,m1=check_artifact(ROOT/'build/connection-publication-clean-1');second,m2=check_artifact(ROOT/'build/connection-publication-clean-2')
require(first==second==json.loads((ROOT/'audit/expected-build.json').read_text())['expected'],'Paired build differs')
require(m1['source_commit']==m2['source_commit']==APP and not m1['source_dirty'] and not m2['source_dirty'],'Paired source provenance differs')
jar=ROOT/'build/connection-publication-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar';require(sha(jar)==JAR,'Product JAR differs')
original=ROOT/'original/RAID_Admin_original.jar';require(sha(original)==ORIGINAL and stat.S_IMODE(original.stat().st_mode)==0o444,'Immutable reference differs')
with zipfile.ZipFile(jar) as z:entries={n:z.read(n) for n in z.namelist()}
reference=ROOT/'build/socket-configuration-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
require(sha(reference)=='2fccbee50eb868a04b415085511e0b52e6a13682543858d6f653b7f1f5fcadad','Audit23 reference differs')
with zipfile.ZipFile(reference) as z:old={n:z.read(n) for n in z.namelist()}
changed=sorted(n for n in entries.keys()|old.keys() if entries.get(n)!=old.get(n))
require(changed==['com/apple/xsr/net/AcpxConnection.class'],'Audit23 entry delta differs')
recovery=json.loads((ROOT/'audit/stopped-post-recovery-expected.json').read_text());require(recovery['candidate_jar_sha256']==JAR and len(recovery['lines'])==143,'Recovery golden differs')
expected=[s.replace('method=run;','method=dispatchLoop;').replace('queued=1; callback-drain-unqualified','queued=0; callbacks=2; terminal-drain') for s in recovery['lines']]
require(all(r['parity']=='PASS' and r['recovery_regression']==expected for r in records['runtime']['observations']),'Exact runtime recovery differs')
require({('x64' if 'architecture=x86_64' in r['api'] else 'aarch64' if 'architecture=aarch64' in r['api'] else 'unknown') for r in records['runtime']['observations']}=={'aarch64','x64'},'Runtime architecture observations differ')
stop=records['stop'];require(sum(bool(r['dispatch_compilation']) for r in stop['observations'])==52,'Installed dispatch coverage differs')
require(sum(r['scenario'].startswith('active:') and r['policy']=='guarded' for r in stop['observations'])==8,'Actual candidate active controls differ')
require(sum(r['scenario'].startswith('active:') and r['policy']=='legacy' for r in stop['observations'])==8,'Actual historical active controls differ')
for r in stop['observations']:
 require(r['lines'][-1].startswith('PASS'),'Stop result differs')
 if r['execution']=='-Xcomp':require(r['dispatch_compilation'] and all(n['method']=='com/apple/xsr/net/CommunicationsManager dispatchLoop ()V' for n in r['dispatch_compilation']),'Target compilation differs')
socket=records['socket'];require({(r['architecture'],r['execution_mode']) for r in socket['observations']}=={(a,e) for a in ('aarch64','x64') for e in ('-Xint','-Xcomp')},'Socket Cartesian coverage differs')
require(all(sum(x['cases'] for x in r['results'])==29 and all(x['result'].startswith('PASS') for x in r['results']) for r in socket['observations']),'Socket outcomes differ')
require(len(socket['negative_controls'])==24 and len({(r['mutation'],r['architecture']) for r in socket['negative_controls']})==24 and all(r['rejected_by_fixture_assertion'] and not r['verifier_or_timeout_failure'] for r in socket['negative_controls']),'Negative control coverage differs')
from socket_configuration_mutants import expected_frames,expected_assertions
require({(r['mutation'],r['architecture']) for r in socket['negative_controls']}=={(m,a) for m in expected_frames for a in ('aarch64','x64')},'Negative Cartesian coverage differs')
require(all(r['execution_mode']=='-Xint' and r['expected_failing_frames']==expected_frames[r['mutation']] and r['assertion']==expected_assertions[r['mutation']] for r in socket['negative_controls']),'Negative assertions/frames differ')
require(socket['product_class_hashes']=={n:hashlib.sha256(v).hexdigest() for n,v in entries.items() if n.endswith('.class') and (n.startswith('compat/') or n=='com/apple/xsr/net/HttpConnection.class')},'Socket class identity inventory differs')
publication=records['publication']
require(publication['candidate_source_commit']==APP and not publication['candidate_source_dirty'],'Publication product provenance differs')
require({(r['architecture'],r['execution_mode'],r['fixture']) for r in publication['observations']}=={(a,e,k) for a in ('aarch64','x64') for e in ('-Xint','-Xcomp') for k in ('ConnectionPublicationObservation','CachedConfigurationObservation')},'Publication matrix differs')
require(all(r['result'].startswith('PASS') and r['jar_sha256']==(JAR if r['fixture']=='ConnectionPublicationObservation' else publication['reference_sha256']) for r in publication['observations']),'Publication outcomes differ')
from check_connection_publication import FRAMES
require({(r['mutation'],r['architecture']) for r in publication['negative_controls']}=={(m,a) for m in FRAMES for a in ('aarch64','x64')} and len(publication['negative_controls'])==8,'Publication negatives differ')
require(all(r['expected_fixture_frames']==FRAMES[r['mutation']] and r['assertion']=='Publication assertion' and r['execution_mode']=='-Xint' and not r['verifier_or_timeout_failure'] for r in publication['negative_controls']),'Publication exact failure frames differ')
require(publication['candidate_acpx_sha256']==hashlib.sha256(entries['com/apple/xsr/net/AcpxConnection.class']).hexdigest(),'Acpx class identity differs')
require(sha(ROOT/'audit/socket-configuration-final-integrity.json')=='509f54f24919ac99ca0168508c1330410297d667fb000689f132f83954cc5137','Frozen audit23 ledger differs')
unit_path=ROOT/'build/connection-publication-reviewed-tests-run.json';unit_raw=unit_path.read_bytes();unit=json.loads(unit_raw)
require(unit['execution_commit']==QA and unit['execution_worktree_status']==[] and unit['returncode']==0 and unit['tests_passed']==146,'Unit execution provenance differs')
require(all(hashlib.sha256(git('show',QA+':'+n)).hexdigest()==h==sha(ROOT/n) for n,h in unit['source_hashes'].items()),'Unit source input differs')
require(unit['stdout_sha256']==sha(ROOT/'build/connection-publication-reviewed-tests.stdout') and unit['stderr_sha256']==sha(ROOT/'build/connection-publication-reviewed-tests.stderr'),'Unit output binding differs')
require(not (ROOT/'build/connection-publication-reviewed-tests.stdout').read_bytes() and re.fullmatch(rb'\.{146}\n-+\nRan 146 tests in [0-9.]+s\n\nOK\n',(ROOT/'build/connection-publication-reviewed-tests.stderr').read_bytes()),'Complete unit result differs')
require(unit['runner_sha256']==sha(ROOT/'build/connection-publication-unit-runner.py'),'Unit runner binding differs')
packages={};diagnostics={}
for arch in ('aarch64','x64'):
 a=ROOT/('build/connection-publication-bundled-'+arch+'-1');b=ROOT/('build/connection-publication-bundled-'+arch+'-2')
 require(check_bundle(a,ROOT/'build/connection-publication-clean-1')==check_bundle(b,ROOT/'build/connection-publication-clean-2'),'Repeated package bytes/modes differ')
 ma=json.loads((a/'provenance.json').read_text());mb=json.loads((b/'provenance.json').read_text())
 require(ma['source_commit']==mb['source_commit']==APP and not ma['source_dirty'] and not mb['source_dirty'] and ma['packager_commit']==mb['packager_commit']==APP and not ma['packager_dirty'] and not mb['packager_dirty'],'Package source differs')
 packages[arch]={'bundle_tree_sha256':ma['bundle_tree_sha256'],'source_commit':APP,'packager_commit':APP,'vendor_signature_verification':ma['bundled_runtime']['signature_verification'],'application_signing':ma['application_signing'],'application_notarization':ma['application_notarization']}
 dp=ROOT/('build/connection-publication-diagnostics-'+arch+'.json');d=json.loads(dp.read_bytes())
 require(d['compatibility_version']=='1.5.1-modern.audit.24' and d['source_commit']==APP and all(d[k] for k in ('matches_build_manifest','matches_reviewed_artifact','compatibility_version_matches_reviewed_artifact')) and d['bundled_jre']['architecture']==arch and d['bundle_tree_sha256']==ma['bundle_tree_sha256'],'Metadata-only diagnostics differ')
 require(d['controller_discovery']=='not run; no controller traffic generated' and d['runtime_selected']=='not evaluated; application not launched','Diagnostic operation scope differs');diagnostics[arch]=d
installed=Path('/Applications/RAID Admin.app');intake=json.loads((ROOT/'audit/intake-provenance.json').read_text())
require(tree(installed)==intake['bundle_file_hashes']['installed'],'Installed intake differs')
require(not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==QA,'Assembly source changed')
require(sum(not n.endswith('/') for n in entries)==3062,'SBOM entry count differs')
# Write only new audit24 records after every assertion above succeeds.
files={}
def archive(name,value):
 path=ROOT/('audit/connection-publication-'+name)
 require(not path.exists(),'Refusing to overwrite audit evidence')
 path.write_bytes(value);files[str(path.relative_to(ROOT))]=sha(path)
for key,value in raw.items():archive('clean-'+key+'.json',value)
archive('clean-tests.json',unit_raw)
for channel in ('stdout','stderr'):archive('clean-tests.'+channel,(ROOT/('build/connection-publication-reviewed-tests.'+channel)).read_bytes())
archive('unit-runner.py',(ROOT/'build/connection-publication-unit-runner.py').read_bytes())
sbom={'format':'project inventory schema 1, not asserted SPDX/CycloneDX conformant','jar_sha256':JAR,'application_source_commit':APP,'third_party_dependencies_added':[],'files':{n:hashlib.sha256(v).hexdigest() for n,v in entries.items() if not n.endswith('/')},'runtime_inventory':'runtime-lock.json'}
require(len(sbom['files'])==3062,'SBOM entry count differs');archive('sbom.json',(json.dumps(sbom,indent=2,sort_keys=True)+'\n').encode())
archive('clean-packages.json',(json.dumps(packages,indent=2,sort_keys=True)+'\n').encode())
for arch,d in diagnostics.items():archive('clean-diagnostics-'+arch+'.json',(json.dumps(d,indent=2,sort_keys=True)+'\n').encode())
archive('evidence-assembler.py',Path(__file__).read_bytes())
ledger={'application_source_commit':APP,'fixture_commits':{k:d.get('fixture_commit',d.get('source_commit')) for k,d in records.items()},'qa_source_commit':QA,'candidate_version':'1.5.1-modern.audit.24','candidate_jar_sha256':JAR,'original_jar_sha256':ORIGINAL,'original_mode':'0444','changed_entries_from_audit23':changed,'gate_observation_counts':counts,'socket_cases_per_runtime_mode':29,'socket_negative_controls':24,'publication_cases_per_candidate_runtime_mode':26,'publication_failed_send_attempts_per_candidate_runtime_mode':34,'publication_negative_controls':8,'publication_reference_observations':4,'python_tests_passed':146,'checked_gate_source_hash_entries':checked,'records':files,'packages':packages,'historical_audit23_ledger_sha256':sha(ROOT/'audit/socket-configuration-final-integrity.json'),'historical_audit22_ledger_sha256':sha(ROOT/'audit/stop-admission-final-integrity.json'),'historical_default_fixture_hashes':stop['historical_default_fixture_hashes'],'installed_jar_sha256':sha(installed/'Contents/Resources/RAID_Admin.jar'),'installed_intake_map_digest':digest(intake['bundle_file_hashes']['installed']),'controller_contact':False,'installed_application_modified':False,'production_or_mounted_volume_tests':False,'action_scope_attestation':'Tool/agent history plus guards; not packet or hardware evidence. Qualification gates are headless; separate unqualified offscreen UI development probes shown no windows, with no app Main/profile/controller access.','source_cleanliness_scope':'Product, fixture, unit and package executions clean at recorded commits. Assembly began on clean pinned QA source; only new audit24 archival records written afterward. Generator/runner bytes bound by SHA, committed in subsequent evidence commit.','excluded_runs':['All development/dirty-source prototypes and earlier unit runs before golden roll-forward; those are not clean qualification.','Separate native-boundary/offscreen-component development probes are not part of these fourteen headless gates.'],'limits':'x64 uses Rosetta, not physical Intel. Memory fixture execution is not controller, native socket, UI, discovery, firmware or release acceptance. Original DNS/TCP connection timing retained; DNS/write/whole-operation bounds, live timeout setter and direct post-newRequest failure recovery, outbound mutability and status/empty-ack interpretation remain open. HTTP plaintext. Original JAR and installed app unchanged.'}
archive('final-integrity.json',(json.dumps(ledger,indent=2,sort_keys=True)+'\n').encode())
require(all(sha(ROOT/n)==h for n,h in files.items()),'Archive bytes changed')
print('PASS audit24 evidence assembly; '+str(checked)+' source-map entries; ledger '+sha(ROOT/'audit/connection-publication-final-integrity.json'))
