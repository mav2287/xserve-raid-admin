#!/usr/bin/env python3
"""Rebuild audit27 and add only private preference saving; never install or launch."""
import argparse,hashlib,json,plistlib,subprocess,sys,shlex
from pathlib import Path
import zipfile
from audit_support import ROOT,isolated_env,sha,tree,modes,digest,verify_jdk,verify_python,run_jdk
from baseline import write_jar
from bundle import copy_verified
BASE_SHA='e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62'
VERSION='1.5.1-modern.audit.28'
NATIVE_ABI='0x58415204'
HELPERS={'compat/PreferenceIO.class','compat/PrivatePreferenceFile.class','compat/PrivatePreferenceFile$Library.class','compat/PrivatePreferenceFile$Session.class','compat/PreferenceSaveFailure.class','compat/PreferenceSaveFailure$Reporter.class','compat/PreferenceSaveFailure$1.class','compat/PreferenceSaveFailure$1$1.class'}

def command(argv):
    p=subprocess.run(list(map(str,argv)),cwd=ROOT,env=isolated_env(),capture_output=True,timeout=120)
    if p.returncode:raise RuntimeError('Secure build command failed; uncontrolled diagnostics withheld')
    return p.stdout

def entries(path):
    with zipfile.ZipFile(path) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate JAR entries')
        return {n:z.read(n) for n in z.namelist() if not n.endswith('/')}

def state():return {'commit':command(['/usr/bin/git','rev-parse','HEAD']).decode().strip(),'dirty':bool(command(['/usr/bin/git','status','--porcelain']))}

def sources():return sorted((ROOT/'modernization/private-preferences').rglob('*'))+sorted((ROOT/'tools').glob('*.py'))+[ROOT/'build-secure.sh']

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-clean',action='store_true');a=p.parse_args();verify_python();compiler=verify_jdk(a.jdk)
    build=ROOT/'build';out=a.output.resolve()
    if build.is_symlink() or a.output.exists() or a.output.is_symlink() or not out.is_relative_to(build.resolve()) or out==build.resolve():raise ValueError('New secure output inside real build required')
    initial=state();inputs={str(f.relative_to(ROOT)):sha(f) for f in sources() if f.is_file() and '__pycache__' not in f.parts}
    if a.require_clean:
        if initial['dirty']:raise ValueError('Clean secure build source required')
        for n,h in inputs.items():
            if hashlib.sha256(command(['/usr/bin/git','show',initial['commit']+':'+n])).hexdigest()!=h:raise ValueError('Secure source differs from Git')
    out.mkdir();base=out/'audit27-reference'
    command([sys.executable,'-E','-s',ROOT/'tools/baseline.py','--jdk',a.jdk,'--output',base])
    provenance=json.loads((base/'provenance.json').read_text());reference=base/'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(reference)!=BASE_SHA:raise ValueError('Rebuilt audit27 JAR differs from frozen reference')
    if provenance['input_hashes']!=json.loads((ROOT/'audit/expected-build.json').read_text())['expected']['input_hashes']:raise ValueError('Audit27 build inputs differ from frozen baseline')
    inputs.update(provenance['input_hashes'])
    production=ROOT/'modernization/private-preferences'
    if any((production/n).read_text().count(NATIVE_ABI)!=1 for n in ['compat/PrivatePreferenceFile.java','native/private_file.c']):raise ValueError('Native ABI source contract differs')
    classes=out/'classes';classes.mkdir();source=ROOT/'modernization/private-preferences'
    run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(reference),'-d',str(classes)]+[str(f) for f in sorted((source/'compat').glob('*.java'))])
    helpers={str(f.relative_to(classes)):f.read_bytes() for f in classes.rglob('*.class')}
    if set(helpers)!=HELPERS or any(v[6:8]!=b'\x00\x34' for v in helpers.values()):raise ValueError('Secure helper class set/version differs')
    before=entries(reference);after=dict(before);after.update(helpers)
    if {n for n in before if before[n]!=after[n]}!={'compat/PreferenceIO.class'} or set(after)-set(before)!=HELPERS-{'compat/PreferenceIO.class'}:raise ValueError('Secure JAR delta differs')
    inverse={n:v for n,v in after.items() if n not in HELPERS-{'compat/PreferenceIO.class'}};inverse['compat/PreferenceIO.class']=before['compat/PreferenceIO.class']
    if inverse!=before:raise ValueError('Secure normalization is not exact')
    app=out/'RAID Admin.app';copy_verified(base/'RAID Admin.app',app,provenance['files'],provenance['file_modes'])
    jar=app/'Contents/Resources/RAID_Admin.jar';write_jar(jar,after);jar.chmod(0o644)
    plist=app/'Contents/Info.plist';metadata=plistlib.loads(plist.read_bytes());metadata.update(CFBundleShortVersionString=VERSION,CFBundleVersion='28');plist.write_bytes(plistlib.dumps(metadata,sort_keys=True))
    clang=command(['/usr/bin/xcrun','--find','clang']).decode().strip();sdk=command(['/usr/bin/xcrun','--show-sdk-path']).decode().strip();ld=command(['/usr/bin/xcrun','--find','ld']).decode().strip()
    tool_hashes={n:sha(Path(n)) for n in [clang,ld,'/usr/bin/xcrun','/usr/bin/nm','/usr/bin/otool','/usr/bin/lipo']}
    settings=Path(sdk)/'SDKSettings.json';sdk_hash=sha(settings);stub_hashes={str(f):sha(f) for f in sorted((Path(sdk)/'usr/lib').rglob('*.tbd'))};native={};native_dir=out/'native';native_dir.mkdir()
    for arch,cpu in [('aarch64','arm64'),('x64','x86_64')]:
        name='libPrivatePreference.dylib';archdir=native_dir/arch;archdir.mkdir();lib=archdir/name
        flags=[clang,'-target',cpu+'-apple-macos11.0','-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fvisibility=hidden','-dynamiclib','-Wl,-install_name,@rpath/'+name,'-I'+str(a.jdk/'include'),'-I'+str(a.jdk/'include/darwin'),source/'native/private_file.c']
        preprocessing=[f for f in flags if f!='-dynamiclib' and not str(f).startswith('-Wl,')]
        depfile=archdir/'headers.d';command(preprocessing+['-M','-MF',depfile])
        dependencies={n:sha(Path(n)) for n in shlex.split(depfile.read_text().replace('\\\n','').split(':',1)[1])}
        preprocessed=command(preprocessing+['-E','-P']);preprocessed_hash=hashlib.sha256(preprocessed).hexdigest()
        command(flags+['-o',lib]);repeat=out/(arch+'-repeat');repeat.mkdir();second=repeat/name;command(flags+['-o',second])
        if sha(lib)!=sha(second):raise ValueError('Native repeated build bytes differ')
        if sorted(command(['/usr/bin/nm','-gjU',lib]).decode().splitlines())!=['_JNI_OnLoad','_JNI_OnUnload']:raise ValueError('Unexpected native exports')
        if command(['/usr/bin/lipo','-archs',lib]).decode().strip()!=cpu:raise ValueError('Native architecture differs')
        deps=command(['/usr/bin/otool','-L',lib]).decode().splitlines()[1:]
        if [v.strip().split(' (')[0] for v in deps]!=['@rpath/'+name,'/usr/lib/libSystem.B.dylib']:raise ValueError('Unexpected native dependency')
        loads=command(['/usr/bin/otool','-l',lib]).decode()
        if 'LC_BUILD_VERSION' not in loads or 'minos 11.0' not in loads:raise ValueError('Native binary floor differs')
        if any(sha(Path(n))!=h for n,h in dependencies.items()) or hashlib.sha256(command(preprocessing+['-E','-P'])).hexdigest()!=preprocessed_hash:raise ValueError('Native header inputs changed')
        lib.chmod(0o644)
        native[arch]={'path':str(lib.relative_to(out)),'sha256':sha(lib),'preprocessed_sha256':preprocessed_hash,'header_hashes':dependencies,'repeated_bytes_equal':True,'architecture':cpu,'minimum_macos':'11.0','compile_argv':list(map(str,flags)),'dependencies':['/usr/lib/libSystem.B.dylib'],'exports':['_JNI_OnLoad','_JNI_OnUnload']}
    for n,h in tool_hashes.items():
        if sha(Path(n))!=h:raise ValueError('Native tool changed')
    if any(sha(Path(n))!=h for n,h in stub_hashes.items()) or sha(settings)!=sdk_hash or state()!=initial or any(sha(ROOT/n)!=h for n,h in inputs.items()):raise ValueError('Secure build inputs changed')
    verify_jdk(a.jdk)
    files=tree(app);permissions=modes(app)
    record={'schema':1,'purpose':'nonlaunchable secure preference intermediate; per-CPU packaging required; hardware/native GUI unqualified','compatibility_version':VERSION,'source_commit':initial['commit'],'source_dirty':initial['dirty'],'input_hashes':inputs,'original_jar_sha256':provenance['original_jar_sha256'],'audit27_jar_sha256':BASE_SHA,'audit27_provenance_sha256':sha(base/'provenance.json'),'jar_sha256':sha(jar),'jar_delta':{'modified':['compat/PreferenceIO.class'],'added':sorted(HELPERS-{'compat/PreferenceIO.class'})},'helper_hashes':{n:hashlib.sha256(v).hexdigest() for n,v in helpers.items()},'compiler_tree_sha256':compiler['tree_sha256'],'native_tool_hashes':tool_hashes,'sdk_settings_sha256':sdk_hash,'sdk_link_stub_hashes':stub_hashes,'jdk':provenance['jdk'],'builder':provenance['builder'],'native_abi':NATIVE_ABI,'native_helpers':native,'application_signing':None,'application_notarization':'not performed','files':files,'file_modes':permissions,'bundle_tree_sha256':digest({'files':files,'file_modes':permissions})}
    (out/'provenance.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS secure build; audit27_inverse_exact=true; repeated_native_equal=true; jar_sha256='+sha(jar))


def check_secure_artifact(output):
    """Verify actual common secure artifact; return its measured identity, never audit27's."""
    record=json.loads((output/'provenance.json').read_text());app=output/'RAID Admin.app'
    if record['native_abi']!=NATIVE_ABI:raise ValueError('Native ABI manifest differs')
    files,permissions=tree(app),modes(app)
    if files!=record['files'] or permissions!=record['file_modes'] or digest({'files':files,'file_modes':permissions})!=record['bundle_tree_sha256']:raise ValueError('Secure artifact snapshot differs')
    base=output/'audit27-reference/RAID Admin.app/Contents/Resources/RAID_Admin.jar';jar=app/'Contents/Resources/RAID_Admin.jar'
    if sha(base)!=BASE_SHA or sha(jar)!=record['jar_sha256']:raise ValueError('Secure reference/JAR changed')
    baseline=json.loads((output/'audit27-reference/provenance.json').read_bytes())
    expected=json.loads((ROOT/'audit/expected-build.json').read_bytes())['expected']
    baseapp=output/'audit27-reference/RAID Admin.app'
    baseidentity={'files':tree(baseapp),'file_modes':modes(baseapp),'input_hashes':baseline['input_hashes'],'original_jar_sha256':baseline['original_jar_sha256'],'jdk':baseline['jdk'],'builder':baseline['builder']}
    if baseidentity!=expected or baseline['files']!=baseidentity['files'] or baseline['file_modes']!=baseidentity['file_modes']:raise ValueError('Audit27 baseline differs from independently frozen identity')
    if set(files)!=set(expected['files']) or permissions!=expected['file_modes'] or {n for n,h in files.items() if expected['files'][n]!=h}!={'Contents/Resources/RAID_Admin.jar','Contents/Info.plist'}:raise ValueError('Secure non-JAR artifact delta differs')
    plist=plistlib.loads((app/'Contents/Info.plist').read_bytes());original=plistlib.loads((baseapp/'Contents/Info.plist').read_bytes());original.update(CFBundleShortVersionString=VERSION,CFBundleVersion='28')
    if plist!=original:raise ValueError('Secure Info.plist differs beyond two version fields')
    before,after=entries(base),entries(jar)
    if set(after)-set(before)!=HELPERS-{'compat/PreferenceIO.class'} or {n for n in before if before[n]!=after[n]}!={'compat/PreferenceIO.class'}:raise ValueError('Secure delta differs')
    if any(hashlib.sha256(after[n]).hexdigest()!=h for n,h in record['helper_hashes'].items()) or set(record['helper_hashes'])!=HELPERS:raise ValueError('Secure helper hashes differ')
    for arch,spec in record['native_helpers'].items():
        if sha(output/spec['path'])!=spec['sha256']:raise ValueError('Secure native changed')
    if any(n.startswith('/') or '..' in Path(n).parts or sha(ROOT/n)!=h for n,h in record['input_hashes'].items()):raise ValueError('Secure input source changed')
    identity={'files':files,'file_modes':permissions,'input_hashes':record['input_hashes'],'original_jar_sha256':record['original_jar_sha256'],'jdk':record['jdk'],'builder':record['builder']}
    return identity,record


def verify_native_inputs(record):
    for n,h in record['native_tool_hashes'].items():
        if sha(Path(n))!=h:raise ValueError('Native build tool changed')
    for n,h in record['sdk_link_stub_hashes'].items():
        if sha(Path(n))!=h:raise ValueError('Native SDK link input changed')
    for spec in record['native_helpers'].values():
        for n,h in spec['header_hashes'].items():
            if sha(Path(n))!=h:raise ValueError('Native header input changed')

if __name__=='__main__':main()
