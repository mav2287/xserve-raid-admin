"""Pinned, offline unit execution and archival outputs; never launches the app."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_support import isolated_env,sha,verify_python
QA='73ffa4efbfbab852c7d6990f5087d180b53751bb'
def git(*args):
    return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
verify_python()
assert git('rev-parse','HEAD').decode().strip()==QA
status=git('status','--porcelain').decode().splitlines()
assert all(s.startswith('?? audit/stop-admission-') for s in status)
inputs={str(p.relative_to(ROOT)):sha(p) for folder in ('tools','tests') for p in (ROOT/folder).rglob('*.py')}
assert all(hashlib.sha256(git('show',QA+':'+name)).hexdigest()==value for name,value in inputs.items())
command=[sys.executable,'-E','-s','-m','unittest','discover','-s','tests']
result=subprocess.run(command,cwd=ROOT,env=isolated_env(),capture_output=True)
assert result.returncode==0 and re.fullmatch(rb'\.{137}\n-+\nRan 137 tests in [0-9.]+s\n\nOK\n',result.stderr)
assert not result.stdout
assert status==git('status','--porcelain').decode().splitlines() and all(sha(ROOT/name)==value for name,value in inputs.items())
for channel,value in (('stdout',result.stdout),('stderr',result.stderr)):
    (ROOT/('build/stop-admission-reviewed-tests.'+channel)).write_bytes(value)
    (ROOT/('audit/stop-admission-clean-tests.'+channel)).write_bytes(value)
run={'command':command,'returncode':result.returncode,'tests_passed':137,'execution_commit':QA,'execution_worktree_status':status,'source_hashes':inputs,'stdout_sha256':sha(ROOT/'audit/stop-admission-clean-tests.stdout'),'stderr_sha256':sha(ROOT/'audit/stop-admission-clean-tests.stderr'),'runner':'audit/stop-admission-unit-runner.py','runner_sha256':sha(Path(__file__)),'scope':'All test/tool inputs match pinned QA commit; exact archival-only status recorded; runner and complete outputs archived by hash'}
(ROOT/'build/stop-admission-reviewed-tests-run.json').write_text(json.dumps(run,indent=2)+'\n')
print('PASS pinned unit runner; 137 tests; complete outputs archived')
