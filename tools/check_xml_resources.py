#!/usr/bin/env python3
"""Observe bounded XML cases and whether lowered JAXP limits govern the original parser."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import tempfile

from audit_support import ROOT, isolated_env, run_jdk, sha, verify_jdk, verify_python
from baseline import verify_original
from runtime import runtime_manifest, verify_runtime
from verify_builds import check_artifact, EXPECTED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--runtime', required=True, action='append', type=Path, help='Pinned .jdk root')
    args = parser.parse_args()
    verify_python(); compiler = verify_jdk(args.compiler)
    if len(args.runtime) != 2: raise ValueError('Provide exactly one pinned runtime per architecture')
    identity, provenance = check_artifact(args.build)
    if identity != json.loads(EXPECTED.read_text())['expected']: raise ValueError('Candidate differs from expected build')
    original = ROOT/'original/RAID_Admin_original.jar'; verify_original(original)
    candidate = args.build/'RAID Admin.app/Contents/Resources/RAID_Admin.jar'
    commit = subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    dirty = bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    sources = [ROOT/'tests/java/PlistResourceProbe.java', ROOT/'tests/java/ParserPolicyProbe.java', ROOT/'tests/java/ParserDefaultsProbe.java', ROOT/'tests/java/fixture/OfflineGuard.java']
    helpers = [Path(__file__).resolve()] + [ROOT/'tools'/name for name in ('audit_support.py','baseline.py','class_patch.py','socket_configuration_patch.py','runtime.py','verify_builds.py')]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in sources + helpers}
    lock = runtime_manifest(); seen = set(); observations = []; expected = {}; policy_observations = []; defaults_observations = []
    lowered = ['-Djdk.xml.entityExpansionLimit=32','-Djdk.xml.totalEntitySizeLimit=256',
               '-Djdk.xml.maxGeneralEntitySizeLimit=256','-Djdk.xml.maxElementDepth=16']
    with tempfile.TemporaryDirectory(prefix='raid-xml-resource-') as temporary:
        run_jdk(args.compiler,'javac',['-source','8','-target','8','-cp',str(original),'-d',temporary]+[str(p) for p in sources])
        for root in args.runtime:
            arch = None
            for key in ('aarch64','x64'):
                try: verify_runtime(root,lock['architectures'][key])
                except ValueError: continue
                arch = key; break
            if arch is None or arch in seen: raise ValueError('Distinct pinned runtimes required')
            seen.add(arch); home = root.resolve()/'Contents/Home'
            defaults=run_jdk(home,'java',['-Xverify:all','-Djava.awt.headless=true','-Duser.home='+temporary,
                '-cp',temporary+':'+str(original),'ParserDefaultsProbe'],timeout=20).splitlines()
            if not defaults or defaults[-1]!='PASS pinned Java8 secure-processing defaults; guarded_operations=0': raise RuntimeError('Vendor-default measurement incomplete')
            if defaults_observations and defaults!=defaults_observations[0]['results']: raise ValueError('Vendor defaults differ between runtimes')
            defaults_observations.append({'architecture':arch,'results':defaults})
            for jar in (original,candidate):
                for mode, flags in [('default',[]),('lowered-jaxp-properties',lowered)]:
                    command = [str(home/'bin/java'),'-Xverify:all','-Xmx64m','-Xss1m',
                               '-Djava.awt.headless=true','-Duser.home='+temporary,
                               '-Djava.ext.dirs='+str(home/'jre/lib/ext'),'-Djava.endorsed.dirs=',
                               '-Dfile.encoding=UTF-8','-Duser.language=en','-Duser.country=US','-Duser.timezone=UTC']
                    command += flags + ['-cp',temporary+':'+str(jar.resolve()),'PlistResourceProbe',str(jar.resolve()),mode,str(jar==candidate).lower()]
                    try: result = subprocess.run(command,env=isolated_env(),capture_output=True,timeout=20)
                    except subprocess.TimeoutExpired: raise RuntimeError('XML resource fixture timed out; raw output withheld') from None
                    if result.returncode or result.stderr: raise RuntimeError('XML resource fixture failed; raw output withheld')
                    try: lines = result.stdout.decode('ascii').splitlines()
                    except UnicodeDecodeError: raise RuntimeError('XML resource fixture output invalid; raw output withheld') from None
                    if not lines or lines[-1] != 'PASS bounded XML resource observations; guarded_operations=0':
                        raise RuntimeError('XML resource fixture incomplete; raw output withheld')
                    application_lines = [line for line in lines if not line.startswith('jdk_control ')]
                    controls = [line for line in lines if line.startswith('jdk_control ')]
                    wanted = ['jdk_control '+label+' rejected='+str(mode != 'default').lower() for label in ('entity-count','entity-size','depth')]
                    if controls != wanted: raise ValueError('JDK positive control did not complete')
                    artifact = 'candidate' if jar==candidate else 'original'
                    if artifact not in expected: expected[artifact] = application_lines
                    if application_lines != expected[artifact]: raise ValueError('Application XML observations vary with ambient properties or runtime')
                    observations.append({'architecture':arch,'jar_sha256':sha(jar),'mode':mode,'results':lines})
            for mode, flags in [('default',[]),('lowered',lowered),('hostile',[
                    '-Djavax.xml.parsers.SAXParserFactory=fixture.invalid.Provider',
                    '-Djdk.xml.entityExpansionLimit=0','-Djdk.xml.totalEntitySizeLimit=0',
                    '-Djdk.xml.maxElementDepth=0','-Djdk.xml.maxXMLNameLimit=0',
                    '-Djdk.xml.maxGeneralEntitySizeLimit=0','-Djdk.xml.maxParameterEntitySizeLimit=0','-Djdk.xml.entityReplacementLimit=0'])]:
                command=[str(home/'bin/java'),'-Xverify:all','-Xmx64m','-Xss1m','-Djava.awt.headless=true','-Duser.home='+temporary,
                    '-Djava.ext.dirs='+str(home/'jre/lib/ext'),'-Djava.endorsed.dirs=','-Dfile.encoding=UTF-8',
                    '-Duser.language=en','-Duser.country=US','-Duser.timezone=UTC']+flags+[
                    '-cp',temporary+':'+str(candidate.resolve()),'ParserPolicyProbe']
                try: result=subprocess.run(command,env=isolated_env(),capture_output=True,timeout=20)
                except subprocess.TimeoutExpired: raise RuntimeError('Parser policy fixture timed out; output withheld') from None
                wanted=b'PASS parser policy: bootstrap provider, fresh instances, explicit quotas, external access empty, predefined references, entity quota, dict depth boundary; guarded_operations=0\n'
                if result.returncode or result.stderr or result.stdout!=wanted: raise RuntimeError('Parser policy fixture failed; raw output withheld')
                policy_observations.append({'architecture':arch,'mode':mode,'properties':flags,'result':'PASS'})
            verify_runtime(root,lock['architectures'][arch])
    for label in ('internal-entity','flat-entities-512','nested-entities-64','arrays-8','arrays-30','string-4096','string-65536','unicode-32768','dict-30','mixed-30','empty-array-30','empty-dict-30'):
        prefix='fixture '+label+' outcome='
        before=[line for line in expected['original'] if line.startswith(prefix)]
        after=[line for line in expected['candidate'] if line.startswith(prefix)]
        if len(before)!=1 or len(before[0][len(prefix):])!=64 or any(c not in '0123456789abcdef' for c in before[0][len(prefix):]) or before!=after: raise ValueError('Accepted plist output differs from original')
    for depth in (31,32,128):
        if 'fixture arrays-'+str(depth)+' outcome=rejected-legacy-array-bounds' not in expected['original'] or 'fixture arrays-'+str(depth)+' outcome=rejected-depth-limit' not in expected['candidate']:
            raise ValueError('Legacy depth rejection boundary changed')
    for kind in ('dict','mixed','empty-array','empty-dict'):
        if 'fixture '+kind+'-31 outcome=rejected-legacy-array-bounds' not in expected['original'] or 'fixture '+kind+'-31 outcome=rejected-depth-limit' not in expected['candidate']:
            raise ValueError('Container depth rejection boundary changed')
    if hashes != {str(p.relative_to(ROOT)): sha(p) for p in sources + helpers}: raise ValueError('Fixture sources changed')
    if check_artifact(args.build)[0] != identity: raise ValueError('Candidate changed')
    verify_original(original); verify_jdk(args.compiler)
    print(json.dumps({'fixture_commit':commit,'fixture_dirty':dirty,'host_machine':platform.machine(),
        'application_source_commit':provenance['source_commit'],'candidate_sha256':sha(candidate),
        'original_sha256':sha(original),'compiler_tree_sha256':compiler['tree_sha256'],
        'runtime_trees':{key:lock['architectures'][key]['tree_sha256'] for key in sorted(seen)},
        'source_hashes':hashes,'heap':'64m','stack':'1m','lowered_properties':lowered,'observations':observations,'policy_observations':policy_observations,'vendor_defaults':defaults_observations,
        'limits':'Bounded synthetic XML cases through Reader/InputStream; accepted cases canonical roundtrip, rejected cases fixed category and direct-readXML reproduction only. Original parser construction and provider origin verified. Differential inputs/canonical characters below 131072, entity output at most 3584 characters, arrays depth at most 128; dict/mixed/empty-container boundaries at 30 and 31. Candidate-only policy probes use inputs below 524288 characters, predefined references 70000, accepted internal references 4000 and rejected references 4100; Expanded-size acceptance is 1040384 characters; a bounded 257-reference document must reject at the 1 MiB total-entity-size quota independently of count and per-entity quotas. A 262145-character entity rejects at the general-entity quota; a 65537-character parameter entity independently rejects while a small 65535-character parameter entity is accepted. Four threads parse 16 small documents. Explicit parser quotas are checked under default, lowered and hostile ambient properties recorded for each run. Three JDK-provider positive controls verify default acceptance versus rejection under combined lowered flags; size controls do not isolate total versus per-entity size quotas. No crash threshold, resource exhaustion, actual controller size, HTTP allocation, full app or UI qualification. Lowered properties are experimental subprocess flags only, never application launcher changes. x64 runs on arm64 host under inferred Rosetta.'},indent=2))


if __name__ == '__main__': main()
