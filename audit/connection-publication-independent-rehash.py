import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ledgers={
 'audit/connection-publication-final-integrity.json':'858b677798af63904a2ea0c87477761db7e2367224a7717519fe88b5675e942f',
 'audit/socket-configuration-final-integrity.json':'509f54f24919ac99ca0168508c1330410297d667fb000689f132f83954cc5137',
 'audit/stop-admission-final-integrity.json':'df1e0ea85687dcabc1248d0abb15dabeb14c67b5c1b62c6e10ea018d978aec57',
 'audit/worker-exit-final-integrity.json':'f53c325d0eadef855f1fdb777e6ebc2feab8d6d1588899738153280b003dfbb7'}
rows=[]
for name,expected in ledgers.items():
 p=ROOT/name
 if sha(p)!=expected:raise ValueError('Frozen ledger differs')
 d=json.loads(p.read_text());records=d.get('records',{})
 for relative,h in records.items():
  path=Path(relative)
  if path.is_absolute() or '..' in path.parts or sha(ROOT/path)!=h:raise ValueError('Bound record differs')
 rows.append({'ledger':name,'sha256':expected,'records_verified':len(records)})
env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','TZ':'UTC'}
commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=env,text=True).strip()
record={'purpose':'Independent separate-invocation byte rehash; no fixture/app/controller execution','execution_commit':commit,'execution_worktree_dirty':bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=env)),'script_sha256':sha(Path(__file__)),'ledgers':rows}
(ROOT/'build/connection-publication-independent-rehash.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS independent rehash; audit24/23/22/21 ledgers and all bound records')
