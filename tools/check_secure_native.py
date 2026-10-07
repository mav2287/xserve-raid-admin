#!/usr/bin/env python3
"""Re-exercise private transaction primitives and real product writer under native faults."""
import argparse,hashlib,json,re,subprocess,tempfile,sys
from pathlib import Path
from audit_support import ROOT,JAVA_FLAGS,isolated_env,sha,verify_jdk,verify_python,run_jdk
from runtime import runtime_manifest,verify_runtime
from secure_build import verify_native_inputs, state,command,entries
# Reuse only the disposable fixture setup/ACL cleanup functions, never its runner.
sys.path.insert(0,str(ROOT/'experiments/atomic-preferences'))
from check import setup,disposable

def replace(source,old,new):
    if source.count(old)!=1:raise ValueError('Native mutation target is not unique')
    return source.replace(old,new)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-clean',action='store_true');a=p.parse_args();verify_python();verify_jdk(a.jdk);initial=state()
    if a.output.exists() or a.output.is_symlink() or not a.output.resolve().is_relative_to((ROOT/'build').resolve()):raise ValueError('New secure native output required')
    source=ROOT/'modernization/private-preferences';native=(source/'native/private_file.c').read_text();manifest=json.loads((a.build/'provenance.json').read_text());jar=a.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar';base=a.build/'audit27-reference/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(jar)!=manifest['jar_sha256']:raise ValueError('Secure product JAR differs')
    verify_native_inputs(manifest)
    layout_hashes={}
    original=(ROOT/'experiments/atomic-preferences/atomic_file.c').read_text()
    if native.count('(*env)->SetLongField(env, owner, handle_field, 0);')!=2 or native.count('"(Lcompat/PrivatePreferenceFile$Session;)V"')!=2 or native.count('return 0x58415204;')!=1:raise ValueError('Native ownership/ABI replacement counts differ')
    # Invert the reviewed production changes; all other transaction code is immutable.
    normalized=native.replace('/* Darwin private preference transaction. No controller or Keychain APIs. */','/* Nonshipping Darwin transaction experiment. No controller or Keychain APIs. */').replace('compat/PrivatePreferenceFile','atomicfixture/AtomicPreferenceFile').replace('0x58415204','0x58415201').replace('#include <limits.h>\n','').replace('length >= PATH_MAX','length >= 1048576')
    normalized=normalized.replace('static void commit_native(JNIEnv *, jclass, jobject);','static void commit_native(JNIEnv *, jclass, jlong);').replace('static void abort_native(JNIEnv *, jclass, jobject);','static void abort_native(JNIEnv *, jclass, jlong);').replace('"(Latomicfixture/AtomicPreferenceFile$Session;)V"','"(J)V"')
    normalized=normalized.replace('(JNIEnv *env, jclass unused, jobject owner) {\n    (void)unused;\n    if (!owner) { fail(env, "atomic-session-state", 0); return; }\n    jlong handle = (*env)->GetLongField(env, owner, handle_field);','(JNIEnv *env, jclass unused, jlong handle) {\n    (void)unused;')
    normalized=normalized.replace('\n    /* Transfer ownership only after native entry, while the Java owner is locked. */\n    (*env)->SetLongField(env, owner, handle_field, 0);','')
    normalized=normalized.replace('value = s->target_present ? renameat','do { value = s->target_present ? renameat').replace('RENAME_EXCL);\n        /* An interrupted remote rename may already have committed. Do not retry. */\n        if (value < 0) error = errno == EINTR ? "atomic-rename-uncertain" : "atomic-rename";','RENAME_EXCL); } while (value < 0 && errno == EINTR);\n        if (value < 0) error = "atomic-rename";')
    if normalized!=original:raise ValueError('Native port differs beyond reviewed ABI/ownership/rename/path changes')
    files=sorted((source/'tests').glob('*.java'));inputs={str(f.relative_to(ROOT)):sha(f) for f in files+sorted((ROOT/'tools').glob('*.py'))+[source/'native/private_file.c',ROOT/'experiments/atomic-preferences/atomic_file.c',ROOT/'experiments/atomic-preferences/check.py']}
    if a.require_clean and (initial['dirty'] or manifest['source_dirty']):raise ValueError('Clean native fixture and product required')
    a.output.mkdir();classes=a.output/'classes';classes.mkdir();run_jdk(a.jdk,'javac',['-source','8','-target','8','-cp',str(jar),'-d',str(classes)]+list(map(str,files)))
    hashes={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')};rows=[];faults=[];negatives=[];lock=runtime_manifest();runtimes=[];libraries={}
    clang=command(['/usr/bin/xcrun','--find','clang']).decode().strip();sdk=command(['/usr/bin/xcrun','--show-sdk-path']).decode().strip()
    def build_variant(cpu,folder,text):
        folder.mkdir();c=folder/'private_file.c';c.write_text(text);lib=folder/'libPrivatePreference.dylib';command([clang,'-target',cpu+'-apple-macos11.0','-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fvisibility=hidden','-dynamiclib','-Wl,-install_name,@rpath/libPrivatePreference.dylib','-I'+str(a.jdk/'include'),'-I'+str(a.jdk/'include/darwin'),c,'-o',lib]);first=sha(lib);repeat=folder/'repeat.dylib';command([clang,'-target',cpu+'-apple-macos11.0','-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fvisibility=hidden','-dynamiclib','-Wl,-install_name,@rpath/libPrivatePreference.dylib','-I'+str(a.jdk/'include'),'-I'+str(a.jdk/'include/darwin'),c,'-o',repeat]);
        if sha(repeat)!=first:raise ValueError('Native variant repeat differs')
        return lib
    def layout(folder,lib):
        resource=folder/'RAID Admin.app/Contents/Resources';resource.mkdir(parents=True);candidate=resource/'RAID_Admin.jar';candidate.write_bytes(jar.read_bytes());framework=resource.parent/'Frameworks';framework.mkdir();(framework/'libPrivatePreference.dylib').write_bytes(lib.read_bytes());layout_hashes[str(candidate.relative_to(a.output))]=sha(candidate);layout_hashes[str((framework/'libPrivatePreference.dylib').relative_to(a.output))]=sha(framework/'libPrivatePreference.dylib');return candidate.resolve()
    def execute(runtime,candidate,root,mode,main,scenario=None,mask=0o022):
        argv=[runtime/'Contents/Home/bin/java']+JAVA_FLAGS+[mode,'-Xverify:all','-Xms256m','-Xmx256m','-Djava.awt.headless=true','-Dlog4j.defaultInitOverride=true','-Duser.home='+str(root/'fake-home'),'-Dfixture.directory='+str(root),'-Dfixture.reference='+str(base.resolve()),'-cp',str(classes.resolve())+':'+str(candidate)]
        if scenario:argv.append('-Dfixture.scenario='+scenario)
        return subprocess.run(list(map(str,argv+['securefixture.'+main])),cwd=ROOT,env=isolated_env(),capture_output=True,timeout=120,umask=mask)
    rename='''value = s->target_present ? renameat(s->dirfd, s->temporary, s->dirfd, s->base)
            : renameatx_np(s->dirfd, s->temporary, s->dirfd, s->base, RENAME_EXCL);'''
    failed=replace(native,rename,'value = -1; errno = EIO;')
    race='''int planted = openat(s->dirfd, s->base, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (planted < 0 || write(planted, "\\004\\005\\006", 3) != 3) { if (planted >= 0) close(planted); error = "fault-plant"; }
        else close(planted);
        '''
    fault_variants={
      'stat-recovered':replace(native,'stat_fd(fd, &temporary) < 0 && stat_fd(fd, &temporary) < 0','(errno = EIO, -1) < 0 && stat_fd(fd, &temporary) < 0'),
      'stat-leftover':replace(native,'stat_fd(fd, &temporary) < 0 && stat_fd(fd, &temporary) < 0','(errno = EIO, -1) < 0 && (errno = EIO, -1) < 0'),
      'mode':replace(native,'mode = fchmod(fd, 0600)','mode = (errno = EACCES, -1)'),
      'dup':replace(native,'s->verify_fd = fcntl(fd, F_DUPFD_CLOEXEC, 0)','s->verify_fd = (errno = EMFILE, -1)'),
      'create-interrupted-before':replace(native,'fd = openat(s->dirfd, s->temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);','fd = -1; errno = EINTR;'),
      'create-interrupted-after':replace(native,'fd = openat(s->dirfd, s->temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);','fd = openat(s->dirfd, s->temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600); if (fd >= 0) { close(fd); fd = -1; errno = EINTR; }'),
      'rename':failed, 'rename-interrupted-before':replace(native,rename,'value = -1; errno = EINTR;'), 'rename-interrupted-after':replace(native,rename,rename+'\n        if (value == 0) { value = -1; errno = EINTR; }'),'remote-sync-ok':replace(native,'else if (!(fs.f_flags & MNT_LOCAL))','else if (1)'),
      'statfs':replace(native,'value = fstatfs(s->verify_fd, &fs)','value = (errno = EIO, -1)'),
      'remote-sync':replace(replace(native,'else if (!(fs.f_flags & MNT_LOCAL))','else if (1)'),'value = fsync(s->verify_fd)','value = (errno = EIO, -1)'),
      'rename-cleanup':replace(failed,'if (!s->created) return 1;','if (s->created) return 0;'),
      'close-committed':replace(native,'if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;','if (s->verify_fd >= 0) { close(s->verify_fd); issues |= 2; }'),
      'rename-exclusive':replace(native,rename,race+rename)}
    close_fault='if (s->verify_fd >= 0) { close(s->verify_fd); issues |= 2; }'
    fault_variants['rename-interrupted-before-close']=replace(fault_variants['rename-interrupted-before'],'if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;',close_fault)
    fault_variants['rename-interrupted-after-close']=replace(fault_variants['rename-interrupted-after'],'if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;',close_fault)
    fault_variants['rename-interrupted-before-leftover']=replace(fault_variants['rename-interrupted-before'],'if (!s->created) return 1;','if (s->created) return 0;')
    fault_variants['rename-interrupted-before-leftover-close']=replace(fault_variants['rename-interrupted-before-leftover'],'if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;',close_fault)
    target='''if (!error && ((s->target_present && (target_exists < 0 || !target_ok(&target) || target.st_dev != s->target_device || target.st_ino != s->target_inode))
        || (!s->target_present && (target_exists == 0 || errno != ENOENT)))) error = "atomic-target-changed";'''
    temp='''if (!temporary_ok(s) || stat_name(s->dirfd, s->temporary, &temporary) < 0
        || temporary.st_dev != s->temporary_device || temporary.st_ino != s->temporary_inode) error = "atomic-temporary-changed";'''
    controls={
      'abort-deletes-target':(replace(native,'unlinkat(s->dirfd, s->temporary, 0)','unlinkat(s->dirfd, s->base, 0)'),'failure-original-present'),
      'abort-without-identity':(replace(native,'if (!S_ISREG(st.st_mode) || st.st_uid != geteuid() || st.st_dev != s->temporary_device || st.st_ino != s->temporary_inode) return 0;',''),'foreign-temporary-not-deleted'),
      'skip-target-identity':(replace(native,target,'(void)target_exists;'),'concurrent-target-rejected'),
      'skip-temporary-identity':(replace(native,temp,'(void)temporary;'),'temporary-swap-rejected'),
      'skip-parent-policy':(replace(native,'if (!parent_ok(s->dirfd))','if (0)'),'rejection-code'),
      'skip-begin-write-check':(replace(native,'if (!target_writable(s))','if (0)'),'rejection-code'),
      'skip-commit-write-check':(replace(native,'if (!error && s->target_present && !target_writable(s))','if (0)'),'commit-readonly-rejected'),
      'skip-target-write-check':(replace(native,'return value == 0;\n}\n\nstatic int temporary_ok','return 1;\n}\n\nstatic int temporary_ok'),'rejection-code'),
      'allow-group-writable-parent':(replace(native,'!(st.st_mode & 0022)','!(st.st_mode & 0002)'),'rejection-code'),
      'allow-parent-allow-acl':(replace(native,'|| tag == ACL_EXTENDED_ALLOW',''),'rejection-code'),
      'allow-parent-inherit-acl':(replace(native,'|| acl_get_flag_np(flags, ACL_ENTRY_FILE_INHERIT) != 0',''),'rejection-code'),
      'leak-native-session-fd':(replace(native,'if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;',''),'fd-lifetime')}
    for folder,arch,cpu in [('arm64','aarch64','arm64'),('x64','x64','x86_64')]:
        runtime=ROOT/('build/logging-bundled-'+folder+'-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk');verify_runtime(runtime,lock['architectures'][arch]);runtimes.append((runtime,arch));lib=a.build/manifest['native_helpers'][arch]['path'];candidate=layout(a.output/(arch+'-normal'),lib)
        for mode in ['-Xint','-Xcomp']:
            for mask in [0,0o022,0o077,0o277]:
                with disposable('secure-native-targets-',a.output) as directory:
                    root=Path(directory);setup(root);result=execute(runtime,candidate,root,mode,'AtomicPreferenceObservation',mask=mask)
                    expected=b'PASS atomic preference experiment; cases=37; old_readers_isolated=true; serialization_failures_preserve_original=true; fd_delta=0\n'
                    if result.returncode or result.stderr or result.stdout!=expected:raise RuntimeError('Secure native functional fixture failed; diagnostics withheld')
                    rows.append({'architecture':arch,'mode':mode,'umask_requested':mask,'cases':37,'result':result.stdout.decode().strip(),'scope':'33 actual writer cases; four hook cases use real private JNI/session primitives via fixture reflection'})
        for scenario,text in fault_variants.items():
            lib=build_variant(cpu,a.output/(arch+'-fault-'+scenario),text);libraries[str(lib.relative_to(a.output))]=sha(lib);candidate=layout(a.output/(arch+'-fault-'+scenario+'-layout'),lib)
            for mode in ['-Xint','-Xcomp']:
                with disposable('secure-fault-targets-',a.output) as directory:
                    result=execute(runtime,candidate,Path(directory),mode,'AtomicFaultObservation',scenario)
                    expected=('PASS atomic fault '+scenario+'; repetitions=32; fd_delta=0; gc_delta=0\n').encode();code=b'' if scenario in ['stat-recovered','remote-sync-ok'] else b'RAID_ADMIN_PREFERENCES_COMMITTED_CLEANUP_FAILED\n' if scenario=='close-committed' else b'RAID_ADMIN_PREFERENCES_SAVE_UNCONFIRMED\n' if scenario.startswith('rename-interrupted-') else b'RAID_ADMIN_PREFERENCES_SAVE_FAILED\n'
                    if result.returncode or result.stdout!=expected or result.stderr!=code:raise RuntimeError('Secure native fault fixture failed; diagnostics withheld')
                    faults.append({'architecture':arch,'mode':mode,'scenario':scenario,'result':result.stdout.decode().strip(),'stderr_fixed_code':code.decode().strip(),'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'native_sha256':sha(lib)})
        for label,(text,code) in controls.items():
            lib=build_variant(cpu,a.output/(arch+'-negative-'+label),text);libraries[str(lib.relative_to(a.output))]=sha(lib);candidate=layout(a.output/(arch+'-negative-'+label+'-layout'),lib)
            with disposable('secure-negative-targets-',a.output) as directory:
                root=Path(directory);setup(root);result=execute(runtime,candidate,root,'-Xint','AtomicPreferenceObservation');prefix=('Exception in thread "main" java.lang.AssertionError: atomic-preference:'+code+'\n').encode()
                if result.returncode!=1 or result.stdout or not result.stderr.startswith(prefix) or not re.fullmatch(rb'(?:\tat securefixture\.AtomicPreferenceObservation\.(?:check|rejected|main)\(AtomicPreferenceObservation\.java:\d+\)\n){2,3}',result.stderr[len(prefix):]):raise ValueError('Secure native negative failed unexpectedly')
                negatives.append({'architecture':arch,'mutation':label,'assertion_code':code,'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),'native_sha256':sha(lib)})
        text=replace(fault_variants['rename-exclusive'],', RENAME_EXCL);',', 0);');lib=build_variant(cpu,a.output/(arch+'-negative-exclusive'),text);libraries[str(lib.relative_to(a.output))]=sha(lib);candidate=layout(a.output/(arch+'-negative-exclusive-layout'),lib)
        with disposable('secure-exclusive-targets-',a.output) as directory:
            result=execute(runtime,candidate,Path(directory),'-Xint','AtomicFaultObservation','rename-exclusive');prefix=b'Exception in thread "main" java.lang.AssertionError: atomic-fault:failure-code\n'
            if result.returncode!=1 or result.stdout or not result.stderr.startswith(prefix) or not re.fullmatch(rb'(?:\tat securefixture\.AtomicFaultObservation\.(?:check|run|main)\(AtomicFaultObservation\.java:\d+\)\n){3}',result.stderr[len(prefix):]):raise ValueError('Secure exclusive negative failed unexpectedly')
            negatives.append({'architecture':arch,'mutation':'no-rename-excl','assertion_code':'atomic-fault:failure-code','stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),'native_sha256':sha(lib)})
    verify_native_inputs(manifest)
    if any(sha(a.output/n)!=h for n,h in layout_hashes.items()):raise ValueError('Copied product layout changed')
    for runtime,arch in runtimes:verify_runtime(runtime,lock['architectures'][arch])
    verify_jdk(a.jdk)
    if state()!=initial or sha(jar)!=manifest['jar_sha256'] or any(sha(ROOT/n)!=h for n,h in inputs.items()) or any(sha(a.output/n)!=h for n,h in libraries.items()) or hashes!={str(f.relative_to(classes)):sha(f) for f in classes.rglob('*.class')}:raise ValueError('Secure native fixture inputs changed')
    record={'qualification':False,'scope':'Actual private product writer/session/native fixtures; disposable files only','source_commit':initial['commit'],'source_dirty':initial['dirty'],'clean_execution':a.require_clean,'product_jar_sha256':sha(jar),'inputs':inputs,'layout_hashes':layout_hashes,'native_input_manifest_sha256':sha(a.build/'provenance.json'),'probe_hashes':hashes,'observations':rows,'fault_observations':faults,'negative_controls':negatives,'native_variant_hashes':libraries,'limits':['Four race/hook cases invoke real primitives through fixture reflection, not a shipping hook','Faults are injected source variants, not real filesystem failure or power-loss tests','No native GUI, real profiles, other users/root, remote filesystems or hardware; x64 uses Rosetta']}
    (a.output/'observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS secure native matrix; functional='+str(len(rows))+'x37; faults='+str(len(faults))+'; negatives='+str(len(negatives)))
if __name__=='__main__':main()
