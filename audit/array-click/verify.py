#!/usr/bin/env python3
"""Read-only audit30 record/Git/optional ZIP verification; never runs Java."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def check(value,why):
    if not value:raise ValueError(why)
r=json.loads((HERE/'receipt.json').read_bytes())
for name,h in r['files'].items():
    check(Path(name).name==name and sha((HERE/name).read_bytes())==h,'Evidence differs: '+name)
for name in ['common-3-provenance.json','common-4-provenance.json','aarch64-provenance.json','x64-provenance.json']:
    p=json.loads((HERE/name).read_bytes());check(p['source_commit']==r['source_commit'] and not p['source_dirty'],'Source state differs')
    for n,h in p['input_hashes'].items():
        check(not Path(n).is_absolute() and '..' not in Path(n).parts,'Unsafe source path')
        raw=subprocess.check_output(['/usr/bin/git','show',p['source_commit']+':'+n],cwd=ROOT,env={'PATH':'/usr/bin:/bin'})
        check(sha(raw)==h,'Recorded Git source differs: '+n)
check(sha((ROOT/'original/RAID_Admin_original.jar').read_bytes())==r['original_jar_sha256'],'Apple reference differs')
t=json.loads((HERE/'listener-results.json').read_bytes());check(t['fixture_commit']==r['source_commit'] and len(t['runs'])==4,'Fixture state differs')
for n,h in t['inputs'].items():
    check(not Path(n).is_absolute() and '..' not in Path(n).parts,'Unsafe fixture path')
    raw=subprocess.check_output(['/usr/bin/git','show',t['fixture_commit']+':'+n],cwd=ROOT,env={'PATH':'/usr/bin:/bin'})
    check(sha(raw)==h,'Fixture Git source differs')
for arch in ['aarch64','x64']:
    before,after=[x for x in t['runs'] if x['arch']==arch]
    check(before['trace']==after['trace'] and after['jar_sha256']==r['jar_sha256'] and before['jar_sha256']==r['reference_jar_sha256'],'Fixture parity/artifact differs')
    v=r['archives'][arch];path=Path(v['local_path']);check(path.parts[0]=='build' and '..' not in path.parts,'Unsafe archive path')
    if (ROOT/path).exists():check(sha((ROOT/path).read_bytes())==v['sha256'],'ZIP differs: '+arch)
    else:print('Local ZIP absent; recorded checksum only: '+arch)
print('PASS audit30 record/Git/reference/available ZIP hashes; no native or hardware acceptance')
