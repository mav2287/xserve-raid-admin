#!/usr/bin/env python3
"""Unsigned per-CPU secure bundle, deterministic ZIP and SPDX inventory; no launch/install."""
import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parent))
import argparse,hashlib,json,plistlib,subprocess,tempfile,zipfile,copy
from pathlib import Path
from audit_support import ROOT,isolated_env,sha,tree,modes,digest,verify_python
from secure_build import state,HELPERS,NATIVE_ABI
from historical_secure import check_historical_artifact
from bundle import copy_verified
from runtime import runtime_manifest,verify_runtime,directory_modes
from release_archive import write_archive,extract_archive,snapshot
from spdx import generate,validate
from baseline import ALLOWED_JAR_CHANGES
from spdx_validator import verify as verify_validator

def verify_spdx_bytes(document,app):
    # Independently bind every physical and virtual file checksum to bundle bytes.
    buffers={app.name+'/'+n:(app/n).read_bytes() for n in tree(app)}
    import zipfile
    with zipfile.ZipFile(app/'Contents/Resources/RAID_Admin.jar') as archive:
        buffers.update({app.name+'/Contents/Resources/RAID_Admin.jar!/'+n:archive.read(n) for n in archive.namelist() if not n.endswith('/')})
    if {f['fileName'] for f in document['files']}!={'./'+n for n in buffers}:raise ValueError('SPDX measured member set differs')
    for package in document['packages']:
        if 'checksums' in package:
            path=package.get('packageFileName','')[2:]
            if path not in buffers or {c['algorithm']:c['checksumValue'] for c in package['checksums']}!={'SHA1':hashlib.sha1(buffers[path]).hexdigest(),'SHA256':hashlib.sha256(buffers[path]).hexdigest()}:raise ValueError('SPDX package checksums differ from measured bytes')
    for record in document['files']:
        data=buffers[record['fileName'][2:]]
        checks={c['algorithm']:c['checksumValue'] for c in record['checksums']}
        if checks!={'SHA256':hashlib.sha256(data).hexdigest(),'SHA1':hashlib.sha1(data).hexdigest()}:raise ValueError('SPDX checksum does not match actual bytes')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--architecture',choices=['aarch64','x64'],required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--validator',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--created',required=True);a=p.parse_args();verify_python();initial=state()
    if initial['dirty']:raise ValueError('Clean secure packaging source required')
    root=ROOT/'build';out=a.output.resolve()
    if root.is_symlink() or a.output.exists() or a.output.is_symlink() or not out.is_relative_to(root.resolve()) or out==root.resolve():raise ValueError('New secure package inside real build required')
    identity,source,bridge=check_historical_artifact(a.build)
    if source['source_dirty']:raise ValueError('Clean secure source artifact required')
    inputs={str(f.relative_to(ROOT)):sha(f) for f in sorted((ROOT/'tools').glob('*.py'))+[ROOT/'audit/sbom.json',ROOT/'audit/spdx-validator-lock.json',ROOT/'audit/runtime-lock.json',ROOT/'audit/spdx-2.3.1-schema.json',ROOT/'modernization/private-preferences/RAIDAdmin',ROOT/'packaging/AppIcon.png']}
    for n,h in source['input_hashes'].items():
        data=subprocess.check_output(['/usr/bin/git','show',source['source_commit']+':'+n],cwd=ROOT,env=isolated_env())
        if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Source provenance differs from recorded Git commit')
    lock=runtime_manifest();spec=lock['architectures'][a.architecture];verify_runtime(a.runtime,spec);validator=verify_validator(a.validator);native=source['native_helpers'][a.architecture]
    out.mkdir();app=out/'RAID Admin.app';copy_verified(a.build/'RAID Admin.app',app,source['files'],source['file_modes'])
    destination=app/'Contents/PlugIns/Runtime.jdk';copy_verified(a.runtime,destination,spec['files'],spec['file_modes'],spec['directory_modes']);verify_runtime(destination,spec)
    launcher=app/'Contents/MacOS/RAIDAdmin';launcher.write_bytes((ROOT/'modernization/private-preferences/RAIDAdmin').read_bytes());launcher.chmod(0o755)
    icon=app/'Contents/Resources/AppIcon.png';icon.write_bytes((ROOT/'packaging/AppIcon.png').read_bytes());icon.chmod(0o644)
    framework=app/'Contents/Frameworks';framework.mkdir();library=framework/'libPrivatePreference.dylib';data=(a.build/native['path']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=native['sha256']:raise ValueError('Selected native helper differs')
    library.write_bytes(data);library.chmod(0o644)
    plist=app/'Contents/Info.plist';metadata=plistlib.loads(plist.read_bytes());expected_plist=dict(metadata);expected_plist['LSMinimumSystemVersion']='11.0';metadata['LSMinimumSystemVersion']='11.0';plist.write_bytes(plistlib.dumps(metadata,sort_keys=True))
    if plistlib.loads(plist.read_bytes())!=expected_plist:raise ValueError('Package plist differs beyond OS binary floor')
    for directory in [app]+list(app.rglob('*')):
        if directory.is_dir():directory.chmod(0o755)
    verify_runtime(destination,spec);files,permissions,dirs=tree(app),modes(app),directory_modes(app)
    changed={n for n,h in source['files'].items() if files.get(n)!=h}
    additions=set(files)-set(source['files'])
    if changed!={'Contents/MacOS/RAIDAdmin','Contents/Info.plist'} or additions!={'Contents/Resources/AppIcon.png','Contents/Frameworks/libPrivatePreference.dylib'}|{'Contents/PlugIns/Runtime.jdk/'+n for n in spec['files']}:raise ValueError('Unexpected secure package delta')
    if files['Contents/Resources/RAID_Admin.jar']!=source['jar_sha256'] or files['Contents/Frameworks/libPrivatePreference.dylib']!=native['sha256']:raise ValueError('Packaged JAR/native differs')
    manifest={'schema':1,'purpose':'unsigned secure compatibility candidate; hardware/native GUI acceptance unqualified','apple_version':'1.5.1','compatibility_version':source['compatibility_version'],'source_commit':source['source_commit'],'source_dirty':False,'packager_commit':initial['commit'],'packager_dirty':False,'historical_product_bridge':bridge,'input_hashes':inputs,'source_provenance_sha256':sha(a.build/'provenance.json'),'original_jar_sha256':source['original_jar_sha256'],'audit27_jar_sha256':source['audit27_jar_sha256'],'jar_sha256':source['jar_sha256'],'native_abi':source['native_abi'],'native_helper':native,'bundled_runtime':{'vendor':lock['vendor'],'version':lock['version'],'architecture':a.architecture,'archive_url':spec['archive_url'],'archive_sha256':spec['archive_sha256'],'tree_sha256':spec['tree_sha256'],'signature_team':spec['signature_team']},'application_signing':None,'application_notarization':'not performed','files':files,'file_modes':permissions,'directory_modes':dirs,'bundle_tree_sha256':digest({'files':files,'file_modes':permissions,'directory_modes':dirs})}
    (out/'provenance.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    first=out/('RAID-Admin-1.5.1-modern.audit.28-'+a.architecture+'-unsigned.zip');second=out/'repeated.zip';write_archive(app,first);write_archive(app,second)
    if sha(first)!=sha(second):raise ValueError('Repeated secure archive differs')
    extracted=extract_archive(first,out/'extracted',app.name)
    if snapshot(extracted)!=snapshot(app):raise ValueError('Extracted secure bundle differs')
    verify_runtime(extracted/'Contents/PlugIns/Runtime.jdk',spec)
    inventory=json.loads((ROOT/'audit/sbom.json').read_text());original_names={n for c in inventory['components'] for n in c['files']};allowed=ALLOWED_JAR_CHANGES|HELPERS|{'META-INF/MANIFEST.MF'}
    provenance={'execution_state':initial,'product_manifest_sha256':sha(a.build/'provenance.json'),'packaged_manifest_sha256':sha(out/'provenance.json'),'audit27_reference_sha256':source['audit27_jar_sha256'],'native_abi':source['native_abi'],'native_dependencies':['/usr/lib/libSystem.B.dylib (provided by macOS, not bundled)'],'qualification':'Local unsigned artifact inventory only; no native GUI/controller acceptance'}
    doc=generate(app,manifest,a.created,inventory['components'],allowed&original_names,allowed-original_names,provenance)
    filename='./RAID Admin.app/Contents/Frameworks/libPrivatePreference.dylib';entry=next(f for f in doc['files'] if f['fileName']==filename);identifier='SPDXRef-private-preferences-native';sha1=next(c['checksumValue'] for c in entry['checksums'] if c['algorithm']=='SHA1')
    doc['packages'].append({'SPDXID':identifier,'name':'RAID Admin private preference native helper','versionInfo':'ABI '+source['native_abi'],'downloadLocation':'NOASSERTION','filesAnalyzed':True,'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION','copyrightText':'NOASSERTION','packageVerificationCode':{'packageVerificationCodeValue':hashlib.sha1(sha1.encode()).hexdigest()},'comment':'Local Darwin JNI helper; '+a.architecture+'; macOS binary floor 11.0. Links only macOS-provided libSystem; no libjvm dependency. Application bundle remains unsigned/unnotarized.'})
    doc['relationships']+=[{'spdxElementId':'SPDXRef-application','relationshipType':'CONTAINS','relatedSpdxElement':identifier},{'spdxElementId':identifier,'relationshipType':'CONTAINS','relatedSpdxElement':entry['SPDXID']}]
    doc.pop('documentNamespace');doc['documentNamespace']='https://github.com/mav2287/xserve-raid-admin/spdx/'+digest(doc);validate(doc,a.validator);verify_spdx_bytes(doc,app);verify_spdx_bytes(doc,extracted)
    bad=copy.deepcopy(doc);bad['files'][0]['checksums'][0]['checksumValue']='0'*64
    bad.pop('documentNamespace');bad['documentNamespace']='https://github.com/mav2287/xserve-raid-admin/spdx/'+digest(bad)
    validate(bad,a.validator)  # Valid format/namespace is insufficient: bytes must disagree.
    try:verify_spdx_bytes(bad,extracted)
    except ValueError:pass
    else:raise ValueError('SPDX negative accepted')
    sha1_bad=copy.deepcopy(doc);item=sha1_bad['files'][0];next(c for c in item['checksums'] if c['algorithm']=='SHA1')['checksumValue']='0'*40
    try:verify_spdx_bytes(sha1_bad,extracted)
    except ValueError:pass
    else:raise ValueError('SPDX wrong SHA1 accepted')
    (out/'SBOM.spdx.json').write_text(json.dumps(doc,sort_keys=True,indent=2)+'\n')
    if state()!=initial or check_historical_artifact(a.build)[0]!=identity or any(sha(ROOT/n)!=h for n,h in inputs.items()) or snapshot(app)!={'files':files,'file_modes':permissions,'directory_modes':dirs}:raise ValueError('Secure packaging inputs changed')
    verify_runtime(a.runtime,spec);verify_validator(a.validator)
    record={'qualification':False,'scope':'Unsigned local package/archive/SPDX verification; no launch/install','product_source_commit':source['source_commit'],'packager_commit':initial['commit'],'source_dirty':False,'historical_product_bridge':bridge,'architecture':a.architecture,'product_jar_sha256':source['jar_sha256'],'native_sha256':native['sha256'],'archive_sha256':sha(first),'repeated_archive_equal':True,'extracted_bundle_equal':True,'vendor_runtime_signature_verified':True,'sbom_sha256':sha(out/'SBOM.spdx.json'),'bundle_tree_sha256':manifest['bundle_tree_sha256'],'inputs':inputs,'limits':['No Developer ID/notarization, quarantine/Gatekeeper, native GUI, physical Intel or real controllers','Original Apple redistribution rights unresolved; inventory is not a license grant']}
    (out/'release-observations.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print('PASS secure unsigned package; architecture='+a.architecture+'; repeat/extract/signature/SPDX=true')
if __name__=='__main__':main()
