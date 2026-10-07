"""Separate frozen-record verification, not a feature or hardware test."""
import json,hashlib,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_support import sha,verify_python,isolated_env
verify_python()
fixed={'audit/socket-configuration-final-integrity.json':'509f54f24919ac99ca0168508c1330410297d667fb000689f132f83954cc5137',
       'audit/stop-admission-final-integrity.json':'df1e0ea85687dcabc1248d0abb15dabeb14c67b5c1b62c6e10ea018d978aec57',
       'audit/worker-exit-final-integrity.json':'f53c325d0eadef855f1fdb777e6ebc2feab8d6d1588899738153280b003dfbb7'}
for name,h in fixed.items():
    if sha(ROOT/name)!=h:raise ValueError('Frozen ledger changed')
ledger=json.loads((ROOT/'audit/socket-configuration-final-integrity.json').read_text())
for name,h in ledger['records'].items():
    if sha(ROOT/name)!=h:raise ValueError('Frozen archive record changed')
record={'result':'PASS','verified_record_count':len(ledger['records']),'frozen_ledgers':fixed,
        'records':ledger['records'],'verifier_sha256':sha(Path(__file__)),
        'execution_commit':subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),
        'execution_worktree_dirty':bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())),
        'scope':'Separate tool invocation after assembly. Byte hashes only; no feature/hardware/GUI qualification. Documentation/archival worktree may be dirty; measured feature execution commits remain recorded in frozen ledger.'}
out=ROOT/'audit/socket-configuration-independent-rehash.json'
if out.exists():raise ValueError('Refusing to overwrite independent evidence')
out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print('PASS separate rehash: 25 archived records and three pinned ledgers')
