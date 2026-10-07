#!/usr/bin/env python3
"""Additive, pinned synthetic credential boundary evidence; never starts the application."""
import argparse, hashlib, json, platform, resource, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_support import JAVA_FLAGS, isolated_env, sha, verify_jdk, verify_python, run_jdk, tree, modes
from inventory import disassemble_entries
from class_patch import ClassFile, u2

ORIGINAL = '5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
PRODUCT = 'bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e'
NATIVE = {'aarch64': '2a402a2e2cd98e22fc31c9c4499c75b720d06cbf2826e2bb9aa0c9d77a872284', 'x64': '2485d8f66b2c480a94d309ba1f16028f1fa1e0edb957f85063eb28a107834f42'}
MANIFESTS = {'aarch64': '6a4c095ecb82d8a8cccf57c5594c48f35fe35cad92089f1a623b8f21203c2314', 'x64': '420730b109f7c2015728e9c543fc2102db4a9918b985c774dce44d99dd76594b'}
FIELDS = {'managementPassword', 'managementPasswordSaved', 'monitoringPassword'}
ACCESSORS = {'get' + n[0].upper() + n[1:] for n in FIELDS} | {'set' + n[0].upper() + n[1:] for n in FIELDS}
SELECTED = ['com/apple/xsr/' + n + '.class' for n in ['SOMLocalizer', 'DefaultSystemRegistry', 'SystemRegistry', 'SystemMonitorController$ForgetPasswordAction', 'SystemMonitorController$ManagementAuthenticationListener', 'SystemMonitorController$ManagementSessionAuthenticationListener', 'Utilities', 'som/RaidSystem', 'som/RaidSystemAgent', 'som/AbstractSystemElement']]
SELECTED += ['com/apple/util/prefs/' + n + '.class' for n in ['Preferences', 'FileBasedPreferences']]
SELECTED += ['com/apple/net/acp/SimpleCryptCoder.class']

def trace(jdk, jar):
    rows = []; count = 0; references = []; named_strings = []; accessors = []
    with zipfile.ZipFile(jar) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith('.class'): continue
            count += 1; cls = ClassFile(archive.read(name))
            for index, (tag, data) in cls.pool.items():
                if tag == 9:
                    _, target = cls.pool[u2(data, 2)]; field = cls.text(u2(target, 0))
                    if field in FIELDS:
                        _, owner = cls.pool[u2(data, 0)]
                        references.append({'class': name, 'owner': cls.text(u2(owner, 0)), 'field': field})
                if tag in (10, 11):
                    _, target = cls.pool[u2(data, 2)]; method_name = cls.text(u2(target, 0))
                    if method_name in ACCESSORS:
                        _, owner = cls.pool[u2(data, 0)]
                        accessors.append({'class': name, 'owner': cls.text(u2(owner, 0)), 'method': method_name})
                if tag == 8:
                    _, value = cls.pool[u2(data, 0)]
                    if value in {n.encode('ascii') for n in FIELDS}: named_strings.append({'class': name, 'field_name_literal': value.decode('ascii')})
        for name in SELECTED:
            data = archive.read(name); cls = ClassFile(data)
            text = disassemble_entries(jdk, jar, [name]); method = None; instructions = []
            for line in text.splitlines():
                if (' = ' not in line and re.match(r'^  [^ ].*\(.*\).*;$', line)) or line == '  static {};':
                    method = {'signature': line.strip(), 'instructions': []}; instructions.append(method)
                if method and ('// Field ' in line or '// Method ' in line or '// InterfaceMethod ' in line):
                    method['instructions'].append(line.strip())
                if method and '// String ' in line and line.split('// String ', 1)[1] in {'Attributes', 'Rate', 'Name', 'IPAddress', 'Systems'}:
                    method['instructions'].append(line.strip())
            rows.append({'class': name, 'sha256': hashlib.sha256(data).hexdigest(), 'xor_instruction_count': len(re.findall(r'^\s+\d+: ixor\b', text, re.M)), 'fields': [{'name': f['name'], 'access': f['access'], 'descriptor': f['descriptor']} for f in cls.fields if f['name'] in FIELDS], 'methods': instructions})
    return {'jar_sha256': sha(jar), 'class_count': count, 'field_constant_pool_references': references, 'accessor_constant_pool_references': accessors, 'exact_field_name_string_constants': named_strings, 'selected_bytecode': rows, 'limits': 'Constant-pool references are not execution evidence; assembled reflection names are not excluded. String values other than fixed schema keys are omitted.'}

def no_core(): resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--jdk', type=Path, required=True); p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    if not sys.flags.isolated or not sys.flags.no_site: raise ValueError('Use Python -I -S')
    verify_python(); verify_jdk(a.jdk)
    out = a.output.absolute()
    if out.exists() or out.is_symlink() or out.parent.resolve() != (ROOT / 'build').resolve() or not out.name.startswith('credential-boundary-'): raise ValueError('Fresh direct build/credential-boundary-* output required')
    original = ROOT / 'original/RAID_Admin_original.jar'
    packages = {arch: ROOT / ('build/secure-release-' + arch + '-6/RAID Admin.app') for arch in NATIVE}
    for arch, app in packages.items():
        if sha(app / 'Contents/Resources/RAID_Admin.jar') != PRODUCT or sha(app / 'Contents/Frameworks/libPrivatePreference.dylib') != NATIVE[arch]: raise ValueError('Product identity differs')
    if sha(original) != ORIGINAL or original.stat().st_mode & 0o777 != 0o444: raise ValueError('Original identity differs')
    from runtime import verify_runtime, runtime_manifest, directory_modes
    def verify_packages():
        for arch, app in packages.items():
            if sha(app.parent / 'provenance.json') != MANIFESTS[arch]: raise ValueError('Frozen package manifest identity differs')
            manifest = json.loads((app.parent / 'provenance.json').read_bytes())
            if tree(app) != manifest['files'] or modes(app) != manifest['file_modes'] or directory_modes(app) != manifest['directory_modes']: raise ValueError('Frozen package changed')
            verify_runtime(app / 'Contents/PlugIns/Runtime.jdk', runtime_manifest()['architectures'][arch])
    verify_packages()
    sources = [ROOT / 'tests/java/credentialfixture/CredentialPersistenceObservation.java', ROOT / 'modernization/private-preferences/tests/AtomicCallerObservation.java', Path(__file__)]
    bound_inputs = sources + [ROOT / 'tools' / n for n in ['audit_support.py', 'inventory.py', 'class_patch.py', 'runtime.py']] + [ROOT / 'audit' / n for n in ['jdk-lock.json', 'runtime-lock.json', 'python-lock.json']]
    initial = {str(s.relative_to(ROOT)): sha(s) for s in bound_inputs}
    commit = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=ROOT, env=isolated_env()).decode().strip()
    if subprocess.check_output(['/usr/bin/git', 'status', '--porcelain'], cwd=ROOT, env=isolated_env()): raise ValueError('Clean committed fixture required')
    out.mkdir(parents=True); classes = out / 'classes'; classes.mkdir()
    run_jdk(a.jdk, 'javac', ['-source', '8', '-target', '8', '-d', str(classes)] + [str(s) for s in sources[:2]])
    record = {'fixture_commit': commit, 'inputs': initial, 'host': {'python_machine': platform.machine(), 'macos_version': subprocess.check_output(['/usr/bin/sw_vers','-productVersion'], env=isolated_env()).decode().strip()}, 'package_manifest_sha256': MANIFESTS, 'compiled_classes': {str(f.relative_to(classes)): sha(f) for f in sorted(classes.rglob('*.class'))}, 'original': trace(a.jdk, original), 'product': trace(a.jdk, packages['aarch64'] / 'Contents/Resources/RAID_Admin.jar'), 'runs': [], 'scope': 'Actual SOMLocalizer and model flag/getter methods; actual explicitly named file backend and cross-reader XML roundtrips. Constructors for model/agent are bypassed. Registry/factory/UI/authentication/startup are not executed.'}
    target = 'com/apple/xsr/SOMLocalizer.class'
    def mutate(source, destination):
        with zipfile.ZipFile(source) as before, zipfile.ZipFile(destination, 'w') as after:
            for name in before.namelist():
                data = before.read(name)
                if name == target:
                    needle = b'getMonitoringPassword'; replacement = b'getManagementPassword'
                    if data.count(needle) != 1 or len(needle) != len(replacement): raise ValueError('Mutation is not unique')
                    data = data.replace(needle, replacement)
                after.writestr(name, data)
        with zipfile.ZipFile(source) as before, zipfile.ZipFile(destination) as after:
            if before.namelist() != after.namelist() or [n for n in before.namelist() if before.read(n) != after.read(n)] != [target]: raise ValueError('Mutation scope differs')
        return {'source_jar_sha256': sha(source), 'mutated_jar_sha256': sha(destination), 'only_changed_entry': target, 'mutation': 'Replace the unique same-length UTF8 getter name; Attributes then reads management instead of monitoring.'}
    mutant = out / 'negative-reference.jar'; current_mutant = out / 'negative-current.jar'
    record['negative_control'] = mutate(original, mutant)
    record['current_negative_control'] = mutate(packages['aarch64'] / 'Contents/Resources/RAID_Admin.jar', current_mutant)
    expected = b'PASS credential persistence; roundtrips=80; management_absent=true; monitoring_preserved=true; forget_flag_only=true; private_current_mode=true; forbidden_operations=0\n'
    for arch, app in packages.items():
        runtime_root = app / 'Contents/PlugIns/Runtime.jdk'
        runtime = runtime_root / 'Contents/Home'
        verify_runtime(runtime_root, runtime_manifest()['architectures'][arch])
        for mode in ['-Xint', '-Xcomp']:
            with tempfile.TemporaryDirectory(prefix='credential-', dir=out) as directory:
                root = Path(directory); env = isolated_env(); env.update(HOME=directory, TMPDIR=directory)
                jvm_arch = 'aarch64' if arch == 'aarch64' else 'x86_64'
                argv = [str(runtime / 'bin/java')] + JAVA_FLAGS + [mode, '-Xverify:all', '-Xmx256m', '-XX:-UsePerfData', '-XX:-HeapDumpOnOutOfMemoryError', '-Djava.awt.headless=true', '-Dlog4j.defaultInitOverride=true', '-Draid.admin.gui=false', '-Dfixture.expectedArch=' + jvm_arch, '-Duser.home=' + directory, '-Djava.io.tmpdir=' + directory, '-Dfixture.directory=' + directory, '-Dfixture.allowed.library=' + str(app / 'Contents/Frameworks/libPrivatePreference.dylib'), '-Dfixture.apple.original=' + str(original), '-Dfixture.caller.candidate=' + str(app / 'Contents/Resources/RAID_Admin.jar'), '-cp', str(classes), 'atomiccaller.CredentialPersistenceObservation']
                result = subprocess.run(argv, cwd=root, env=env, capture_output=True, timeout=120, preexec_fn=no_core)
                if result.returncode or result.stdout != expected or result.stderr: raise ValueError('Credential fixture failed; raw output withheld')
                if list(root.iterdir()): raise ValueError('Unexpected fixture files remain')
                record['runs'].append({'architecture': arch, 'verified_java_os_arch': jvm_arch, 'mode': mode, 'stdout': expected.decode().strip(), 'empty_stderr': True, 'runtime_tree_sha256': runtime_manifest()['architectures'][arch]['tree_sha256']})
                print('PASS credential boundary ' + arch + ' ' + mode, flush=True)
                for altered, label in [(mutant, 'wrong_getter_negative_detected'), (current_mutant, 'current_wrong_getter_negative_detected')]:
                    negative = [('-Dfixture.apple.original=' + str(altered)) if arg.startswith('-Dfixture.apple.original=') else arg for arg in argv]
                    result = subprocess.run(negative, cwd=root, env=env, capture_output=True, timeout=120, preexec_fn=no_core)
                    if result.returncode == 0 or result.stdout != b'FAIL credential fixture; fixed_code=monitor-source\n' or b'java.lang.AssertionError: credential-fixture-failed' not in result.stderr: raise ValueError('Wrong-getter negative control failed; raw output withheld')
                    if list(root.iterdir()): raise ValueError('Negative control wrote unexpected files')
                    record['runs'][-1][label] = True
    if initial != {str(s.relative_to(ROOT)): sha(s) for s in bound_inputs} or sha(original) != ORIGINAL: raise ValueError('Inputs changed')
    verify_packages()
    (out / 'observations.json').write_text(json.dumps(record, indent=2) + '\n')

if __name__ == '__main__': main()
