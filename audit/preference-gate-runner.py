"""Clean commit-bound candidate gates; lock stress runs after the other fixtures."""
import concurrent.futures,hashlib,json,re,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import isolated_env,sha,verify_python
verify_python()
def git(*args):return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,env=isolated_env())
initial=git('rev-parse','HEAD').decode().strip()
if git('status','--porcelain'):raise ValueError('Clean gate source required')
source_files=[Path(__file__),ROOT/'audit/preference-gate-commands.json',ROOT/'tools/audit_support.py',ROOT/'audit/python-lock.json']
sources={str(p.relative_to(ROOT)):sha(p) for p in source_files}
if any(hashlib.sha256(git('show',initial+':'+name)).hexdigest()!=h for name,h in sources.items()):raise ValueError('Gate runner source differs from commit')
commands=json.loads((ROOT/'audit/preference-gate-commands.json').read_text())
EXPECTED={'preference':'PASS preference IO gate; runs=8; cases=18; original_controls=8; negative_controls=16; units=5','help':'PASS integrated Help boundary; four runtime/mode variants; no browser/controller','model':'PASS model diagnostic gate; four runtime/mode variants; sixteen behavioral negative controls; no controller/profile'}
def run(name):
    argv=shlex.split(commands[name]);r=subprocess.run(argv,cwd=ROOT,env=isolated_env(),capture_output=True,timeout=900)
    row={'gate':name,'argv':argv,'returncode':r.returncode,'stdout_bytes':len(r.stdout),'stderr_bytes':len(r.stderr),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'accepted':False}
    if r.returncode==0 and not r.stderr:
        if name in EXPECTED:
            row['accepted']=r.stdout==((EXPECTED[name]+'\n').encode())
            row['record']='build/preference-clean-'+name+'-boundary/observations.json'
            if row['accepted']:row['record_sha256']=sha(ROOT/row['record'])
        else:
            try:data=json.loads(r.stdout)
            except ValueError:pass
            else:
                row['accepted']=True;row['record']='build/preference-clean-'+name+'.json'
                with (ROOT/row['record']).open('xb') as out:out.write(r.stdout)
                row['record_sha256']=sha(ROOT/row['record'])
    if not row['accepted']:row['safe_python_frames']=re.findall(r'File "[^\n"]*/((?:tools|audit)/[A-Za-z0-9_./-]+\.py)", line (\d+)',r.stderr.decode('utf8',errors='replace'))
    print('gate='+name+'; accepted='+str(row['accepted']).lower(),flush=True);return row
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,name) for name in commands if name!='lock']
    for future in concurrent.futures.as_completed(futures):rows.append(future.result())
rows.append(run('lock'))
if git('rev-parse','HEAD').decode().strip()!=initial or git('status','--porcelain') or sources!={str(p.relative_to(ROOT)):sha(p) for p in source_files}:raise ValueError('Gate source changed')
record={'execution_commit':initial,'execution_dirty':False,'sources':sources,'rows':sorted(rows,key=lambda r:r['gate']),'scope':'Seventeen local candidate gates; no Main/controller/production-volume acceptance'}
with (ROOT/'build/preference-gate-run-summary.json').open('x') as out:out.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
if len(rows)!=17 or not all(row['accepted'] for row in rows):raise SystemExit('Gate failure; raw output withheld')
print('PASS seventeen clean candidate gates')
