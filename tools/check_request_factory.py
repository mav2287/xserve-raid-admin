#!/usr/bin/env python3
"""Bounded synthetic factory sweep; no request is sent and filename firmware is excluded."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from audit_support import ROOT, sha, verify_jdk, verify_python, run_jdk, isolated_env
from baseline import verify_original
from runtime import runtime_manifest, verify_runtime


CATALOG=ROOT/'audit/request-factory-signatures.json'
EXPECTED=ROOT/'audit/request-factory-expected.json'


def unique_object(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate JSON key; raw output withheld')
        value[key]=item
    return value


def read_json(path):
    raw=path.read_bytes()
    return json.loads(raw,object_pairs_hook=unique_object),hashlib.sha256(raw).hexdigest()


def validate(result,catalog,expected=None):
    try:return _validate(result,catalog,expected)
    except (KeyError,TypeError):raise ValueError('Factory schema differs; raw output withheld') from None


def _validate(result,catalog,expected=None):
    try:data=json.loads(result,object_pairs_hook=unique_object)
    except (ValueError,TypeError):raise ValueError('Factory fixture JSON invalid; raw output withheld') from None
    if not isinstance(data,dict) or set(data)!={'signatures','rows','enqueue_observations','invoked_per_sweep','excluded_per_sweep','guarded_operations'} or data['signatures']!=catalog['signatures'] or data['invoked_per_sweep']!=58 or data['excluded_per_sweep']!=1 or data['guarded_operations']!=0:raise ValueError('Factory coverage differs; raw output withheld')
    if any(type(data[key]) is not int for key in ('invoked_per_sweep','excluded_per_sweep','guarded_operations')):raise ValueError('Factory counters differ')
    rows=data['rows']
    if not isinstance(rows,list) or len(rows)!=116:raise ValueError('Factory row coverage differs; raw output withheld')
    expected_signatures=[name for name in catalog['signatures'] if name not in catalog['excluded']]
    keys={'signature','factory_timeout','class','path','command','shutdown','restart','timeout','body_timeout_present','shape','parameter_keys','plist_clone','parameters_clone','shared_headers','body_sha256','body_size','target'}
    for offset,timeout in ((0,0),(58,123)):
        if [row.get('signature') for row in rows[offset:offset+58] if isinstance(row,dict)]!=expected_signatures:raise ValueError('Factory signature order differs')
        for row in rows[offset:offset+58]:
            if set(row)!=keys or row['factory_timeout']!=timeout or row['class'] not in {'com.apple.xsr.net.AcpxMessageFactory$'+name for name in ('1','AcpxRequestMessage','RpcRequestMessage')} or row['shape'] not in ('none','rpc','command-dict','property-dict','property-array'):raise ValueError('Factory metadata differs; raw output withheld')
            if any(type(row[key]) is not bool for key in ('shutdown','body_timeout_present','shared_headers')) or not row['shared_headers']:raise ValueError('Factory clone metadata differs')
            if type(row['body_size']) is not int or not 0<=row['body_size']<=65536 or not isinstance(row['body_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',row['body_sha256']):raise ValueError('Factory body digest or bound differs')
            if row['parameter_keys']!=sorted(set(row['parameter_keys'])):raise ValueError('Factory parameter-key order differs')
            if any(type(row[key]) is not int for key in ('factory_timeout','timeout','restart')) or not isinstance(row['parameter_keys'],list) or any(not isinstance(key,str) for key in row['parameter_keys']):raise ValueError('Factory field types differ')
            if row['timeout']!=timeout or row['body_timeout_present']!=('timeout' in row['parameter_keys']) or row['body_timeout_present']!=(row['shape']=='command-dict' and timeout!=0):raise ValueError('Factory timeout semantics differ')
            if row['plist_clone'] not in ('absent','shared','copied') or row['parameters_clone'] not in ('absent','shared','copied'):raise ValueError('Factory clone state differs')
            if (row['shape']=='rpc')!=(row['class'].endswith('$RpcRequestMessage')) or (row['shape']=='rpc')!=(row['path']=='/cgi-bin/perform'):raise ValueError('RPC factory identity differs')
            if row['shape']=='none' and (row['body_size']!=0 or row['plist_clone']!='absent' or row['parameters_clone']!='absent'):raise ValueError('Noop body/clone semantics differ')
            if row['shape'] in ('property-array','property-dict') and row['parameters_clone']!='absent':raise ValueError('Property parameter state differs')
    expected_sharing=[{'case':name,'body_changed_after_post':changed,'header_shared':True,'target_snapshot':True,'timeout_snapshot':True} for name,changed in (('rpc',True),('command',False),('property',False))]+[{'case':'property-mutable-leaves','date_and_bytes_isolated':True},{'case':'noop','body_changed_after_post':False,'header_shared':True,'target_snapshot':True,'timeout_snapshot':True},{'case':'rpc-caller-list','body_changed_after_post':True}]
    if not isinstance(data['enqueue_observations'],list) or any(not isinstance(item,dict) or any(type(value) is not bool for key,value in item.items() if key!='case') for item in data['enqueue_observations']):raise ValueError('Factory sharing field types differ')
    if data['enqueue_observations']!=expected_sharing:raise ValueError('Factory enqueue sharing differs; raw output withheld')
    if expected is not None and data!=expected:raise ValueError('Factory results differ from reviewed expected table')
    return data


def qualification_gate(dirty,architectures,candidate_sha,expected_sha,candidate_is_original):
    if dirty:raise ValueError('Qualification requires clean committed sources')
    if architectures!={'aarch64','x64'}:raise ValueError('Qualification requires both pinned architectures')
    if candidate_is_original or candidate_sha!=expected_sha:raise ValueError('Candidate is not the current reviewed artifact')


def bootstrap_path(path):
    output=path.parent.resolve(strict=True)/path.name
    if output.suffix!='.json' or not output.is_relative_to((ROOT/'build').resolve()) or output.exists() or output.is_symlink():raise ValueError('Bootstrap requires a new ignored build JSON')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk',required=True,type=Path)
    parser.add_argument('--runtime',required=True,action='append',type=Path,help='Pinned Runtime.jdk root')
    parser.add_argument('--candidate-sha256',required=True)
    parser.add_argument('--bootstrap-output',type=Path,help='New ignored build JSON for review; not qualification')
    parser.add_argument('candidate',type=Path)
    args=parser.parse_args();verify_python();lock=verify_jdk(args.jdk)
    original=ROOT/'original/RAID_Admin_original.jar';verify_original(original)
    if args.candidate.is_symlink() or not args.candidate.is_file() or sha(args.candidate)!=args.candidate_sha256:raise ValueError('Candidate identity differs')
    catalog,catalog_sha=read_json(CATALOG)
    if catalog['original_jar_sha256']!=sha(original) or len(catalog['signatures'])!=59 or catalog['signatures']!=sorted(set(catalog['signatures'])) or catalog['excluded']!=['newUpdateFirmwareRequest(IILjava/lang/String;)Lcom/apple/xsr/net/RequestMessage;']:raise ValueError('Factory catalog identity differs')
    if args.bootstrap_output:
        output=bootstrap_path(args.bootstrap_output)
    else:
        expected,expected_sha=read_json(EXPECTED)
    sources=[ROOT/'tests/java/com/apple/xsr/net/RequestFactoryObservation.java',ROOT/'tests/java/fixture/OfflineGuard.java',ROOT/'patches/sun/io/MalformedInputException.java']
    helpers=[Path(__file__),CATALOG,ROOT/'audit/expected-build.json',ROOT/'tools/audit_support.py',ROOT/'tools/baseline.py',ROOT/'tools/class_patch.py',ROOT/'tools/runtime.py']
    if not args.bootstrap_output:helpers.append(EXPECTED)
    identities={str(p.relative_to(ROOT)):sha(p) for p in sources+helpers}
    if identities[str(CATALOG.relative_to(ROOT))]!=catalog_sha or (not args.bootstrap_output and identities[str(EXPECTED.relative_to(ROOT))]!=expected_sha):raise ValueError('Parsed inventory identity changed')
    commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env(),text=True))
    runtimes=[];seen=set();manifest=runtime_manifest()
    for root in args.runtime:
        root=root.resolve();architecture=None
        for name,entry in manifest['architectures'].items():
            try:verify_runtime(root,entry);architecture=name;break
            except ValueError:continue
        if architecture is None or architecture in seen:raise ValueError('Runtime identity differs or duplicates')
        seen.add(architecture);runtimes.append((root,architecture))
    artifact_sha=json.loads((ROOT/'audit/expected-build.json').read_text())['expected']['files']['Contents/Resources/RAID_Admin.jar']
    if seen!=set(manifest['architectures']) or args.candidate.resolve()==original.resolve() or args.candidate_sha256!=artifact_sha:raise ValueError('Both pinned runtimes and current candidate required')
    if not args.bootstrap_output:qualification_gate(dirty,seen,args.candidate_sha256,artifact_sha,args.candidate.resolve()==original.resolve())
    observations=[];reference=None
    with tempfile.TemporaryDirectory(prefix='raid-request-factory-') as tmp:
        run_jdk(args.jdk,'javac',['-source','8','-target','8','-cp',str(original),'-d',tmp]+[str(p) for p in sources])
        for jar in (original,args.candidate.resolve()):
            for root,architecture in runtimes:
                result=run_jdk(root/'Contents/Home','java',['-Xverify:all','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+tmp,'-Duser.language=en','-Duser.country=US','-Duser.timezone=UTC','-cp',tmp+':'+str(jar),'com.apple.xsr.net.RequestFactoryObservation'],timeout=20)
                data=validate(result,catalog,None if args.bootstrap_output else expected)
                if reference is None:reference=data
                if data!=reference:raise ValueError('Factory metadata/clone differential differs; raw output withheld')
                observations.append({'jar_sha256':sha(jar),'architecture':architecture,'rows':116,'invoked_per_sweep':58,'excluded_per_sweep':1,'guarded_operations':0})
                verify_runtime(root,manifest['architectures'][architecture])
    if identities!={str(p.relative_to(ROOT)):sha(p) for p in sources+helpers}:raise ValueError('Factory source changed during observation')
    verify_original(original);verify_jdk(args.jdk)
    if sha(args.candidate)!=args.candidate_sha256:raise ValueError('Candidate changed during observation')
    final_commit=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    final_dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env(),text=True))
    if final_commit!=commit or (not args.bootstrap_output and final_dirty):raise ValueError('Repository changed during qualification')
    record={'fixture_commit':commit,'fixture_dirty':dirty,'qualification':not bool(args.bootstrap_output),'purpose':'development-bootstrap' if args.bootstrap_output else 'clean-reviewed-qualification','compiler_tree_sha256':lock['tree_sha256'],'host_machine':platform.machine(),'macos_version':platform.mac_ver()[0],'runtime_trees':{architecture:manifest['architectures'][architecture]['tree_sha256'] for _,architecture in runtimes},'source_hashes':identities,'observations':observations,'limits':'Synthetic arguments and body-only serialization into capped memory; no controller, wire-header serialization, header/body values emitted, full GUI/CLI, profile or actual firmware. 59=58 invoked+one filename-firmware exclusion. Two factory timeout states; clone identities, body digests '+('generated for review' if args.bootstrap_output else 'matched to reviewed table')+' and unmutated body equality. Six bounded enqueue-sharing cases, including Date/byte-array isolation and caller-list aliasing. No retry classifier, concurrency, mutation-between-retries or sequence qualification. One synthetic argument set per overload, not every conditional/default schema. Copied maps become HashMap, so ordered-map serialization may change. Source isValidElement accepts Float/general List types unsupported by deepCopy/writeXMLLevel; no GUI failure inferred. HashMap serialization order is pinned-runtime evidence, not portability proof. x64 uses Rosetta here.'}
    if args.bootstrap_output:
        with output.open('x') as stream:stream.write(json.dumps({'record':record,'expected_for_review':reference},indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
