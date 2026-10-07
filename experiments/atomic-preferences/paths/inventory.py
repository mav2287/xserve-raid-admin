#!/usr/bin/env python3
"""Select preference call and counter sites from immutable Apple bytecode, without running it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from inventory import disassemble_entries
from class_patch import ClassFile
from audit_support import isolated_env,sha,verify_jdk,verify_python

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-clean',action='store_true');a=p.parse_args()
    verify_python();compiler=verify_jdk(a.jdk)
    build=ROOT/'build'
    if build.is_symlink() or a.output.exists() or a.output.is_symlink() or not a.output.resolve().is_relative_to(build.resolve()) or a.output.resolve()==build.resolve():raise ValueError('New static inventory output inside real build required')
    jar=ROOT/'original/RAID_Admin_original.jar';candidate=ROOT/'build/preference-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(jar)!='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449' or sha(candidate)!='e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62':raise ValueError('Pinned original/audit27 required')
    files=[Path(__file__).resolve(),ROOT/'audit/static-inventory.json']+sorted((ROOT/'tools').glob('*.py'))+[ROOT/('audit/'+n+'-lock.json') for n in ['jdk','python']]
    sources={str(f.relative_to(ROOT)):sha(f) for f in files}
    def state():return (subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env()).decode().strip(),bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
    initial=state()
    if a.require_clean:
        if initial[1]:raise ValueError('Clean inventory source required')
        for n,h in sources.items():
            data=subprocess.check_output(['/usr/bin/git','show',initial[0]+':'+n],cwd=ROOT,env=isolated_env())
            if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Inventory source differs from Git')
    inv=json.loads((ROOT/'audit/static-inventory.json').read_text());classes=set();sites=[]
    tokens=['synchronize:','synchronizePrefs:','updatePreferences:','getPreferences:']
    for m in inv['methods']:
        calls=[c for c in m['calls'] if any(t in c for t in tokens)]
        if calls:classes.add(m['class']);sites.append({'class':m['class'],'signature':m['signature'],'calls':calls})
    with zipfile.ZipFile(jar) as z:
        if inv['jar_sha256']!=sha(jar) or any(hashlib.sha256(z.read(n)).hexdigest()!=h for n,h in inv['entry_hashes'].items()):raise ValueError('Cached original inventory entry hashes differ')
        for n in z.namelist():
            if not n.endswith('.class'):continue
            cls=ClassFile(z.read(n))
            if any(tag==1 and value==b'changeCount' for tag,value in cls.pool.values()) or n.startswith('com/apple/util/prefs/'):classes.add(n[:-6].replace('/','.'))
        names=sorted(c.replace('.','/')+'.class' for c in classes);hashes={n:hashlib.sha256(z.read(n)).hexdigest() for n in names}
    with zipfile.ZipFile(candidate) as z:changed=[n for n,h in hashes.items() if hashlib.sha256(z.read(n)).hexdigest()!=h]
    if changed!=['com/apple/util/prefs/FileBasedPreferences.class']:raise ValueError('Relevant audit27 class deltas differ')
    a.output.mkdir(parents=True);text=disassemble_entries(a.jdk,jar,names);(a.output/'original.javap').write_text(text)
    rows=[];cls=method=None
    for line in text.splitlines():
        m=re.match(r'^(?:\w+ )*(?:class|interface) ([\w.$]+).*\{$',line)
        if m:cls=m[1];method=None
        if re.match(r'^  [^ ].*\(.*\).*;$',line):method=line.strip()
        if 'putfield' in line and re.search(r'// Field (?:[\w/$]+\.)?changeCount:I$',line):rows.append({'class':cls,'method':method,'instruction':line.strip()})
    if len(names)!=22 or len(sites)!=23 or len(rows)!=7:raise ValueError('Preference static inventory counts differ')
    verify_jdk(a.jdk)
    if initial!=state() or sha(jar)!='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449' or sha(candidate)!='e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62' or any(sha(ROOT/n)!=h for n,h in sources.items()):raise ValueError('Inventory inputs changed')
    record={'qualification':False,'source_commit':initial[0],'source_dirty':initial[1],'clean_experimental_execution':a.require_clean,'sources':sources,'compiler_tree_sha256':compiler,'original_sha256':sha(jar),'audit27_sha256':sha(candidate),'original_entries':hashes,'selected_candidate_changed_entries':changed,'selected_original_disassembly_sha256':sha(a.output/'original.javap'),'sites':sites,'original_changeCount_field_writes':rows,'scope':'Original bytecode selection; candidate differences cover only selected entries; callers selected by method-name matching, field writes are original putfield only; no runtime frequency or reflective/native completeness'}
    (a.output/'selection.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS preference static selection; classes=22; caller_methods=23; counter_writes=7; code_executed=false')
if __name__=='__main__':main()
