#!/usr/bin/env python3
"""Re-run preserved audit27 and secure candidate fixture matrices; no application launch."""
import argparse,json,shlex,subprocess,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_support import ROOT,sha,isolated_env,verify_python
from secure_build import check_secure_artifact,state,BASE_SHA

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify_python();initial=state()
 if initial['dirty'] or a.output.exists() or not a.output.resolve().is_relative_to((ROOT/'build').resolve()):raise ValueError('Clean source and new qualification output required')
 identity,product=check_secure_artifact(a.build)
 if product['source_dirty']:raise ValueError('Clean candidate build required')
 a.output.mkdir();commands=json.loads((ROOT/'audit/preference-gate-commands.json').read_text());rows=[]
 if len(commands)!=17 or 'preference' not in commands:raise ValueError('Frozen gate inventory differs')
 for name,old in commands.items():
  argv=shlex.split(old);argv=[v.replace('build/preference-clean-1',str((a.build/'audit27-reference').resolve())) for v in argv]
  if '--output' in argv:argv[argv.index('--output')+1]=str(a.output/('audit27-'+name+'-boundary'))
  result=subprocess.run(argv,cwd=ROOT,env=isolated_env(),capture_output=True,timeout=1200)
  if result.returncode or result.stderr:raise RuntimeError('Rebuilt audit27 gate failed: '+name+'; raw diagnostics withheld')
  try:data=json.loads(result.stdout)
  except ValueError:
   if not result.stdout.startswith(b'PASS '):raise ValueError('Non-JSON gate result differs')
   data={'stdout':result.stdout.decode().strip(),'boundary_record_sha256':sha(Path(argv[argv.index('--output')+1])/'observations.json')}
  record={'gate':name,'scope':'Frozen fixture on freshly rebuilt audit27; no hardware/GUI qualification','source_commit':initial['commit'],'source_dirty':False,'candidate_jar_sha256':BASE_SHA,'argv':argv,'result':data}
  path=a.output/('audit27-'+name+'.json');path.write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');rows.append({'scope':'audit27','gate':name,'path':str(path.relative_to(a.output)),'sha256':sha(path)});print('PASS rebuilt audit27 gate='+name,flush=True)
 for name in commands:
  if name=='preference':continue
  path=a.output/('secure-'+name+'.json');argv=[sys.executable,'-E','-s',str(ROOT/'tools/secure_gate_driver.py'),'--build',str(a.build),'--gate',name,'--output',str(path)]
  result=subprocess.run(argv,cwd=ROOT,env=isolated_env(),capture_output=True,timeout=1200)
  if result.returncode or result.stderr:raise RuntimeError('Secure candidate gate failed: '+name+'; raw diagnostics withheld')
  if result.stdout!=('PASS secure runtime gate='+name+'; actual_jar=true; explicit_artifact_adapter=true\n').encode():raise ValueError('Secure gate output differs')
  rows.append({'scope':'secure','gate':name,'path':str(path.relative_to(a.output)),'sha256':sha(path)});print(result.stdout.decode().strip(),flush=True)
 if state()!=initial or check_secure_artifact(a.build)[0]!=identity:raise ValueError('Qualification inputs changed')
 record={'qualification':False,'scope':'Seventeen rebuilt audit27 gates and sixteen explicitly adapted secure gates; private-save product gates separate','execution_commit':initial['commit'],'source_dirty':False,'product_jar_sha256':product['jar_sha256'],'command_source_sha256':sha(ROOT/'audit/preference-gate-commands.json'),'observations':rows,'limits':['Fixture execution does not qualify native GUI or real controllers','Static helper normalization is not applied to runtime JARs']}
 (a.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS combined gates; audit27=17; secure=16')
if __name__=='__main__':main()
