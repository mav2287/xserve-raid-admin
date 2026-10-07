"""Pinned, offline unit execution and archival outputs; never launches the app."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_support import isolated_env,sha,verify_python
QA='8c246e188929522c5420a3a3b88aed79ec80bb8e'
def git(*args):
    return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
def require(value,message):
    if not value:raise ValueError(message)
verify_python()
require(git('rev-parse','HEAD').decode().strip()==QA, 'Pinned unit execution check failed')
status=git('status','--porcelain').decode().splitlines()
require(status==[], 'Pinned unit execution check failed')
inputs={str(p.relative_to(ROOT)):sha(p) for folder in ('tools','tests') for p in (ROOT/folder).rglob('*.py')}
require(all(hashlib.sha256(git('show',QA+':'+name)).hexdigest()==value for name,value in inputs.items()), 'Pinned unit execution check failed')
command=[sys.executable,'-E','-s','-m','unittest','discover','-s','tests']
result=subprocess.run(command,cwd=ROOT,env=isolated_env(),capture_output=True)
require(result.returncode==0 and re.fullmatch(rb'\.{146}\n-+\nRan 146 tests in [0-9.]+s\n\nOK\n',result.stderr), 'Pinned unit execution check failed')
require(not result.stdout, 'Pinned unit execution check failed')
require(status==git('status','--porcelain').decode().splitlines() and all(sha(ROOT/name)==value for name,value in inputs.items()), 'Pinned unit execution check failed')
for channel,value in (('stdout',result.stdout),('stderr',result.stderr)):
    (ROOT/('build/connection-publication-reviewed-tests.'+channel)).write_bytes(value)
run={'command':command,'returncode':result.returncode,'tests_passed':146,'execution_commit':QA,'execution_worktree_status':status,'source_hashes':inputs,'stdout_sha256':sha(ROOT/'build/connection-publication-reviewed-tests.stdout'),'stderr_sha256':sha(ROOT/'build/connection-publication-reviewed-tests.stderr'),'runner':'build/connection-publication-unit-runner.py','runner_sha256':sha(Path(__file__)),'scope':'All test/tool inputs match pinned QA commit; clean source state recorded; runner and complete outputs archived by hash'}
(ROOT/'build/connection-publication-reviewed-tests-run.json').write_text(json.dumps(run,indent=2)+'\n')
print('PASS pinned unit runner; 146 tests; complete outputs archived')
