#!/usr/bin/env python3
"""Deterministic SPDX 2.3 bundle/JAR-entry inventory, schema and hash validation."""
import argparse,hashlib,json,re,sys,zipfile,io,os,tempfile,copy,sysconfig,unicodedata
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_support import ROOT,sha,tree,verify_python,digest,isolated_env
import subprocess
from runtime import directory_modes
from verify_bundles import check_bundle
from spdx_validator import verify as verify_validator

def clean_state():
    value={'commit':subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),'dirty':bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))}
    if value['dirty']:raise ValueError('Clean SBOM source required')
    return value

def generate(app,manifest,created,components,expected_modified=None,expected_added=None,provenance=None):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",created):raise ValueError("Invalid SPDX creation date")
    datetime.strptime(created,'%Y-%m-%dT%H:%M:%SZ')
    files=[];relationships=[];packages=[];identifiers=set();maps={};sha1s={}
    def file(name,data,comment=None):
        identifier='SPDXRef-file-'+hashlib.sha256(name.encode()).hexdigest()
        if identifier in identifiers:raise ValueError('Duplicate SPDX file identifier')
        identifiers.add(identifier);maps[name]=identifier;sha1s[identifier]=hashlib.sha1(data).hexdigest()
        record={'SPDXID':identifier,'fileName':'./'+name,'checksums':[{'algorithm':'SHA256','checksumValue':hashlib.sha256(data).hexdigest()},{'algorithm':'SHA1','checksumValue':sha1s[identifier]}],'licenseConcluded':'NOASSERTION','licenseInfoInFiles':['NOASSERTION'],'copyrightText':'NOASSERTION'}
        if comment:record['comment']=comment
        files.append(record);return identifier
    def package(identifier,name,version,ids,comment):
        if not ids:raise ValueError('Empty analyzed package')
        record={'SPDXID':identifier,'name':name,'downloadLocation':'NOASSERTION','filesAnalyzed':True,'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION','copyrightText':'NOASSERTION','packageVerificationCode':{'packageVerificationCodeValue':hashlib.sha1(''.join(sorted(sha1s[i] for i in ids)).encode('ascii')).hexdigest()},'comment':comment}
        if version is not None:record['versionInfo']=version
        packages.append(record)
        for fid in ids:relationships.append({'spdxElementId':identifier,'relationshipType':'CONTAINS','relatedSpdxElement':fid})
    physical=[];runtime=[];buffers={};prefix=app.name+'/'
    for name,h in sorted(manifest['files'].items()):
        data=(app/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Bundle file changed')
        buffers[name]=data
        fid=file(prefix+name,data);physical.append(fid)
        if name.startswith('Contents/PlugIns/Runtime.jdk/'):runtime.append(fid)
    jar=app/'Contents/Resources/RAID_Admin.jar';entryprefix=prefix+'Contents/Resources/RAID_Admin.jar!/'
    jar_bytes=buffers['Contents/Resources/RAID_Admin.jar']
    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate JAR entry')
        normalized=set()
        for item in z.infolist():
            name=item.filename.rstrip('/')
            key=unicodedata.normalize('NFD',unicodedata.normalize('NFD',name).casefold())
            if (not name or name.startswith('/') or any(part in ('','..','.') for part in name.split('/')) or '\\' in name or '!/' in name or any(ord(c)<32 for c in name) or key in normalized or (item.is_dir() and item.file_size)):
                raise ValueError('Unsafe or ambiguous JAR member')
            normalized.add(key)
        entries={n:z.read(n) for n in names if not n.endswith('/')}
    original_hashes={n:h for c in components for n,h in c['files'].items()}
    modified={n for n,h in original_hashes.items() if n in entries and hashlib.sha256(entries[n]).hexdigest()!=h}
    if expected_modified is not None and modified!=expected_modified:raise ValueError('Modified original member set differs')
    additions=set(entries)-set(original_hashes)
    if expected_added is not None and additions!=expected_added:raise ValueError('Added member set differs')
    entry_ids={n:file(entryprefix+n,data,'Virtual uncompressed archive member.'+(' Compatibility override; original member SHA256='+original_hashes[n]+'.' if n in modified else ' Original member unchanged.' if n in original_hashes else ' Compatibility addition.')) for n,data in sorted(entries.items())}
    package('SPDXRef-application','RAID Admin',manifest['compatibility_version'],physical,'Unsigned local preservation candidate. Original Apple 1.5.1 JAR reference SHA256 '+manifest['original_jar_sha256']+'. No controller, native UI or release acceptance implied. Licenses/redistribution rights unresolved; NOASSERTION is not a license grant.')
    package('SPDXRef-runtime',manifest['bundled_runtime']['vendor'],manifest['bundled_runtime']['version'],runtime,'Actual bundled vendor runtime files; vendor signature verified separately. License conclusions are not inferred from bundled notices.')
    package('SPDXRef-jar','RAID_Admin.jar',manifest['compatibility_version'],list(entry_ids.values()),'Archive members analyzed; package verification code hashes their uncompressed SHA1 values. Archive checksum is recorded on the separate physical JAR file.')
    packages[-1]['packageFileName']='./'+entryprefix[:-2]
    packages[-1]['checksums']=[{'algorithm':'SHA256','checksumValue':hashlib.sha256(jar_bytes).hexdigest()},{'algorithm':'SHA1','checksumValue':hashlib.sha1(jar_bytes).hexdigest()}]
    packages[1]['downloadLocation']=manifest['bundled_runtime'].get('archive_url','NOASSERTION')
    covered=set()
    for index,component in enumerate(components):
        names=set(component['files'])
        if covered&names or not names<=set(entries):raise ValueError('Component membership overlaps or omits shipped entries')
        covered|=names
        package('SPDXRef-component-'+str(index),component['name'],((component.get('version') or 'upstream version unresolved')+' + compatibility '+manifest['compatibility_version']) if names&modified else component.get('version'),[entry_ids[n] for n in sorted(names)],'Classification and observed version from original project SBOM; current member bytes are measured here. May include narrow compatibility overrides. Upstream exact version may remain unresolved; no upstream distribution checksum or license grant is asserted.')
        relationships.append({'spdxElementId':'SPDXRef-jar','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-component-'+str(index)})
    extra=set(entries)-covered
    package('SPDXRef-compatibility','RAID Admin compatibility additions',manifest['compatibility_version'],[entry_ids[n] for n in sorted(extra)],'Added compatibility classes/resources only; overridden original members remain in their original component classifications.')
    relationships += [{'spdxElementId':'SPDXRef-DOCUMENT','relationshipType':'DESCRIBES','relatedSpdxElement':'SPDXRef-application'},{'spdxElementId':'SPDXRef-application','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-runtime'},{'spdxElementId':'SPDXRef-application','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-jar'},{'spdxElementId':'SPDXRef-jar','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-compatibility'}]
    doc={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'RAID Admin '+manifest['compatibility_version']+' '+manifest['bundled_runtime']['architecture'],'creationInfo':{'created':created,'creators':['Tool: RAID-Admin-spdx-1']},'packages':packages,'files':files,'relationships':relationships,'comment':'Physical app bundle files and virtual uncompressed JAR entries are distinguished by !/ names. NOASSERTION preserves unresolved license/version evidence; metadata license does not change software licenses.'}
    if provenance:doc['creationInfo']['comment']=json.dumps(provenance,sort_keys=True,separators=(',',':'))
    doc['comment']+=' Files may belong to both their container and component package; paths are relative to the bundle-output directory. The explicit creation date is metadata input, not execution time.'
    doc['documentNamespace']='https://github.com/mav2287/xserve-raid-admin/spdx/'+digest(doc)
    return doc

def validate_semantics(document):
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z',document['creationInfo']['created']):raise ValueError('SPDX creation date differs')
    items=[document]+document['files']+document['packages'];ids=[item['SPDXID'] for item in items]
    if len(set(ids))!=len(ids) or any(not re.fullmatch(r'SPDXRef-[A-Za-z0-9.+-]+',name) for name in ids):raise ValueError('SPDX IDs differ')
    names=[f['fileName'] for f in document['files']]
    if len(set(names))!=len(names):raise ValueError('Duplicate SPDX file name')
    relations=document['relationships'];triples=[(r['spdxElementId'],r['relationshipType'],r['relatedSpdxElement']) for r in relations]
    if len(set(triples))!=len(triples) or sum(r['relationshipType']=='DESCRIBES' for r in relations)!=1:raise ValueError('SPDX relationships differ')
    if any(r['spdxElementId'] not in ids or r['relatedSpdxElement'] not in ids for r in relations):raise ValueError('Dangling SPDX relationship')
    values={}
    for file in document['files']:
        checks=file['checksums']
        if len(checks)!=2 or {c['algorithm'] for c in checks}!={'SHA1','SHA256'} or any(not re.fullmatch(r'[0-9a-f]{'+str(40 if c['algorithm']=='SHA1' else 64)+'}',c['checksumValue']) for c in checks):raise ValueError('SPDX file checksum syntax differs')
        values[file['SPDXID']]=next(c['checksumValue'] for c in checks if c['algorithm']=='SHA1')
    memberships={name:[] for name in values}
    for package in document['packages']:
        members=[r['relatedSpdxElement'] for r in relations if r['spdxElementId']==package['SPDXID'] and r['relationshipType']=='CONTAINS' and r['relatedSpdxElement'] in values]
        if not members or hashlib.sha1(''.join(sorted(values[m] for m in members)).encode()).hexdigest()!=package['packageVerificationCode']['packageVerificationCodeValue']:raise ValueError('SPDX verification code differs')
        for member in members:memberships[member].append(package['SPDXID'])
    for file in document['files']:
        members=memberships[file['SPDXID']]
        if not members or ('!/' in file['fileName'] and sum(name.startswith('SPDXRef-component-') or name=='SPDXRef-compatibility' for name in members)!=1):raise ValueError('SPDX membership differs')
    content=dict(document);namespace=content.pop('documentNamespace')
    if namespace!='https://github.com/mav2287/xserve-raid-admin/spdx/'+digest(content):raise ValueError('SPDX namespace differs')

def validate(document,cache):
    if not sys.flags.isolated or not sys.flags.no_site:raise ValueError('Use Python -I -S for isolated QA validation')
    verify_validator(cache);oldpath=list(sys.path);oldbytecode=sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode=True;sys.path.insert(0,str(cache.resolve()));before=set(sys.modules)
        import jsonschema,referencing,attrs,rpds,jsonschema_specifications
        stdlib=Path(sysconfig.get_paths()['stdlib']).resolve()
        for name,module in list(sys.modules.items()):
            if name in before and not name.startswith(('jsonschema','referencing','attrs','attr','rpds')):continue
            location=getattr(module,'__file__',None)
            if location:
                path=Path(location).resolve()
                if not path.is_relative_to(cache.resolve()) and not (path.is_relative_to(stdlib) and 'site-packages' not in path.parts):raise ValueError('Validator module origin differs')
        schema=json.loads((ROOT/'audit/spdx-2.3.1-schema.json').read_text())
        def deny(uri):raise ValueError('External schema retrieval prohibited')
        jsonschema.Draft201909Validator.check_schema(schema)
        validator=jsonschema.Draft201909Validator(schema,registry=referencing.Registry(retrieve=deny))
        if list(validator.iter_errors(document)):raise ValueError('SPDX schema validation failed; detail withheld')
        validate_semantics(document);verify_validator(cache)
    finally:sys.path[:]=oldpath;sys.dont_write_bytecode=oldbytecode

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--validator',type=Path,required=True);p.add_argument('--created',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--self-test',action='store_true');a=p.parse_args();verify_python()
    if a.output.exists() or a.output.is_symlink() or a.output.resolve().is_relative_to(a.bundle.resolve()) or a.output.resolve().is_relative_to(a.source.resolve()) or a.output.resolve().is_relative_to(a.validator.resolve()):raise ValueError('SBOM output exists or overlaps inputs')
    initial=clean_state()
    input_paths=[ROOT/n for n in ('tools/spdx.py','tools/spdx_validator.py','tools/audit_support.py','tools/runtime.py','tools/verify_bundles.py','tools/verify_builds.py','tools/baseline.py','tools/help_patch.py','tools/model_diagnostic_patch.py','audit/model-diagnostic-patches.json','tools/class_patch.py','tools/sync_ownership_patch.py','audit/sbom.json','audit/spdx-2.3.1-schema.json','audit/spdx-validator-lock.json','audit/runtime-lock.json','audit/expected-build.json','audit/python-lock.json')]
    inputs={str(path.relative_to(ROOT)):sha(path) for path in input_paths}
    manifest_bytes=(a.bundle/'provenance.json').read_bytes();source_bytes=(a.source/'provenance.json').read_bytes();manifest=json.loads(manifest_bytes)
    if manifest.get('source_dirty') is not False or manifest.get('packager_dirty') is not False:raise ValueError('Clean packaged artifact required')
    measured=check_bundle(a.bundle,a.source)
    lock=verify_validator(a.validator)
    if sha(ROOT/'audit/sbom.json')!=lock['original_sbom_sha256']:raise ValueError('Original SBOM classification differs')
    inventory=json.loads((ROOT/'audit/sbom.json').read_text())
    if inventory['jar_sha256']!=manifest['original_jar_sha256']:raise ValueError('Original SBOM/JAR provenance differs')
    from baseline import ALLOWED_JAR_CHANGES
    original_names={name for component in inventory['components'] for name in component['files']}
    provenance={'execution_state':initial,'source_dirty':False,'packager_dirty':False,'negative_controls':12 if a.self_test else 0,'source_commit':manifest['source_commit'],'packager_commit':manifest['packager_commit'],'source_hashes':inputs,'bundle_tree_sha256':manifest['bundle_tree_sha256'],'validator_tree_sha256':lock['tree_sha256']}
    document=generate(a.bundle/'RAID Admin.app',manifest,a.created,inventory['components'],(ALLOWED_JAR_CHANGES|{'META-INF/MANIFEST.MF'})&original_names,(ALLOWED_JAR_CHANGES|{'META-INF/MANIFEST.MF'})-original_names,provenance);validate(document,a.validator)
    if a.self_test:
        mutations=[]
        for operation in range(12):
            bad=copy.deepcopy(document)
            if operation==0:bad['files'][0]['SPDXID']=bad['files'][1]['SPDXID']
            elif operation==1:bad['relationships'][0]['relatedSpdxElement']='SPDXRef-missing'
            elif operation==2:bad['packages'][0]['packageVerificationCode']['packageVerificationCodeValue']='0'*40
            elif operation==3:bad['files'][0]['checksums']=bad['files'][0]['checksums'][:1]
            elif operation==4:bad['files'][0]['checksums'][0]['checksumValue']='A'*64
            elif operation==5:bad['files'][0]['checksums'][0]['checksumValue']='a'
            elif operation==6:bad['relationships'].append(dict(bad['relationships'][0]))
            elif operation==7:bad['relationships']=[r for r in bad['relationships'] if r['relationshipType']!='DESCRIBES']
            elif operation==8:bad['documentNamespace']='https://example.invalid/mismatch'
            elif operation==9:bad['files'][0]['SPDXID']+='\n'
            elif operation==10:bad['unknownSchemaProperty']=True
            else:bad['creationInfo']['created']+='\n'
            try:validate(bad,a.validator)
            except ValueError:mutations.append(operation)
            else:raise ValueError('SPDX negative control accepted')
        if len(mutations)!=12:raise ValueError('SPDX controls incomplete')
    app=a.bundle/'RAID Admin.app'
    if measured!={'files':tree(app),'file_modes':{n:(app/n).stat().st_mode&0o7777 for n in manifest['files']},'directory_modes':directory_modes(app)} or (a.bundle/'provenance.json').read_bytes()!=manifest_bytes or (a.source/'provenance.json').read_bytes()!=source_bytes or inputs!={str(path.relative_to(ROOT)):sha(path) for path in input_paths} or clean_state()!=initial:raise ValueError('SBOM inputs changed')
    with tempfile.TemporaryDirectory(prefix='.raid-spdx-',dir=a.output.parent) as t:
        staged=Path(t)/'document.json'
        with staged.open('x') as out:out.write(json.dumps(document,sort_keys=True,indent=2)+'\n');out.flush();os.fsync(out.fileno())
        os.link(staged,a.output)
    print('PASS SPDX 2.3 schema, provenance, measured file inventory and semantic checks; offline validation')
if __name__=='__main__':main()
