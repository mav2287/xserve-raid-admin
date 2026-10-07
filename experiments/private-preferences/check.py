#!/usr/bin/env python3
"""Observe a nonshipping Darwin JNI experiment on disposable local files only."""
import argparse
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
sys.path.insert(0, str(ROOT / 'tools'))
from audit_support import JAVA_FLAGS, isolated_env, run_jdk, sha, verify_jdk, verify_python
from runtime import runtime_manifest, verify_runtime

HERE = Path(__file__).resolve().parent
REFERENCE_SHA = 'e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62'
RESULT = 'PASS private descriptor experiment; cases=34; bytes_interrupts_preserved=true; private_modes=true; link_acl_rejections=true; fd_delta=0\n'

def execute(argv, *, mask=None, timeout=120):
    saved = os.umask(mask) if mask is not None else None
    try:
        value = subprocess.run(list(map(str, argv)), env=isolated_env(), capture_output=True, timeout=timeout)
    finally:
        if saved is not None:
            os.umask(saved)
    if value.returncode or value.stderr:
        # Fixed codes only: no arbitrary native/JVM diagnostics or filesystem names.
        raise RuntimeError('private-experiment-subprocess-failed; output withheld')
    return value.stdout.decode('utf-8')

def setup(root):
    (root / 'directory').mkdir()
    os.mkfifo(root / 'fifo', 0o600)
    (root / 'acl-file').write_bytes(bytes([9, 8, 7]))
    (root / 'acl-file').chmod(0o644)
    (root / 'acl-parent').mkdir()
    execute(['/bin/chmod', '+a', 'everyone allow read', root / 'acl-file'])
    execute(['/bin/chmod', '+a', 'everyone allow read,file_inherit,directory_inherit', root / 'acl-parent'])

def replace_once(value, old, new):
    if value.count(old) != 1:
        raise ValueError('Native mutation target is not unique')
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
    parser.add_argument('--require-clean', action='store_true', help='Require all recorded source bytes at a clean Git commit')
    args = parser.parse_args()
    verify_python()
    compiler = verify_jdk(args.jdk)
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('New experiment directory required')
    reference = ROOT / 'build/preference-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    if sha(reference) != REFERENCE_SHA:
        raise ValueError('Pinned audit27 reference required')
    sources = {str(p.relative_to(ROOT)): sha(p) for p in sorted(HERE.glob('*')) if p.is_file()}
    sources.update({str(p.relative_to(ROOT)): sha(p) for p in [ROOT / 'tools/audit_support.py', ROOT / 'tools/runtime.py', ROOT / 'audit/runtime-lock.json', ROOT / 'audit/jdk-lock.json', ROOT / 'audit/python-lock.json']})
    commit = execute(['/usr/bin/git', 'rev-parse', 'HEAD']).strip()
    dirty = bool(execute(['/usr/bin/git', 'status', '--porcelain']))
    if args.require_clean:
        if dirty:
            raise ValueError('Clean experimental source required')
        for name, expected in sources.items():
            value = subprocess.check_output(['/usr/bin/git', 'show', commit + ':' + name], cwd=ROOT, env=isolated_env())
            if hashlib.sha256(value).hexdigest() != expected:
                raise ValueError('Experimental source differs from recorded Git commit')
    clang = Path(execute(['/usr/bin/xcrun', '--find', 'clang']).strip())
    sdk = Path(execute(['/usr/bin/xcrun', '--show-sdk-path']).strip())
    native_tools = {'clang_sha256': sha(clang), 'clang_version': execute([clang, '--version']).strip(), 'sdk_settings_sha256': sha(sdk / 'SDKSettings.json'), 'acl_header_sha256': sha(sdk / 'usr/include/sys/acl.h')}
    args.output.mkdir(parents=True)
    classes = args.output / 'classes'; classes.mkdir()
    run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(reference), '-d', str(classes)] + [str(HERE / n) for n in ['PrivatePreferenceFile.java', 'PrivatePreferenceObservation.java']])
    hashes = {str(p.relative_to(classes)): sha(p) for p in classes.rglob('*.class')}
    with zipfile.ZipFile(reference) as z:
        if set(hashes) & set(z.namelist()):
            raise ValueError('Experiment shadows product classes')
    lock = runtime_manifest(); rows = []; libraries = {}; runtimes = []; negatives = []; source_gates = {}; library_paths = {}
    for folder, arch, cpu in [('arm64', 'aarch64', 'arm64'), ('x64', 'x64', 'x86_64')]:
        runtime = ROOT / ('build/logging-bundled-' + folder + '-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk')
        verify_runtime(runtime, lock['architectures'][arch]); runtimes.append((runtime, arch)); source_gates[arch] = runtime_source_gate(runtime)
        binaries = []; commands = []
        for repeat in (1, 2):
            directory = args.output / (arch + '-' + str(repeat)); directory.mkdir()
            library = directory / 'libPrivatePreference.dylib'
            command = [clang, '-target', cpu + '-apple-macos11.0', '-isysroot', sdk, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', '-fvisibility=hidden', '-dynamiclib', '-Wl,-install_name,@rpath/libPrivatePreference.dylib', '-I' + str(args.jdk / 'include'), '-I' + str(args.jdk / 'include/darwin'), HERE / 'private_file.c', '-o', library]
            execute(command); binaries.append(library); commands.append(list(map(str, command)))
        if sha(binaries[0]) != sha(binaries[1]):
            raise ValueError('Native repeated build differs')
        library_paths[arch] = binaries
        libraries[arch] = {'sha256': sha(binaries[0]), 'bytes': binaries[0].stat().st_size, 'build_commands': commands, 'repeated_bytes_equal': True}
        for mode in ['-Xint', '-Xcomp']:
            for mask in [0o022, 0o077, 0o277]:
                with tempfile.TemporaryDirectory(prefix='disposable-', dir=args.output) as directory:
                    root = Path(directory).resolve(); setup(root)
                    argv = [runtime / 'Contents/Home/bin/java'] + JAVA_FLAGS + [mode, '-Xverify:all', '-Xms256m', '-Xmx256m', '-Djava.awt.headless=true', '-Dlog4j.defaultInitOverride=true', '-Dfixture.private.library=' + str(binaries[0].resolve()), '-Dfixture.directory=' + str(root), '-Dfixture.reference=' + str(reference.resolve()), '-cp', str(classes.resolve()) + ':' + str(reference.resolve()), 'privatefixture.PrivatePreferenceObservation']
                    result = execute(argv, mask=mask)
                    if result != RESULT:
                        raise ValueError('Experiment result differs')
                    names = []
                    for i in range(5):
                        old = sorted(os.listdir(os.fsencode(root / 'original-names' / ('case-' + str(i)))))
                        new = sorted(os.listdir(os.fsencode(root / 'candidate-names' / ('case-' + str(i)))))
                        if len(old) != 1 or old != new:
                            raise ValueError('Native directory-entry byte parity differs')
                        names.append(old[0].hex())
                    if names != ['6173636969', 'e697a5e69cace8aa9e', 'c3a9', '65cc81', 'f09f9883']:
                        raise ValueError('APFS raw input filename preservation differs')
                    rows.append({'architecture': arch, 'mode': mode, 'umask': mask, 'phase': 'differential', 'result': result.strip(), 'filename_bytes_hex': names, 'argv': list(map(str, argv))})
            for operation in ['deny-descriptor', 'deny-path', 'missing-library', 'unset-library']:
                with tempfile.TemporaryDirectory(prefix='permission-', dir=args.output) as directory:
                    library = binaries[0] if operation != 'missing-library' else args.output / 'not-present.dylib'
                    argv = [runtime / 'Contents/Home/bin/java'] + JAVA_FLAGS + [mode, '-Xverify:all', '-Xms256m', '-Xmx256m', '-Djava.awt.headless=true', '-Dfixture.private.library=' + str(library.resolve()), '-Dfixture.directory=' + str(Path(directory).resolve()), '-cp', str(classes.resolve()) + ':' + str(reference.resolve()), 'privatefixture.PrivatePreferenceObservation', operation]
                    if operation == 'unset-library':
                        argv = [v for v in argv if not str(v).startswith('-Dfixture.private.library=')]
                    result = execute(argv, mask=0o022)
                    if result != 'PASS private descriptor ' + operation + '; bytes_modes_unchanged=true; fd_delta=0\n':
                        raise ValueError('Descriptor denial result differs')
                    rows.append({'architecture': arch, 'mode': mode, 'phase': operation, 'result': result.strip(), 'argv': list(map(str, argv))})
        native = (HERE / 'private_file.c').read_text()
        variants = {
            'early-truncation': (replace_once(native, 'O_WRONLY | O_CREAT | O_NOFOLLOW', 'O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW'), 'hardlink-bytes'),
            'follow-final-symlink': (replace_once(native, ' | O_NOFOLLOW', ''), 'policy-not-rejected'),
            'allow-hardlink': (replace_once(native, '&& st->st_nlink == 1', ''), 'policy-not-rejected'),
            'keep-public-mode': (replace_once(replace_once(native, 'result = fchmod(fd, 0600)', 'result = (fd >= 0 ? 0 : -1)'), '(st.st_mode & 07777) != 0600', '0'), 'private-mode'),
            'leak-rejected-descriptor': (replace_once(native, 'if (error) { close(fd); fail', 'if (error) { fail'), 'rejection-close'),
            'skip-parent-acl': (replace_once(native, 'if (!acl_policy(dirfd, 1))', 'if (0)'), 'policy-code'),
            'publish-before-validation': (replace_once(native, 'struct stat st;\n    const char *error', '(*env)->SetIntField(env, descriptor, fd_field, fd);\n    struct stat st;\n    const char *error'), 'suppressed-close'),
            'keep-nonblock': (replace_once(replace_once(native, 'flags & ~O_NONBLOCK', 'flags'), '(get_flags(fd, F_GETFL) & O_NONBLOCK)', '0'), 'descriptor-flags'),
            'drop-cloexec': (replace_once(native, ' | O_NONBLOCK | O_CLOEXEC, 0600', ' | O_NONBLOCK, 0600'), 'descriptor-flags'),
        }
        for name, (changed, code) in variants.items():
            if changed == native:
                raise ValueError('Native mutation absent')
            folder = args.output / (arch + '-negative-' + name); folder.mkdir()
            source = folder / 'private_file.c'; source.write_text(changed)
            library = folder / 'libPrivatePreference.dylib'
            mutant_command = list(command)
            mutant_command[mutant_command.index(HERE / 'private_file.c')] = source
            mutant_command[-1] = library
            execute(mutant_command)
            with tempfile.TemporaryDirectory(prefix='negative-', dir=folder) as directory:
                root = Path(directory).resolve(); setup(root)
                argv = [runtime / 'Contents/Home/bin/java'] + JAVA_FLAGS + ['-Xint', '-Xverify:all', '-Xms256m', '-Xmx256m', '-Djava.awt.headless=true', '-Dlog4j.defaultInitOverride=true', '-Dfixture.private.library=' + str(library.resolve()), '-Dfixture.directory=' + str(root), '-Dfixture.reference=' + str(reference.resolve()), '-cp', str(classes.resolve()) + ':' + str(reference.resolve()), 'privatefixture.PrivatePreferenceObservation']
                saved = os.umask(0o022)
                try:
                    result = subprocess.run(list(map(str, argv)), env=isolated_env(), capture_output=True, timeout=120)
                finally:
                    os.umask(saved)
                expected = ('Exception in thread "main" java.lang.AssertionError: private-descriptor:' + code + '\n').encode()
                frames = result.stderr[len(expected):].decode('utf-8') if result.stderr.startswith(expected) else ''
                if result.returncode != 1 or result.stdout or not frames or not re.fullmatch(r'(?:\tat privatefixture\.PrivatePreferenceObservation\.(?:check|rejected|compare|main)\(PrivatePreferenceObservation\.java:\d+\)\n){2,3}', frames):
                    raise ValueError('Native negative failed unexpectedly; raw output withheld')
                negatives.append({'architecture': arch, 'mode': '-Xint', 'mutation': name, 'assertion_code': code, 'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(), 'library_sha256': sha(library), 'mutant_source_sha256': sha(source), 'result': 'expected differential assertion', 'argv': list(map(str, argv))})
    for runtime, arch in runtimes:
        verify_runtime(runtime, lock['architectures'][arch])
        if runtime_source_gate(runtime) != source_gates[arch] or any(sha(p) != libraries[arch]['sha256'] for p in library_paths[arch]):
            raise ValueError('Runtime sources or native libraries changed')
    verify_jdk(args.jdk)
    if sha(reference) != REFERENCE_SHA or any(sha(ROOT / n) != value for n, value in sources.items()) or hashes != {str(p.relative_to(classes)): sha(p) for p in classes.rglob('*.class')} or execute(['/usr/bin/git', 'rev-parse', 'HEAD']).strip() != commit or bool(execute(['/usr/bin/git', 'status', '--porcelain'])) != dirty:
        raise ValueError('Experiment inputs changed')
    if len(rows) != 28 or len(negatives) != 18:
        raise ValueError('Experiment execution count differs')
    record = {'qualification': False, 'scope': 'Nonshipping descriptor experiment; disposable local files only', 'source_commit': commit, 'source_dirty': dirty, 'sources': sources, 'compiler_tree_sha256': compiler['tree_sha256'], 'native_tool_metadata': native_tools, 'reference_sha256': REFERENCE_SHA, 'probe_hashes': hashes, 'libraries': libraries, 'runtime_trees': {arch: lock['architectures'][arch]['tree_sha256'] for _, arch in runtimes}, 'observations': rows, 'negative_controls': negatives, 'limits': ['No product integration or full regression qualification', 'Final component protected; parent components not secured against hostile filesystem changes', 'Same-user concurrent chmod/link/ACL modification not prevented', 'Nonempty ACLs refused rather than silently removed', 'No actual foreign-owner file or filesystem/close error injection', 'JNI FileDescriptor field bound only by these pinned runtime executions', 'No atomic-save/fsync/encryption; original serialization failure output preserved', 'Native tool metadata is not a complete locked toolchain', 'x64 execution is Rosetta, not physical Intel; native GUI and controllers untested']}
    record['limits'] += ['Other users may retain descriptors opened before tightening mode', 'Rejected existing files would be silently retried by the original store handler; not integrated', 'Rejection after creation may leave an empty private file', 'Parent open requires directory read access; search-only parent behavior not yet covered']
    record['runtime_java_source_gates'] = source_gates
    record['clean_experimental_execution'] = args.require_clean and not dirty
    record['filesystem'] = 'apfs (asserted in every JVM run); other filesystems unqualified'
    record['limits'] = [v for v in record['limits'] if v != 'JNI FileDescriptor field bound only by these pinned runtime executions']
    record['limits'].append('Vendor native fileClose/initIDs not source-verified; field invalidation observed, reuse close tests Java idempotence; early publish mutant demonstrates a suppressed double-close error')
    def sanitized(value):
        if isinstance(value, str):
            for prefix, label in sorted([(str(ROOT.resolve()), '<repo>'), (str(args.jdk.resolve()), '<java-compiler>'), (str(sdk.resolve()), '<sdk>'), (str(clang.parent.resolve()), '<clang-bin>')], key=lambda v: -len(v[0])):
                value = value.replace(prefix, label)
            return value
        if isinstance(value, dict): return {k: sanitized(v) for k, v in value.items()}
        if isinstance(value, list): return [sanitized(v) for v in value]
        return value
    record = sanitized(record)
    (args.output / 'observations.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print('PASS nonshipping private descriptor experiment; differential_runs=12; cases=34; denial_and_library_runs=16; negative_controls=18')

if __name__ == '__main__':
    main()
