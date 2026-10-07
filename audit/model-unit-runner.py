"""Clean, commit-bound full unit execution; no application startup or controller."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import isolated_env,sha,verify_python
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);a=p.parse_args();verify_python()
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
def require(value):
    if not value:raise ValueError('Clean unit qualification failed; output withheld')
require(git('rev-parse','HEAD').decode().strip()==a.commit and not git('status','--porcelain'))
inputs={str(f.relative_to(ROOT)):sha(f) for folder in ('tools','tests') for f in (ROOT/folder).rglob('*.py')}
require(all(hashlib.sha256(git('show',a.commit+':'+name)).hexdigest()==h for name,h in inputs.items()))
command=[sys.executable,'-E','-s','-m','unittest','discover','-s','tests'];r=subprocess.run(command,cwd=ROOT,env=isolated_env(),capture_output=True,timeout=300)
require(r.returncode==0 and not r.stdout and re.fullmatch(rb'\.{170}\n-+\nRan 170 tests in [0-9.]+s\n\nOK\n',r.stderr))
require(not git('status','--porcelain') and all(sha(ROOT/name)==h for name,h in inputs.items()))
for channel,value in [('stdout',r.stdout),('stderr',r.stderr)]:
    with (ROOT/('build/model-clean-unit.'+channel)).open('xb') as out:out.write(value)
record={'scope':'Clean full unit qualification; no native app/controller acceptance','execution_commit':a.commit,'execution_dirty':False,'tests_passed':170,'command':command,'sources':inputs,'runner_sha256':sha(Path(__file__)),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()}
with (ROOT/'build/model-clean-unit.json').open('x') as out:out.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print('PASS 170 unit tests from pinned clean commit')
