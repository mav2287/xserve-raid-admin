#!/usr/bin/env python3
"""Characterize synthetic firmware ZIP loading through the unchanged original wrapper."""
import argparse
import json
import platform
from pathlib import Path
import subprocess
import tempfile
import warnings
import zipfile
import zlib
from audit_support import ROOT, sha, verify_jdk, verify_python, run_jdk, isolated_env
from baseline import verify_original
from runtime import runtime_manifest, verify_runtime
from verify_builds import check_artifact, EXPECTED


def fixtures(directory):
    main = ('Manifest-Version: 1.0\r\n'
            'xserveraid-raid-controller-update-image: raid.bin\r\n'
            'xserveraid-coprocessor-full-image: full.bin\r\n'
            'xserveraid-coprocessor-update-image: update.bin\r\n'
            'Fixture-Continuation: ' + 'x'*40 + '\r\n ' + 'x'*40 + '\r\n\r\n')
    sections = ''.join('Name: '+name+'\r\nfirmware-version: 9.9.9\r\nfirmware-date: 2000-01-01\r\n\r\n'
                       for name in ['raid.bin','full.bin','update.bin','ghost.bin'])
    contents = [('META-INF/MANIFEST.MF',(main+sections).encode('ascii'))]
    contents += [(name,bytes(range(4))) for name in ['raid.bin','full.bin','update.bin']]
    def write(name, items, compression=zipfile.ZIP_STORED):
        with zipfile.ZipFile(directory/name,'w') as archive:
            for entry,data in items:
                info=zipfile.ZipInfo(entry,(1980,1,1,0,0,0)); info.compress_type=compression
                archive.writestr(info,data)
    write('stored.xfb',contents); write('deflated.xfb',contents,zipfile.ZIP_DEFLATED)
    write('no-manifest.xfb',[('fixture.bin',bytes(range(4)))])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UserWarning)
        write('duplicate.xfb',[('duplicate.bin',b'\x01'),('duplicate.bin',b'\x02')])
    data=(directory/'stored.xfb').read_bytes()
    (directory/'malformed.xfb').write_bytes(b'synthetic non-ZIP fixture')
    (directory/'truncated.xfb').write_bytes(data[:data.index(b'PK\x01\x02')+10])
    (directory/'corrupt-local-header.xfb').write_bytes(b'BAD!'+data[4:])
    paths=sorted(directory.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in paths): raise ValueError('Unsafe fixture path')
    return {p.name:sha(p) for p in paths}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler',required=True,type=Path)
    parser.add_argument('--build',required=True,type=Path)
    parser.add_argument('--runtime',required=True,action='append',type=Path,help='Vendor .jdk root, not Contents/Home')
    args=parser.parse_args(); verify_python(); compiler=verify_jdk(args.compiler)
    if len(args.runtime) != 2: raise ValueError('Provide exactly one runtime per architecture')
    fixture_commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    fixture_dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    identity,provenance=check_artifact(args.build)
    if identity != json.loads(EXPECTED.read_text())['expected']: raise ValueError('Candidate differs from reviewed build')
    candidate=args.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    original=ROOT/'original/RAID_Admin_original.jar'; verify_original(original)
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(candidate) as after:
        names=[n for n in before.namelist() if n.startswith('com/apple/xsr/update/FirmwareBundleConnection') and n.endswith('.class')]
        candidate_names=[n for n in after.namelist() if n.startswith('com/apple/xsr/update/FirmwareBundleConnection') and n.endswith('.class')]
        if not names or set(names) != set(candidate_names) or any(before.read(n) != after.read(n) for n in names): raise ValueError('Firmware wrapper changed')
    sources=[ROOT/'tests/java/FirmwareArchiveProbe.java',ROOT/'tests/java/fixture/OfflineGuard.java']
    observations=[]; seen=set(); lock=runtime_manifest()
    with tempfile.TemporaryDirectory(prefix='raid-archive-fixture-') as temporary:
        root=Path(temporary); archives=root/'archives'; archives.mkdir(); classes=root/'classes'; classes.mkdir()
        hashes=fixtures(archives)
        run_jdk(args.compiler,'javac',['-source','8','-target','8','-cp',str(original),'-d',str(classes)]+[str(p) for p in sources])
        for runtime in args.runtime:
            # Identify by pinned contents; supplied path/name is not identity evidence.
            arch=None
            for key in ('aarch64','x64'):
                try: verify_runtime(runtime,lock['architectures'][key])
                except ValueError: continue
                arch=key; break
            if arch is None: raise ValueError('Runtime does not match either pinned architecture')
            if arch in seen: raise ValueError('Runtime architecture repeated')
            seen.add(arch)
            home=runtime.resolve()/'Contents/Home'
            results=[]
            for jar in (original,candidate):
                command=[str(home/'bin/java'),'-Xverify:all','-Djava.awt.headless=true','-Duser.home='+temporary,
                    '-Djava.ext.dirs='+str(home/'jre/lib/ext'),'-Djava.endorsed.dirs=',
                    '-Dfile.encoding=UTF-8','-Duser.language=en','-Duser.country=US','-Duser.timezone=UTC',
                    '-cp',str(classes)+':'+str(jar.resolve()),'FirmwareArchiveProbe',str(archives),str(jar.resolve())]
                try: result=subprocess.run(command,env=isolated_env(),capture_output=True,timeout=30)
                except subprocess.TimeoutExpired: raise RuntimeError('Archive fixture timed out; raw output withheld') from None
                if result.returncode or result.stderr: raise RuntimeError('Archive fixture failed; raw output withheld')
                try: results.append(result.stdout.decode('ascii').splitlines())
                except UnicodeDecodeError: raise RuntimeError('Archive fixture output invalid; raw output withheld') from None
            if results[0] != results[1]: raise ValueError('Original/candidate archive behavior differs')
            verify_runtime(runtime,lock['architectures'][arch])
            observations.append({'architecture':arch,'runtime_tree_sha256':lock['architectures'][arch]['tree_sha256'],'results':results})
    print(json.dumps({'fixture_commit':fixture_commit,'fixture_dirty':fixture_dirty,'host_machine':platform.machine(),
        'source_commit':provenance['source_commit'],'source_dirty':provenance['source_dirty'],
        'original_sha256':sha(original),'candidate_sha256':sha(candidate),'wrapper_entries':names,
        'compiler_tree_sha256':compiler['tree_sha256'],'fixture_sources':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'tool_sha256':sha(Path(__file__)),'archives':hashes,'zlib_version':zlib.ZLIB_RUNTIME_VERSION,'observations':observations,
        'limits':'Synthetic local archive loading through byte-identical wrapper only. Original and candidate share each pinned runtime; this primarily characterizes JDK archive behavior. No real firmware validity, updater/preflight UI, cache changes, transmission, controller access or retry-queue qualification. On an arm64 host, successful x64 execution is inferred to use Rosetta; physical Intel qualification is not established.'},indent=2))


if __name__ == '__main__': main()
