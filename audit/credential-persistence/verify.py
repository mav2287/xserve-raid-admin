#!/usr/bin/env python3
"""Read-only verification of additive boundary records and their actual Git inputs."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def member(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts: raise ValueError('Invalid evidence member')
    return ROOT / path
ledger = json.loads((ROOT / 'audit/credential-persistence/integrity.json').read_bytes())
if sha(ROOT/'audit/secure-release/final-integrity.json') != ledger['frozen_audit28_ledger_sha256']: raise ValueError('Frozen release ledger changed')
if sha(ROOT/'audit/secure-release/verify.txt') != ledger['frozen_verifier_sha256']: raise ValueError('Frozen verifier changed')
directory=ROOT/'audit/credential-persistence'
listed={Path(name).name for name in ledger['records'] if Path(name).parent == Path('audit/credential-persistence')}
if {p.name for p in directory.iterdir()} != listed | {'integrity.json'} or any(p.is_symlink() or not p.is_file() for p in directory.iterdir()): raise ValueError('Unexpected boundary archive contents')
for name, digest in ledger['records'].items():
    if sha(member(name)) != digest: raise ValueError('Boundary record changed: ' + name)
env = {'PATH':'/usr/bin:/bin', 'HOME':'/var/empty', 'GIT_CONFIG_NOSYSTEM':'1', 'GIT_CONFIG_GLOBAL':'/dev/null'}
expected=set()
for name in ['observations.json','observations-27bb482.json']:
    record=json.loads((directory/name).read_bytes())
    expected.update((record['fixture_commit'],path,digest) for path,digest in record['inputs'].items())
actual={(p['commit'],p['path'],p['sha256']) for p in ledger['source_proofs']}
if len(ledger['source_proofs']) != 20 or len(actual) != 20 or actual != expected: raise ValueError('Fixture proof set incomplete')
for proof in ledger['source_proofs']:
    data = subprocess.check_output(['/usr/bin/git','show',proof['commit']+':'+proof['path']], cwd=ROOT, env=env)
    if hashlib.sha256(data).hexdigest() != proof['sha256']: raise ValueError('Fixture Git proof changed')
observations = json.loads((ROOT / 'audit/credential-persistence/observations.json').read_bytes())
if observations['fixture_commit'] != ledger['fixture_commit'] or len(observations['runs']) != 4: raise ValueError('Boundary attribution differs')
if any(not row['wrong_getter_negative_detected'] or not row['current_wrong_getter_negative_detected'] or not row['empty_stderr'] for row in observations['runs']): raise ValueError('Boundary run incomplete')
subprocess.run([sys.executable,'-I','-S',str(ROOT/'audit/secure-release/verify.txt')], cwd=ROOT, env=env, check=True)
print('PASS additive credential boundary records and Git input proofs; frozen audit28 remains intact; no Java execution')
