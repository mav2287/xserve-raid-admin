import concurrent.futures,hashlib,json,re,shlex,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import isolated_env
commands=json.loads((ROOT/'build/help-gate-commands.json').read_text())
rows=[]
def run(name):
    r=subprocess.run(shlex.split(commands[name]),cwd=ROOT,env=isolated_env(),capture_output=True,timeout=900)
    row={'gate':name,'returncode':r.returncode,'stdout_bytes':len(r.stdout),'stderr_bytes':len(r.stderr),'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'argv':shlex.split(commands[name])}
    if r.returncode==0 and not r.stderr:
        try:data=json.loads(r.stdout)
        except ValueError:row['accepted']=False
        else:
            row['accepted']=True
            with (ROOT/('build/help-clean-'+name+'.json')).open('xb') as out:out.write(r.stdout)
    else:row['accepted']=False
    if not row['accepted']:
        row['safe_python_frames']=re.findall(r'File "[^"]*/((?:tools|audit)/[A-Za-z0-9_./-]+\.py)", line (\d+)',r.stderr.decode('utf8',errors='replace'))
    print('gate='+name+'; accepted='+str(row['accepted']).lower(),flush=True);return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,name) for name in commands if name!='lock']
    for future in concurrent.futures.as_completed(futures):rows.append(future.result())
rows.append(run('lock'))
(ROOT/'build/help-gate-run-summary.json').write_text(json.dumps(rows,sort_keys=True,indent=2)+'\n')
if not all(row['accepted'] for row in rows):raise SystemExit('Gate failure; raw output withheld')
print('PASS 14 clean candidate regression gates')
