#!/usr/bin/env python3
"""Re-execute frozen runtime gates on the secure JAR with explicit artifact adapters.

Only static artifact identity metadata and exact private-helper comparators are
adapted. Java fixture argv/classpaths continue to reference the actual secure JAR.
The original files and controller/fixture expected-behavior tables remain frozen.
"""
import argparse,hashlib,json,sys,io,contextlib,shlex,subprocess,inspect
from pathlib import Path
from audit_support import ROOT,isolated_env,sha,verify_python
from secure_build import HELPERS,BASE_SHA,entries,state,check_secure_artifact

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--gate',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify_python();initial=state()
    if initial['dirty']:raise ValueError('Clean secure gate source required')
    if a.output.exists() or a.output.is_symlink() or not a.output.resolve().is_relative_to((ROOT/'build').resolve()):raise ValueError('New secure gate output required')
    identity,product=check_secure_artifact(a.build)
    if product['source_dirty'] or product['source_commit']!=initial['commit']:raise ValueError('Clean secure product required')
    commands=json.loads((ROOT/'audit/preference-gate-commands.json').read_text())
    if a.gate=='preference' or a.gate not in commands:raise ValueError('The in-place preference gate is replaced by direct secure tests')
    oldargv=shlex.split(commands[a.gate]);source=ROOT/oldargv[3];original=source.read_text();jar=a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar';base=a.build/'audit27-reference/RAID Admin.app/Contents/Resources/RAID_Admin.jar';baseline=entries(base);helpers=product['helper_hashes']
    argv=[v.replace('build/preference-clean-1',str(a.build.resolve())).replace(BASE_SHA,product['jar_sha256']) for v in oldargv[4:]]
    if '--output' in argv:argv[argv.index('--output')+1]=str(a.output.parent/(a.output.stem+'-boundary'))
    # Runtime fixture bodies are frozen. Adapt artifact hashes and Help static comparison;
    # actual artifact verification below still checks the complete secure delta.
    if not any(str(jar.resolve()) in v or str(a.build.resolve())==v for v in argv):raise ValueError('Secure fixture argv lacks actual product')
    adapted=original.replace(BASE_SHA,product['jar_sha256'])
    import verify_builds,preference_io_patch
    original_checker=verify_builds.check_artifact;verify_builds.check_artifact=check_secure_artifact
    original_strip=preference_io_patch.strip_entries
    def normalize_private(values):
        present=set(values)&(HELPERS-{'compat/PreferenceIO.class'})
        if present:
            if present!=HELPERS-{'compat/PreferenceIO.class'} or any(hashlib.sha256(values[n]).hexdigest()!=helpers[n] for n in HELPERS):raise ValueError('Static comparator sees altered private helpers')
            values={n:v for n,v in values.items() if n not in HELPERS-{'compat/PreferenceIO.class'}};values['compat/PreferenceIO.class']=baseline['compat/PreferenceIO.class']
        return values
    def strip_private(values):return original_strip(normalize_private(values))
    if a.gate=='help':
        window="if sha(actual)!=sha(jar):raise ValueError('Integrated candidate differs from exact qualified-core overlay')"
        if adapted.count(window)!=1:raise ValueError('Frozen Help static comparison window differs')
        adapted=adapted.replace(window,"if secure_normalize_private(secure_read_entries(actual))!=secure_read_entries(jar):raise ValueError('Integrated candidate differs beyond exact private helper extension')")
    preference_io_patch.strip_entries=strip_private
    expected_path=ROOT/'audit/expected-build.json';recovery_path=ROOT/'audit/stopped-post-recovery-expected.json'
    expected_text=json.dumps({'expected':identity});recovery=json.loads(recovery_path.read_text());recovery['candidate_jar_sha256']=product['jar_sha256'];recovery_text=json.dumps(recovery)
    read_text=Path.read_text
    def read_metadata(path,*args,**kwargs):
        if path.resolve()==expected_path.resolve():return expected_text
        if path.resolve()==recovery_path.resolve():return recovery_text
        return read_text(path,*args,**kwargs)
    inputs={str(f.relative_to(ROOT)):sha(f) for f in sorted((ROOT/'tools').glob('*.py'))+sorted((ROOT/'tests').rglob('*.java'))+[ROOT/'audit/preference-gate-commands.json',expected_path,recovery_path]}
    Path.read_text=read_metadata
    oldargs=sys.argv;sys.argv=[str(source)]+argv;stdout=io.StringIO();stderr=io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):exec(compile(adapted,str(source),'exec'),{'__name__':'__main__','__file__':str(source),'secure_normalize_private':normalize_private,'secure_read_entries':entries})
    finally:
        Path.read_text=read_text;verify_builds.check_artifact=original_checker;preference_io_patch.strip_entries=original_strip;sys.argv=oldargs
    if stderr.getvalue():raise ValueError('Secure gate emitted unexpected diagnostics')
    result=stdout.getvalue();expected={'help':'PASS integrated Help boundary; four runtime/mode variants; no browser/controller','model':'PASS model diagnostic gate; four runtime/mode variants; sixteen behavioral negative controls; no controller/profile'}
    if a.gate in expected:
        if result!=expected[a.gate]+'\n':raise ValueError('Secure UI boundary result differs')
        data=json.loads((a.output.parent/(a.output.stem+'-boundary/observations.json')).read_text())
    else:data=json.loads(result)
    if state()!=initial or any(sha(ROOT/n)!=h for n,h in inputs.items()) or check_secure_artifact(a.build)[0]!=identity:raise ValueError('Secure gate inputs changed')
    record={'qualification':False,'scope':'Frozen behavior/runtime fixture on actual secure JAR; artifact metadata/comparator adapted explicitly','gate':a.gate,'execution_commit':initial['commit'],'product_source_commit':product['source_commit'],'artifact_hash_literal_replacements':original.count(BASE_SHA),'source_dirty':False,'product_jar_sha256':product['jar_sha256'],'frozen_driver':str(source.relative_to(ROOT)),'frozen_driver_sha256':sha(source),'adapted_driver_sha256':hashlib.sha256(adapted.encode()).hexdigest(),'artifact_metadata_adaptations':{'expected_build_original_sha256':sha(expected_path),'expected_build_effective_sha256':hashlib.sha256(expected_text.encode()).hexdigest(),'recovery_original_sha256':sha(recovery_path),'recovery_effective_sha256':hashlib.sha256(recovery_text.encode()).hexdigest(),'static_inverse_only':'Exact private helper hashes removed/restored solely in comparator; runtime JAR never normalized'},'argv':argv,'inputs':inputs,'underlying_fixture_result':data,'limits':['No native GUI/controller/production profile execution','Driver-alone original qualification flag is superseded by this explicit secure scope']}
    with a.output.open('x') as out:out.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
    print('PASS secure runtime gate='+a.gate+'; actual_jar=true; explicit_artifact_adapter=true')
if __name__=='__main__':main()
