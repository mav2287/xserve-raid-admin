#!/usr/bin/env python3
"""Read-only recorded evidence and optional local ZIP check; never launches Java."""
import gzip,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def git(commit,name):return subprocess.check_output(['/usr/bin/git','show',commit+':'+name],cwd=ROOT,env={'PATH':'/usr/bin:/bin'})
r=json.loads((HERE/'receipt.json').read_bytes())
for n,h in r['files'].items():
 assert Path(n).name==n and sha((HERE/n).read_bytes())==h, 'Evidence differs: '+n
for log,v in r['jit_logs'].items():
 assert sha(gzip.decompress((HERE/v['archive']).read_bytes()))==v['raw_sha256'], 'JIT log differs'
for n in ['common-7-provenance.json','common-8-provenance.json','aarch64-provenance.json','x64-provenance.json']:
 p=json.loads((HERE/n).read_bytes());assert p['source_commit']==r['source_commit'] and not p['source_dirty']
 for name,h in p['input_hashes'].items():
  assert not Path(name).is_absolute() and '..' not in Path(name).parts
  assert sha(git(p['source_commit'],name))==h, 'Recorded source differs: '+name
for arch,v in r['archives'].items():
 assert Path(v['local_path']).parts[0]=='build' and '..' not in Path(v['local_path']).parts
 p=ROOT/v['local_path']
 if p.exists():assert sha(p.read_bytes())==v['sha256'], 'Local ZIP differs: '+arch
 else:print('Local ZIP absent; recorded checksum only: '+arch)
a=json.loads((HERE/'listener-results.json').read_bytes())
assert len(a['runs'])==8 and len(a['negatives'])==4 and a['whole_jar_inverse_exact'] and a['all_other_entries_unchanged']
print('PASS recorded audit29 evidence/source hashes; not native GUI or hardware qualification')
