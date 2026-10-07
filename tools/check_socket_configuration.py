#!/usr/bin/env python3
"""Qualify initial read-timeout setup using actual classes and memory SocketImpl only."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from audit_support import ROOT, sha, verify_python, verify_jdk, run_jdk, isolated_env
from runtime import runtime_manifest, verify_runtime
from verify_builds import check_artifact, entries
from baseline import verify_original
from socket_configuration_patch import ENTRY, plan, normalize
from socket_configuration_structure import check_socket_setup
from inventory import disassemble_entries

REFERENCE = '202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd'
HELPER = 'compat/SocketConfiguration.class'
JAVA = ('tests/java/socketfixture/ConfigurationPublicationObservation.java',
        'tests/java/socketfixture/ConfigurationObservation.java',
        'tests/java/socketfixture/ConfigurationRunner.java',
        'tests/java/fixture/OfflineGuard.java', 'tests/java/fixture/FixtureIdentity.java')
SOURCES = JAVA + ('tools/check_socket_configuration.py', 'tools/socket_configuration_patch.py','tools/connection_publication_patch.py','tools/help_patch.py','tools/model_diagnostic_patch.py','tools/preference_io_patch.py','audit/preference-io-patches.json','audit/model-diagnostic-patches.json','audit/help-patches.json',
    'tools/socket_configuration_structure.py', 'tools/socket_configuration_mutants.py', 'tools/class_patch.py', 'tools/sync_ownership_patch.py',
    'tools/worker_exit_patch.py', 'tools/stop_admission_patch.py', 'tools/audit_support.py',
    'tools/baseline.py', 'tools/runtime.py', 'tools/inventory.py', 'tools/verify_builds.py',
    'patches/compat/SocketConfiguration.java', 'audit/expected-build.json',
    'audit/security-patches.json', 'audit/runtime-lock.json', 'audit/jdk-lock.json',
    'audit/python-lock.json', 'tests/test_socket_configuration.py',
    'tests/fixtures/socket-configuration-candidate-http.javap')


def state():
    return (subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=ROOT,
            env=isolated_env(), text=True).strip(),
            bool(subprocess.check_output(['/usr/bin/git', 'status', '--porcelain'],
                 cwd=ROOT, env=isolated_env())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--runtime', required=True, action='append', type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--candidate-sha256', required=True)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--development', action='store_true')
    args = parser.parse_args()
    verify_python(); compiler = verify_jdk(args.jdk); initial = state()
    if initial[1] and not args.development:
        raise ValueError('Clean fixture source required')
    candidate = args.candidate.resolve(); reference = args.reference.resolve()
    if args.candidate.is_symlink() or args.reference.is_symlink():
        raise ValueError('Regular candidate and reference required')
    if sha(candidate) != args.candidate_sha256 or sha(reference) != REFERENCE:
        raise ValueError('Anchored artifact identity differs')
    identity, manifest = check_artifact(candidate.parents[3])
    if identity != json.loads((ROOT/'audit/expected-build.json').read_text())['expected']:
        raise ValueError('Candidate differs from expected build')
    if manifest['source_dirty'] and not args.development:
        raise ValueError('Clean product source required')
    original = ROOT/'original/RAID_Admin_original.jar'; verify_original(original)
    old, new, apple = entries(reference), entries(candidate), entries(original)
    from help_patch import strip_entries
    core=strip_entries(new)
    if set(core)-set(old) != {HELPER} or set(old)-set(core):
        raise ValueError('Reference entry set differs beyond socket helper')
    from connection_publication_patch import ENTRY as ACPX,normalize as normalize_publication
    if normalize_publication(new[ACPX])!=old[ACPX]:raise ValueError('Private Acpx predecessor differs')
    if {n for n in old if old[n] != core[n]} != {ENTRY,ACPX}:
        raise ValueError('Reference bytes differ beyond socket and private connection overrides')
    if old[ENTRY] != apple[ENTRY] or plan(apple[ENTRY]) != new[ENTRY] or normalize(new[ENTRY]) != apple[ENTRY]:
        raise ValueError('Whole original class reconstruction differs')
    check_socket_setup(disassemble_entries(args.jdk, candidate, [ENTRY], verbose=True))
    hashes = {name: sha(ROOT/name) for name in SOURCES}
    artifacts = {str(p): sha(p) for p in (candidate, reference, original)}
    lock = runtime_manifest(); runtimes = {}; rows = []
    for root in args.runtime:
        matching = []
        for arch in ('aarch64', 'x64'):
            try: verify_runtime(root, lock['architectures'][arch])
            except ValueError: continue
            matching.append(arch)
        if len(matching) != 1 or matching[0] in runtimes:
            raise ValueError('Distinct locked runtimes required')
        runtimes[matching[0]] = root.resolve()
    if set(runtimes) != {'aarch64', 'x64'}:
        raise ValueError('Both locked architectures required')
    with tempfile.TemporaryDirectory(prefix='raid-socket-configuration-') as temporary:
        tmp = Path(temporary); classes = tmp/'classes'; classes.mkdir()
        helper = tmp/'helper'; helper.mkdir()
        run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-d', str(helper),
                str(ROOT/'patches/compat/SocketConfiguration.java')], require_empty_stderr=True)
        if (helper/HELPER).read_bytes() != new[HELPER] or new[HELPER][6:8] != b'\x00\x34':
            raise ValueError('Product helper differs from source or Java 8 version')
        # Only fixture compilation permits compiler notes from the legacy APIs.
        run_jdk(args.jdk, 'javac', ['-source', '8', '-target', '8', '-cp', str(candidate),
                '-d', str(classes)]+[str(ROOT/name) for name in JAVA])
        probes = {str(p.relative_to(classes)): sha(p) for p in classes.rglob('*.class')}
        if HELPER in probes or ENTRY in probes or any(n in new for n in probes):
            raise ValueError('Fixture shadows a product class')
        product = {name: hashlib.sha256(data).hexdigest() for name, data in new.items()
                   if name.endswith('.class') and (name.startswith('compat/') or name == ENTRY)}
        identity_rows = [n[:-6].replace('/', '.')+'\t'+str(location)+'\t'+h
            for mapping, location in ((probes, classes), (product, candidate))
            for n, h in sorted(mapping.items())]
        idfile = tmp/'identity.tsv'; idfile.write_text('\n'.join(identity_rows)+'\n')
        idhash = sha(idfile)
        for arch, root in runtimes.items():
            for mode in ('-Xint', '-Xcomp'):
                results = []
                for kind, expected in (
                    ('publication', 'PASS actual read-timeout configuration prototype; cases=15; native_sockets=0'),
                    ('direct', 'PASS direct configuration prototype; cases=14; guarded_operations=0')):
                    flags = [mode, '-Xverify:all', '-Djava.awt.headless=true', '-Duser.home='+str(tmp),
                        '-Dfixture.identitymanifest='+str(idfile), '-cp', str(candidate)+':'+str(classes),
                        'ConfigurationRunner', kind]
                    output = run_jdk(root/'Contents/Home', 'java', flags, timeout=60, require_empty_stderr=True)
                    if output.splitlines() != [expected]:
                        raise ValueError('Exact memory fixture result differs; raw output withheld')
                    results.append({'fixture': kind, 'cases': 15 if kind == 'publication' else 14,
                                    'result': expected, 'execution_flags': flags})
                rows.append({'architecture': arch, 'execution_mode': mode, 'results': results,
                             'runtime_tree_sha256': lock['architectures'][arch]['tree_sha256']})
            verify_runtime(root, lock['architectures'][arch])
        from socket_configuration_mutants import observe
        negatives = observe(args.jdk, runtimes, new, (ROOT/'patches/compat/SocketConfiguration.java').read_text(),
                            classes, probes, tmp/'mutants')
        for arch, root in runtimes.items(): verify_runtime(root, lock['architectures'][arch])
        if sha(idfile) != idhash:
            raise ValueError('Class identity manifest changed')
    verify_jdk(args.jdk); verify_original(original)
    if state() != initial or hashes != {n: sha(ROOT/n) for n in SOURCES} or artifacts != {p: sha(Path(p)) for p in artifacts}:
        raise ValueError('Source or artifact changed during observation')
    print(json.dumps({'fixture_commit': initial[0], 'fixture_dirty': initial[1],
        'source_commit': manifest['source_commit'], 'source_dirty': manifest['source_dirty'],
        'candidate_sha256': sha(candidate), 'reference_sha256': REFERENCE,
        'compiler_tree_sha256': compiler['tree_sha256'], 'sources': hashes,
        'compiled_fixture_hashes': probes, 'product_class_hashes': product,
        'class_identity_manifest_sha256': idhash, 'helper_source_recompiled_identically': True,
        'whole_original_class_reconstructed': True, 'independent_javap_structure': 'PASS',
        'observations': rows, 'negative_controls': negatives, 'limits': '29 memory cases per architecture/mode. Actual candidate classes, class origins and bytes checked before guards. No app Main, native sockets, controller, profiles or credentials. x64 uses Rosetta, not physical Intel. Xcomp is a requested execution policy; compilation of every method is not asserted. DNS, real TCP, timing, native GUI, controller availability and nonstandard exception subclasses remain unqualified. Original Socket(host,80), unused connect argument, commands, polling and retry policy retained. Initial read-timeout failure refuses publication and closes best effort; known IO categories retained with fixed detail. HTTP remains plaintext. Prototype wording in exact fixture output describes the memory harness, not a launch or release qualification.'}, indent=2))


if __name__ == '__main__': main()
