#!/usr/bin/env python3
"""Run a nonshipping atomic profile experiment against disposable APFS files."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from audit_support import JAVA_FLAGS, isolated_env, run_jdk, sha, verify_jdk, verify_python
from runtime import runtime_manifest, verify_runtime

REFERENCE_SHA = 'e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62'
RESULT = 'PASS atomic preference experiment; cases=37; old_readers_isolated=true; serialization_failures_preserve_original=true; fd_delta=0\n'

def execute(argv, mask=None):
    saved = os.umask(mask) if mask is not None else None
    try:
        result = subprocess.run(list(map(str, argv)), env=isolated_env(), capture_output=True, timeout=120, cwd=ROOT)
    finally:
        if saved is not None: os.umask(saved)
    if result.returncode or result.stderr:
        raise RuntimeError('atomic-experiment-subprocess-failed; output withheld')
    return result.stdout.decode('utf-8')

def setup(root):
    (root / 'directory').mkdir(); os.mkfifo(root / 'fifo', 0o600)
    (root / 'public-parent').mkdir(); (root / 'public-parent').chmod(0o777)
    (root / 'acl-parent').mkdir()
    execute(['/bin/chmod', '+a', 'everyone allow read,file_inherit,directory_inherit', root / 'acl-parent'])
    (root / 'group-parent').mkdir(); (root / 'group-parent').chmod(0o770)
    for name, acl in [('allow-parent', 'everyone allow read'), ('inherit-deny-parent', 'everyone deny delete,file_inherit'), ('deny-parent', 'everyone deny delete')]:
        (root / name).mkdir()
        execute(['/bin/chmod', '+a', acl, root / name])
    (root / 'deny-write-file').write_bytes(bytes([9, 8, 7])); (root / 'deny-write-file').chmod(0o600)
    execute(['/bin/chmod', '+a', 'everyone deny write', root / 'deny-write-file'])
    (root / 'acl-file').write_bytes(bytes([9, 8, 7])); (root / 'acl-file').chmod(0o644)
    execute(['/bin/chmod', '+a', 'everyone allow read', root / 'acl-file'])

@contextmanager
def disposable(prefix, folder):
    with tempfile.TemporaryDirectory(prefix=prefix, dir=folder) as directory:
        root = Path(directory).resolve()
        try:
            yield directory
        finally:
            # Remove only ACLs deliberately installed on these owned fixture directories.
            # A deny-delete entry otherwise prevents TemporaryDirectory from removing them.
            for name in ['deny-parent', 'inherit-deny-parent']:
                path = root / name
                if path.is_dir() and not path.is_symlink():
                    execute(['/bin/chmod', '-N', path])
                    for child in path.iterdir():
                        if child.is_file() and not child.is_symlink(): execute(['/bin/chmod', '-N', child])

def replace_once(value, old, new):
    if value.count(old) != 1: raise ValueError('Atomic mutation target not unique')
    return value.replace(old, new)

def runtime_source_gate(runtime):
    archive = runtime / 'Contents/Home/src.zip'
    with zipfile.ZipFile(archive) as z:
        values = {name: z.read(name) for name in ['java/io/FileOutputStream.java', 'java/io/FileDescriptor.java', 'java/io/File.java', 'java/io/UnixFileSystem.java']}
    descriptor = values['java/io/FileDescriptor.java'].decode()
    output = values['java/io/FileOutputStream.java'].decode()
    constructor = output.split('public FileOutputStream(FileDescriptor fdObj)', 1)[1].split('private native void open0', 1)[0]
    if not all(v in descriptor for v in ['private int fd;', 'fd = -1;', 'private Closeable parent;', 'private boolean closed;', 'synchronized void attach(Closeable c)']) or constructor.index('security.checkWrite(fdObj)') > constructor.index('fd.attach(this)'):
        raise ValueError('Pinned runtime Java descriptor ownership differs')
    with zipfile.ZipFile(runtime / 'Contents/Home/jre/lib/rt.jar') as z:
        bytecode = z.read('java/io/FileDescriptor.class')
    if bytecode[:8] != bytes.fromhex('cafebabe00000034'):
        raise ValueError('Pinned runtime FileDescriptor class version differs')
    return {'src_archive_sha256': sha(archive), 'entries': {n: hashlib.sha256(v).hexdigest() for n, v in values.items()}, 'file_descriptor_class_sha256': hashlib.sha256(bytecode).hexdigest(), 'java_attachment_before_open': True, 'vendor_native_close_source_verified': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-clean', action='store_true', help='Require recorded source bytes at a clean Git commit')
    args = parser.parse_args(); verify_python(); compiler = verify_jdk(args.jdk)
    if args.output.exists() or args.output.is_symlink(): raise ValueError('New atomic output required')
    reference = ROOT / 'build/preference-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(reference) != REFERENCE_SHA: raise ValueError('Pinned actual audit27 reference required')
    sources = {str(p.relative_to(ROOT)): sha(p) for p in sorted(HERE.glob('*')) if p.is_file()}
    sources.update({str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'tools').glob('*.py'))})
    sources.update({str(p.relative_to(ROOT)): sha(p) for p in [ROOT / 'audit/jdk-lock.json', ROOT / 'audit/python-lock.json', ROOT / 'audit/runtime-lock.json']})
    initial_commit = execute(['/usr/bin/git', 'rev-parse', 'HEAD']).strip()
    dirty = bool(execute(['/usr/bin/git', 'status', '--porcelain']))
    if args.require_clean:
        if dirty: raise ValueError('Clean atomic experimental source required')
        for name, expected in sources.items():
            data = subprocess.check_output(['/usr/bin/git', 'show', initial_commit + ':' + name], cwd=ROOT, env=isolated_env())
            if hashlib.sha256(data).hexdigest() != expected: raise ValueError('Atomic source differs from Git')
    clang = Path(execute(['/usr/bin/xcrun', '--find', 'clang']).strip())
    sdk = Path(execute(['/usr/bin/xcrun', '--show-sdk-path']).strip())
    native_inputs = [clang, sdk / 'SDKSettings.json', sdk / 'usr/include/sys/acl.h', sdk / 'usr/include/sys/stdio.h', sdk / 'usr/include/sys/fcntl.h', sdk / 'usr/include/sys/unistd.h']
    native_input_hashes = {str(p): sha(p) for p in native_inputs}
    native_output_hashes = {}
    def compile_native(command):
        execute(command); native_output_hashes[str(command[-1])] = sha(command[-1])
    native_metadata = {'clang_sha256': sha(clang), 'sdk_settings_sha256': sha(sdk / 'SDKSettings.json'), 'acl_header_sha256': sha(sdk / 'usr/include/sys/acl.h'), 'rename_header_sha256': sha(sdk / 'usr/include/sys/stdio.h'), 'fcntl_header_sha256': sha(sdk / 'usr/include/sys/fcntl.h'), 'unistd_header_sha256': sha(sdk / 'usr/include/sys/unistd.h'), 'clang_version': execute([clang, '--version']).strip()}
    args.output.mkdir(parents=True); classes = args.output / 'classes'; classes.mkdir()
    run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(reference), '-d', str(classes)] + [str(HERE / name) for name in ['AtomicPreferenceFile.java', 'AtomicPreferenceObservation.java', 'NativeBindingObservation.java', 'AtomicFaultObservation.java', 'NativeLoadObservation.java', 'SuppressionObservation.java']])
    probe_hashes = {str(p.relative_to(classes)): sha(p) for p in classes.rglob('*.class')}
    with zipfile.ZipFile(reference) as archive:
        if set(probe_hashes) & set(archive.namelist()): raise ValueError('Atomic probes shadow product classes')
    source_gates = {}
    lock = runtime_manifest(); runtimes = []; libraries = {}; rows = []; negatives = []; faults = []; bindings = []; jni_loads = []; jni_functional = []; suppression_rows = []
    for folder, arch, cpu in [('arm64', 'aarch64', 'arm64'), ('x64', 'x64', 'x86_64')]:
        runtime = ROOT / ('build/logging-bundled-' + folder + '-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk')
        verify_runtime(runtime, lock['architectures'][arch]); runtimes.append((runtime, arch)); source_gates[arch] = runtime_source_gate(runtime); binaries = []
        for repeat in [1, 2]:
            directory = args.output / (arch + '-' + str(repeat)); directory.mkdir()
            library = directory / 'libAtomicPreference.dylib'
            command = [clang, '-target', cpu + '-apple-macos11.0', '-isysroot', sdk, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', '-fvisibility=hidden', '-dynamiclib', '-Wl,-install_name,@rpath/libAtomicPreference.dylib', '-I' + str(args.jdk / 'include'), '-I' + str(args.jdk / 'include/darwin'), HERE / 'atomic_file.c', '-o', library]
            compile_native(command); binaries.append(library)
        if sha(binaries[0]) != sha(binaries[1]): raise ValueError('Atomic native repeat differs')
        exports = execute(['/usr/bin/nm', '-gjU', binaries[0]]).splitlines()
        if sorted(exports) != ['_JNI_OnLoad', '_JNI_OnUnload']: raise ValueError('Native transaction functions exported')
        libraries[arch] = {'exports': exports, 'sha256': sha(binaries[0]), 'bytes': binaries[0].stat().st_size, 'repeated_bytes_equal': True, 'compile_command': list(map(str, command))}
        for mode in ['-Xint', '-Xcomp']:
            for mask in [0o000, 0o022, 0o077, 0o277]:
                with disposable('disposable-atomic-', args.output) as directory:
                    root = Path(directory).resolve(); setup(root)
                    argv = [runtime / 'Contents/Home/bin/java'] + JAVA_FLAGS + [mode, '-Xverify:all', '-Xms256m', '-Xmx256m', '-Djava.awt.headless=true', '-Dlog4j.defaultInitOverride=true', '-Dfixture.atomic.library=' + str(binaries[0].resolve()), '-Dfixture.directory=' + str(root), '-Dfixture.reference=' + str(reference.resolve()), '-cp', str(classes.resolve()) + ':' + str(reference.resolve()), 'atomicfixture.AtomicPreferenceObservation']
                    result = execute(argv, mask)
                    if result != RESULT: raise ValueError('Atomic result differs')
                    # Successful replacement must remove the original target ACL, not merely tighten mode bits.
                    acl_output = execute(['/bin/ls', '-led', root / 'acl-file'])
                    if len(acl_output.splitlines()) != 1 or '+' in acl_output.split()[0]:
                        raise ValueError('Atomic target ACL retained')
                    rows.append({'architecture': arch, 'mode': mode, 'umask': mask, 'result': result.strip()})
        def java_argv(library, root, mode, main, scenario=None):
            argv = [runtime / 'Contents/Home/bin/java'] + JAVA_FLAGS + [mode, '-Xverify:all', '-Xms256m', '-Xmx256m', '-Djava.awt.headless=true', '-Dfixture.atomic.library=' + str(library.resolve()), '-Dfixture.directory=' + str(root), '-Dfixture.reference=' + str(reference.resolve()), '-cp', str(classes.resolve()) + ':' + str(reference.resolve())]
            if scenario: argv += ['-Dfixture.scenario=' + scenario]
            return argv + ['atomicfixture.' + main]
        baseline_library = args.output / (arch + '-loader-baseline.dylib')
        baseline_command = list(command); baseline_command[baseline_command.index(HERE / 'atomic_file.c')] = HERE / 'load_baseline.c'; baseline_command[-1] = baseline_library
        compile_native(baseline_command)
        # No loader warnings are silently discarded. Compare exact output to a
        # no-op JNI_OnLoad control, separately from the functional regression.
        for mode in ['-Xint', '-Xcomp']:
            with disposable('jni-load-', args.output) as directory:
                base_argv = java_argv(baseline_library, Path(directory), mode, 'NativeLoadObservation')
                base_argv.insert(-1, '-Xcheck:jni')
                candidate_argv = java_argv(binaries[0], Path(directory), mode, 'NativeLoadObservation')
                candidate_argv.insert(-1, '-Xcheck:jni')
                baseline_output = execute(base_argv, 0o022); candidate_output = execute(candidate_argv, 0o022)
                if baseline_output != candidate_output or not baseline_output.endswith('PASS native load\n'):
                    raise ValueError('Candidate JNI load diagnostics differ from empty baseline')
                jni_loads.append({'architecture': arch, 'mode': mode, 'baseline_library_sha256': sha(baseline_library), 'stdout_sha256': hashlib.sha256(baseline_output.encode()).hexdigest(), 'warning_lines': baseline_output.splitlines()[:-1], 'umask': 0o022, 'scope': 'Loading only; not a full -Xcheck:jni functional qualification'})
        # Exercise begin, commit and abort through the full functional suite under
        # JNI checking; accept only the exact warning prefix from the empty control.
        with disposable('jni-functional-', args.output) as directory:
            root = Path(directory).resolve(); setup(root)
            argv = java_argv(binaries[0], root, '-Xint', 'AtomicPreferenceObservation'); argv.insert(-1, '-Xcheck:jni')
            output = execute(argv, 0o022)
            prefix = baseline_output[:-len('PASS native load\n')]
            if output != prefix + RESULT: raise ValueError('Functional JNI diagnostics differ from empty load control')
            jni_functional.append({'architecture': arch, 'mode': '-Xint', 'umask': 0o022, 'result': RESULT.strip(), 'warning_prefix_sha256': hashlib.sha256(prefix.encode()).hexdigest(), 'scope': 'Full functional suite; exact empty-loader warning prefix only'})
        stale_library = args.output / (arch + '-stale-no-onload.dylib')
        stale_command = list(command); stale_command[stale_command.index(HERE / 'atomic_file.c')] = HERE / 'stale_no_onload.c'; stale_command[-1] = stale_library; compile_native(stale_command)
        bad_abi_library = args.output / (arch + '-stale-bad-abi.dylib')
        bad_abi_command = list(command); bad_abi_command[bad_abi_command.index(HERE / 'atomic_file.c')] = HERE / 'stale_bad_abi.c'; bad_abi_command[-1] = bad_abi_library; compile_native(bad_abi_command)
        native = (HERE / 'atomic_file.c').read_text()
        mismatched = replace_once(native, '{"commit0", "(J)V",', '{"notAJavaMethod", "(J)V",')
        mismatch_folder = args.output / (arch + '-mismatch'); mismatch_folder.mkdir()
        mismatch_source = mismatch_folder / 'atomic_file.c'; mismatch_source.write_text(mismatched)
        mismatch_library = mismatch_folder / 'libAtomicPreference.dylib'
        mismatch_command = list(command); mismatch_command[mismatch_command.index(HERE / 'atomic_file.c')] = mismatch_source; mismatch_command[-1] = mismatch_library; compile_native(mismatch_command)
        for mode in ['-Xint', '-Xcomp']:
            for scenario in ['normal', 'missing', 'unset', 'mismatch', 'no-onload', 'bad-abi', 'deny-path', 'deny-fd']:
                library = bad_abi_library if scenario == 'bad-abi' else stale_library if scenario == 'no-onload' else mismatch_library if scenario == 'mismatch' else args.output / 'not-present.dylib' if scenario == 'missing' else binaries[0]
                with disposable('binding-', args.output) as directory:
                    argv = java_argv(library, Path(directory), mode, 'NativeBindingObservation', scenario)
                    if scenario == 'unset': argv = [v for v in argv if not str(v).startswith('-Dfixture.atomic.library=')]
                    checked_binding = scenario in ['normal', 'mismatch'] and mode == '-Xint'
                    if checked_binding: argv.insert(-1, '-Xcheck:jni')
                    output = execute(argv, 0o022)
                    binding_prefix = prefix if checked_binding else ''
                    if output != binding_prefix + 'PASS atomic binding ' + scenario + '\n': raise ValueError('Atomic binding differs')
                    bindings.append({'architecture': arch, 'mode': mode, 'scenario': scenario, 'umask': 0o022, 'jni_checked': checked_binding, 'result': output[len(binding_prefix):].strip(), 'library_sha256': sha(library) if library.exists() else None, 'mismatch_source_sha256': sha(mismatch_source) if scenario == 'mismatch' else None, 'stale_source_sha256': sha(HERE / 'stale_bad_abi.c') if scenario == 'bad-abi' else sha(HERE / 'stale_no_onload.c') if scenario == 'no-onload' else None})
        for mode in ['-Xint', '-Xcomp']:
            with disposable('suppression-', args.output) as directory:
                output = execute(java_argv(binaries[0], Path(directory), mode, 'SuppressionObservation'), 0o022)
                if output != 'PASS atomic suppression; cases=3; primary_preserved=true\n': raise ValueError('Suppression result differs')
                suppression_rows.append({'architecture': arch, 'mode': mode, 'umask': 0o022, 'result': output.strip()})
        rename = """do { value = s->target_present ? renameat(s->dirfd, s->temporary, s->dirfd, s->base)
            : renameatx_np(s->dirfd, s->temporary, s->dirfd, s->base, RENAME_EXCL); } while (value < 0 && errno == EINTR);"""
        rename_fail = replace_once(native, rename, 'value = -1; errno = EIO;')
        race = """int planted = openat(s->dirfd, s->base, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (planted < 0 || write(planted, "\\004\\005\\006", 3) != 3) { if (planted >= 0) close(planted); error = "fault-plant"; }
        else close(planted);
        """
        fault_variants = {
            'stat-recovered': replace_once(native, 'stat_fd(fd, &temporary) < 0 && stat_fd(fd, &temporary) < 0', '(errno = EIO, -1) < 0 && stat_fd(fd, &temporary) < 0'),
            'stat-leftover': replace_once(native, 'stat_fd(fd, &temporary) < 0 && stat_fd(fd, &temporary) < 0', '(errno = EIO, -1) < 0 && (errno = EIO, -1) < 0'),
            'mode': replace_once(native, 'mode = fchmod(fd, 0600)', 'mode = (errno = EACCES, -1)'),
            'dup': replace_once(native, 's->verify_fd = fcntl(fd, F_DUPFD_CLOEXEC, 0)', 's->verify_fd = (errno = EMFILE, -1)'),
            'rename': rename_fail,
            'remote-sync-ok': replace_once(native, 'else if (!(fs.f_flags & MNT_LOCAL))', 'else if (1)'),
            'statfs': replace_once(native, 'value = fstatfs(s->verify_fd, &fs)', 'value = (errno = EIO, -1)'),
            'remote-sync': replace_once(replace_once(native, 'else if (!(fs.f_flags & MNT_LOCAL))', 'else if (1)'), 'value = fsync(s->verify_fd)', 'value = (errno = EIO, -1)'),
            'rename-cleanup': replace_once(rename_fail, 'if (!s->created) return 1;', 'if (s->created) return 0;'),
            'close-committed': replace_once(native, 'if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;', 'if (s->verify_fd >= 0) { close(s->verify_fd); issues |= 2; }'),
            'rename-exclusive': replace_once(native, rename, race + rename),
        }
        for scenario, changed in fault_variants.items():
            fault_folder = args.output / (arch + '-fault-' + scenario); fault_folder.mkdir()
            fault_source = fault_folder / 'atomic_file.c'; fault_source.write_text(changed)
            fault_library = fault_folder / 'libAtomicPreference.dylib'
            fault_command = list(command); fault_command[fault_command.index(HERE / 'atomic_file.c')] = fault_source; fault_command[-1] = fault_library; compile_native(fault_command)
            for mode in ['-Xint', '-Xcomp']:
                with disposable('fault-', fault_folder) as directory:
                    argv = java_argv(fault_library, Path(directory), mode, 'AtomicFaultObservation', scenario)
                    checked = scenario == 'rename' and mode == '-Xint'
                    if checked: argv.insert(-1, '-Xcheck:jni')
                    output = execute(argv, 0o022)
                    fault_prefix = prefix if checked else ''
                    if output != fault_prefix + 'PASS atomic fault ' + scenario + '; repetitions=32; fd_delta=0; gc_delta=0\n': raise ValueError('Atomic fault differs')
                    faults.append({'architecture': arch, 'mode': mode, 'scenario': scenario, 'umask': 0o022, 'jni_checked': checked, 'result': output[len(fault_prefix):].strip(), 'source_sha256': sha(fault_source), 'library_sha256': sha(fault_library)})
        # The planted target is inserted inside native after the identity pre-check,
        # so this control genuinely reaches the RENAME_EXCL protection.
        exclusive_mutant = replace_once(fault_variants['rename-exclusive'], ', RENAME_EXCL);', ', 0);')
        exclusive_folder = args.output / (arch + '-negative-no-rename-excl'); exclusive_folder.mkdir()
        exclusive_source = exclusive_folder / 'atomic_file.c'; exclusive_source.write_text(exclusive_mutant)
        exclusive_library = exclusive_folder / 'libAtomicPreference.dylib'
        exclusive_command = list(command); exclusive_command[exclusive_command.index(HERE / 'atomic_file.c')] = exclusive_source; exclusive_command[-1] = exclusive_library; compile_native(exclusive_command)
        with disposable('exclusive-negative-', exclusive_folder) as directory:
            saved = os.umask(0o022)
            try: result = subprocess.run(list(map(str, java_argv(exclusive_library, Path(directory), '-Xint', 'AtomicFaultObservation', 'rename-exclusive'))), env=isolated_env(), capture_output=True, timeout=120, cwd=ROOT)
            finally: os.umask(saved)
            expected = b'Exception in thread "main" java.lang.AssertionError: atomic-fault:failure-code\n'
            frames = result.stderr[len(expected):].decode() if result.stderr.startswith(expected) else ''
            if result.returncode != 1 or result.stdout or not re.fullmatch(r'(?:\tat atomicfixture\.AtomicFaultObservation\.(?:check|run|main)\(AtomicFaultObservation\.java:\d+\)\n){3}', frames):
                raise ValueError('Atomic exclusive negative differs; raw withheld')
            negatives.append({'architecture': arch, 'mode': '-Xint', 'mutation': 'no-rename-excl', 'umask': 0o022, 'assertion_code': 'atomic-fault:failure-code', 'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(), 'library_sha256': sha(exclusive_library), 'mutant_source_sha256': sha(exclusive_source)})
        target_check = '''if (!error && ((s->target_present && (target_exists < 0 || !target_ok(&target) || target.st_dev != s->target_device || target.st_ino != s->target_inode))
        || (!s->target_present && (target_exists == 0 || errno != ENOENT)))) error = "atomic-target-changed";'''
        temp_check = '''if (!temporary_ok(s) || stat_name(s->dirfd, s->temporary, &temporary) < 0
        || temporary.st_dev != s->temporary_device || temporary.st_ino != s->temporary_inode) error = "atomic-temporary-changed";'''
        variants = {
            'abort-deletes-target': (replace_once(native, 'unlinkat(s->dirfd, s->temporary, 0)', 'unlinkat(s->dirfd, s->base, 0)'), 'failure-original-present'),
            'abort-without-identity': (replace_once(native, 'if (!S_ISREG(st.st_mode) || st.st_uid != geteuid() || st.st_dev != s->temporary_device || st.st_ino != s->temporary_inode) return 0;', ''), 'foreign-temporary-not-deleted'),
            'skip-target-identity': (replace_once(native, target_check, '(void)target_exists;'), 'concurrent-target-rejected'),
            'skip-temporary-identity': (replace_once(native, temp_check, '(void)temporary;'), 'temporary-swap-rejected'),
            'skip-parent-policy': (replace_once(native, 'if (!parent_ok(s->dirfd))', 'if (0)'), 'rejection-code'),
            'skip-begin-write-check': (replace_once(native, 'if (!target_writable(s))', 'if (0)'), 'rejection-code'),
            'skip-commit-write-check': (replace_once(native, 'if (!error && s->target_present && !target_writable(s))', 'if (0)'), 'commit-readonly-rejected'),
            'skip-target-write-check': (replace_once(native, 'return value == 0;\n}\n\nstatic int temporary_ok', 'return 1;\n}\n\nstatic int temporary_ok'), 'rejection-code'),
            'allow-group-writable-parent': (replace_once(native, '!(st.st_mode & 0022)', '!(st.st_mode & 0002)'), 'rejection-code'),
            'allow-parent-allow-acl': (replace_once(native, '|| tag == ACL_EXTENDED_ALLOW', ''), 'rejection-code'),
            'allow-parent-inherit-acl': (replace_once(native, '|| acl_get_flag_np(flags, ACL_ENTRY_FILE_INHERIT) != 0', ''), 'rejection-code'),
            'leak-native-session-fd': (replace_once(native, 'if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;', ''), 'fd-lifetime'),
        }
        for name, (changed, code) in variants.items():
            folder = args.output / (arch + '-negative-' + name); folder.mkdir()
            source = folder / 'atomic_file.c'; source.write_text(changed); library = folder / 'libAtomicPreference.dylib'
            altered = list(command); altered[altered.index(HERE / 'atomic_file.c')] = source; altered[-1] = library; compile_native(altered)
            with disposable('negative-atomic-', folder) as directory:
                root = Path(directory).resolve(); setup(root)
                argv = [runtime / 'Contents/Home/bin/java'] + JAVA_FLAGS + ['-Xint', '-Xverify:all', '-Xms256m', '-Xmx256m', '-Djava.awt.headless=true', '-Dlog4j.defaultInitOverride=true', '-Dfixture.atomic.library=' + str(library.resolve()), '-Dfixture.directory=' + str(root), '-Dfixture.reference=' + str(reference.resolve()), '-cp', str(classes.resolve()) + ':' + str(reference.resolve()), 'atomicfixture.AtomicPreferenceObservation']
                saved = os.umask(0o022)
                try: result = subprocess.run(list(map(str, argv)), env=isolated_env(), capture_output=True, timeout=120, cwd=ROOT)
                finally: os.umask(saved)
                expected = ('Exception in thread "main" java.lang.AssertionError: atomic-preference:' + code + '\n').encode()
                frames = result.stderr[len(expected):].decode('utf-8') if result.stderr.startswith(expected) else ''
                if result.returncode != 1 or result.stdout or not re.fullmatch(r'(?:\tat atomicfixture\.AtomicPreferenceObservation\.(?:check|rejected|main)\(AtomicPreferenceObservation\.java:\d+\)\n){2,3}', frames):
                    raise ValueError('Atomic negative failed unexpectedly; raw withheld')
                negatives.append({'architecture': arch, 'mode': '-Xint', 'mutation': name, 'assertion_code': code, 'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(), 'library_sha256': sha(library), 'mutant_source_sha256': sha(source)})
    if len(rows) != 16 or len(negatives) != 26 or len(faults) != 44 or len(bindings) != 32 or len(jni_loads) != 4 or len(jni_functional) != 2 or len(suppression_rows) != 4: raise ValueError('Atomic matrix incomplete')
    for runtime, arch in runtimes:
        verify_runtime(runtime, lock['architectures'][arch])
        if runtime_source_gate(runtime) != source_gates[arch]: raise ValueError('Runtime source gate changed')
    if any(sha(Path(path)) != expected for path, expected in native_input_hashes.items()) or any(sha(Path(path)) != expected for path, expected in native_output_hashes.items()): raise ValueError('Native tools or output bytes changed')
    verify_jdk(args.jdk)
    if sha(reference) != REFERENCE_SHA or any(sha(ROOT / name) != value for name, value in sources.items()) or probe_hashes != {str(p.relative_to(classes)): sha(p) for p in classes.rglob('*.class')} or execute(['/usr/bin/git', 'rev-parse', 'HEAD']).strip() != initial_commit or bool(execute(['/usr/bin/git', 'status', '--porcelain'])) != dirty:
        raise ValueError('Atomic experiment inputs changed')
    record = {'qualification': False, 'clean_experimental_execution': args.require_clean and not dirty, 'runtime_java_source_gates': source_gates, 'native_outputs': native_output_hashes, 'source_commit': initial_commit, 'source_dirty': dirty, 'scope': 'Nonshipping atomic-save development experiment; disposable files only', 'sources': sources, 'compiler_tree_sha256': compiler['tree_sha256'], 'native_tool_metadata': native_metadata, 'reference_sha256': REFERENCE_SHA, 'probe_hashes': probe_hashes, 'libraries': libraries, 'runtime_trees': {arch: lock['architectures'][arch]['tree_sha256'] for _, arch in runtimes}, 'observations': rows, 'negative_controls': negatives, 'fault_observations': faults, 'binding_observations': bindings, 'jni_load_controls': jni_loads, 'jni_functional_controls': jni_functional, 'suppression_observations': suppression_rows, 'limits': ['Not integrated into product; no full candidate regression or release qualification', 'Fault-injected source variants are not actual filesystem failures; complete native ownership qualification remains incomplete', 'Metadata/ACL/hardlink behavior intentionally differs from inplace saving', 'Remote fsync branch has an injected error test only; real remote filesystem and power-loss durability unqualified; no encryption claim', 'Cross-uid/root/same-uid attackers and parent changes remain unqualified', 'Native compiler metadata not a full toolchain lock', 'x64 is Rosetta, not physical Intel; GUI/profiles/controllers untested']}
    def sanitized(value):
        if isinstance(value, str):
            for prefix, label in sorted([(str(ROOT.resolve()), '<repo>'), (str(args.jdk.resolve()), '<java-compiler>'), (str(sdk.resolve()), '<sdk>'), (str(clang.parent.resolve()), '<clang-bin>')], key=lambda entry: -len(entry[0])): value = value.replace(prefix, label)
            return value
        if isinstance(value, dict): return {sanitized(key): sanitized(item) for key, item in value.items()}
        if isinstance(value, list): return [sanitized(item) for item in value]
        return value
    record = sanitized(record)
    (args.output / 'observations.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print('PASS nonshipping atomic preference experiment; runs=16; cases=37; native_negative_controls=26; fault_runs=44; binding_runs=32; jni_load_controls=4; jni_functional_controls=2; suppression_runs=4')

if __name__ == '__main__': main()
