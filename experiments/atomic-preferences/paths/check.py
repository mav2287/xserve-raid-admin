#!/usr/bin/env python3
"""Characterize pinned audit27 raw-stream pathname semantics in disposable directories."""
import argparse
import hashlib
import json
import os
import plistlib
import stat
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from audit_support import JAVA_FLAGS,isolated_env,run_jdk,sha,verify_jdk,verify_python
from runtime import runtime_manifest,verify_runtime
CASES=['absolute','relative','dot','dotdot','missingdotdot','filedotdot','basedot','basedotdot','slashes','composed','decomposed','nonbmp','high','low','reversed','nul','empty','trailing','long255','multi255','multi258','long256']
REFERENCE_SHA='e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-clean',action='store_true');a=p.parse_args()
    verify_python();compiler=verify_jdk(a.jdk)
    build=ROOT/'build'
    if build.is_symlink() or a.output.exists() or a.output.is_symlink() or not a.output.resolve().is_relative_to(build.resolve()) or a.output.resolve()==build.resolve():raise ValueError('New pathname output inside real build directory required')
    reference=ROOT/'build/preference-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(reference)!=REFERENCE_SHA:raise ValueError('Pinned audit27 reference required')
    inputs=[HERE/'PathObservation.java',HERE/'check.py',ROOT/'patches/compat/PreferenceIO.java']+[ROOT/('tools/'+n) for n in ['audit_support.py','runtime.py']]+[ROOT/('audit/'+n+'-lock.json') for n in ['runtime','jdk','python']]
    sources={str(f.relative_to(ROOT)):sha(f) for f in inputs}
    def state():return (subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env()).decode().strip(),bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env())))
    initial=state()
    if a.require_clean:
        if initial[1]:raise ValueError('Clean pathname source required')
        for name,digest in sources.items():
            data=subprocess.check_output(['/usr/bin/git','show',initial[0]+':'+name],cwd=ROOT,env=isolated_env())
            if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Pathname source differs from Git')
    a.output.mkdir(parents=True);classes=a.output/'classes';classes.mkdir()
    run_jdk(a.jdk,'javac',['-source','8','-target','8','-d',str(classes),str(HERE/'PathObservation.java')])
    probes={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}
    with zipfile.ZipFile(reference) as z:
        if len(z.namelist())!=len(set(z.namelist())) or 'META-INF/INDEX.LIST' in z.namelist() or any(n.startswith('META-INF/versions/') for n in z.namelist()) or re.search(rb'(?im)^Class-Path:',z.read('META-INF/MANIFEST.MF')):raise ValueError('Reference classpath extension')
        helper=hashlib.sha256(z.read('compat/PreferenceIO.class')).hexdigest()
    rows=[];first=None;lock=runtime_manifest();runtimes=[]
    metadata_tools={name:sha(Path(name)) for name in ['/bin/df','/usr/sbin/diskutil']}
    mount=subprocess.check_output(['/bin/df','-P',str(a.output.resolve())],env=isolated_env(),timeout=10).decode().splitlines()[-1].split()[-1]
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist',mount],env=isolated_env(),timeout=10))
    filesystem={key:volume[key] for key in ['FilesystemName','FilesystemType','FilesystemUserVisibleName']}
    with tempfile.TemporaryDirectory(prefix='volume-disposable-',dir=a.output) as directory:
        folder=Path(directory);(folder/'CaseProbe').write_bytes(b'fixture');filesystem['case_sensitive_observed']=not (folder/'caseprobe').exists()
        (folder/'é').write_bytes(b'fixture');filesystem['normalization_sensitive_observed']=not (folder/'e\u0301').exists()
    for folder,arch in [('arm64','aarch64'),('x64','x64')]:
        runtime=ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(runtime,lock['architectures'][arch]);runtimes.append((runtime,arch))
        for mode in ['-Xint','-Xcomp']:
            with tempfile.TemporaryDirectory(prefix='path-disposable-',dir=a.output) as directory:
                root=Path(directory).resolve()
                for name in CASES:(root/name).mkdir()
                (root/'dotdot/child').mkdir();(root/'basedotdot/child').mkdir()
                (root/'filedotdot/blocker').write_bytes(b'fixture-blocker')
                argv=[str(runtime/'Contents/Home/bin/java')]+JAVA_FLAGS+[mode,'-Xverify:all','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(root/'fake-home'),'-Dfixture.directory='+str(root),'-Dfixture.reference='+str(reference.resolve()),'-cp',str(classes.resolve()),'atomicpaths.PathObservation']
                result=subprocess.run(argv,cwd=root,env=isolated_env(),capture_output=True,timeout=120,umask=0o022)
                if result.returncode or result.stderr:raise RuntimeError('Pathname probe failed; raw output withheld')
                lines=result.stdout.decode('ascii').splitlines();observations=[]
                encoding=lines.pop(0).split('\t')
                if encoding!=['ENCODING','UTF-8','UTF-8']:raise ValueError('Pinned encoding differs')
                if len(lines)!=len(CASES):raise ValueError('Pathname case count differs')
                for name,line in zip(CASES,lines):
                    parts=line.split('\t')
                    if len(parts)!=6 or parts[0]!=name or parts[1] not in ['SUCCESS','java.io.FileNotFoundException']:raise ValueError('Unexpected pathname result')
                    folder=os.fsencode(root/name);names=sorted(os.listdir(folder));files=[]
                    for raw in names:
                        path=folder+b'/'+raw
                        if name in ['dotdot','basedotdot'] and raw==b'child':
                            if not os.path.isdir(path) or os.listdir(path):raise ValueError('Dotdot child modified')
                        elif name=='filedotdot' and raw==b'blocker':
                            if os.path.islink(path) or Path(os.fsdecode(path)).read_bytes()!=b'fixture-blocker':raise ValueError('Blocker modified')
                        else:
                            if os.path.islink(path) or not os.path.isfile(path):raise ValueError('Unexpected pathname file type')
                            data=Path(os.fsdecode(path)).read_bytes();files.append({'name_bytes_hex':raw.hex(),'sha256':hashlib.sha256(data).hexdigest(),'length':len(data),'mode':stat.S_IMODE(os.lstat(path).st_mode)})
                    failures={'nul','empty','long256','missingdotdot','filedotdot','basedot','basedotdot'}
                    expected_result='java.io.FileNotFoundException' if name in failures else 'SUCCESS'
                    if parts[1]!=expected_result:raise ValueError('Characterized pathname result differs')
                    expected_names={'composed':'é','decomposed':'e\u0301','nonbmp':'😃','high':'a?b','low':'a?b','reversed':'a??b','long255':'x'*255,'multi255':'日'*85,'multi258':'日'*86}
                    if parts[1]=='SUCCESS' and [f['name_bytes_hex'] for f in files]!=[expected_names.get(name,'profile').encode().hex()]:raise ValueError('Characterized filename bytes differ')
                    if len(files)!=(1 if parts[1]=='SUCCESS' else 0):raise ValueError('Pathname success/file mismatch')
                    if any(f['sha256']!='b6d80632494c573e1da5813be98bf7c6e44e4e863ffe6c6254cd8f765d248cb5' or f['length']!=151 or f['mode']!=0o644 for f in files):raise ValueError('Observed XML bytes or permissions differ')
                    observations.append({'case':name,'result':parts[1],'input_relative_utf16_hex':parts[2],'file_path_relative_utf16_hex':parts[3],'nio_to_path_result':parts[4],'java_listing_utf16_hex':parts[5].split(',') if parts[5] else [],'files':files})
                if {f.name for f in root.iterdir()}!=set(CASES):raise ValueError('Unexpected top-level entries')
                if first is None:first=observations
                elif observations!=first:raise ValueError('Pathname semantics differ between runtime/mode')
                rows.append({'architecture':arch,'mode':mode,'umask_requested':0o022,'encoding':{'sun.jnu.encoding':encoding[1],'file.encoding':encoding[2],'file.encoding_forced_by_flags':True},'requested_locale':{k:isolated_env()[k] for k in ['LANG','LC_ALL']},'observations':observations})
    for runtime,arch in runtimes:verify_runtime(runtime,lock['architectures'][arch])
    verify_jdk(a.jdk)
    if initial!=state() or sha(reference)!=REFERENCE_SHA or any(sha(ROOT/n)!=d for n,d in sources.items()) or probes!={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}:raise ValueError('Pathname inputs changed')
    if {f.name for f in a.output.iterdir()}!={'classes'} or any(sha(Path(n))!=d for n,d in metadata_tools.items()):raise ValueError('Pathname output or metadata tools changed')
    record={'scope':'Nonshipping disposable raw-stream filename characterization','qualification':False,'source_commit':initial[0],'source_dirty':initial[1],'clean_experimental_execution':a.require_clean,'sources':sources,'compiler_tree_sha256':compiler,'reference_sha256':REFERENCE_SHA,'helper_sha256':helper,'filesystem':filesystem,'metadata_tool_sha256':metadata_tools,'synthetic_empty_xml_sha256':'b6d80632494c573e1da5813be98bf7c6e44e4e863ffe6c6254cd8f765d248cb5','probe_hashes':probes,'observations':rows,'limits':['Characterizes audit27 raw-stream helper, not factory/Main/GUI or a shipping atomic helper','x64 uses Rosetta; no physical Intel, production profiles, native preference database or hardware','Known disposable directories only; no external symlink, ownership or remote-filesystem qualification']}
    (a.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS filename characterization; variants=4; cases=22; no product changes')
if __name__=='__main__':main()
