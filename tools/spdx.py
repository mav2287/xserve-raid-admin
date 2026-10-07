#!/usr/bin/env python3
"""Deterministic SPDX 2.3 bundle/JAR-entry inventory, schema and hash validation."""
import argparse,hashlib,json,re,sys,zipfile
from datetime import datetime
from pathlib import Path
from audit_support import ROOT,sha,tree,verify_python,digest
from runtime import directory_modes
from verify_bundles import check_bundle
from spdx_validator import verify as verify_validator

def generate(app,manifest,created,components):
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
        record={'SPDXID':identifier,'name':name,'downloadLocation':'NOASSERTION','filesAnalyzed':True,'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION','copyrightText':'NOASSERTION','packageVerificationCode':{'packageVerificationCodeValue':hashlib.sha1(''.join(sorted(sha1s[i] for i in ids)).encode('ascii')).hexdigest()},'comment':comment}
        if version is not None:record['versionInfo']=version
        packages.append(record)
        for fid in ids:relationships.append({'spdxElementId':identifier,'relationshipType':'CONTAINS','relatedSpdxElement':fid})
    physical=[];runtime=[];prefix=app.name+'/'
    for name,h in sorted(manifest['files'].items()):
        data=(app/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Bundle file changed')
        fid=file(prefix+name,data);physical.append(fid)
        if name.startswith('Contents/PlugIns/Runtime.jdk/'):runtime.append(fid)
    jar=app/'Contents/Resources/RAID_Admin.jar';entryprefix=prefix+'Contents/Resources/RAID_Admin.jar!/'
    with zipfile.ZipFile(jar) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate JAR entry')
        entries={n:z.read(n) for n in names if not n.endswith('/')}
    entry_ids={n:file(entryprefix+n,data,'Virtual archive member; checksum covers uncompressed bytes of this entry in the shipped JAR.') for n,data in sorted(entries.items())}
    package('SPDXRef-application','RAID Admin',manifest['compatibility_version'],physical,'Unsigned local preservation candidate. Original Apple 1.5.1 JAR reference SHA256 '+manifest['original_jar_sha256']+'. No controller, native UI or release acceptance implied. Licenses/redistribution rights unresolved; NOASSERTION is not a license grant.')
    package('SPDXRef-runtime',manifest['bundled_runtime']['vendor'],manifest['bundled_runtime']['version'],runtime,'Actual bundled vendor runtime files; vendor signature verified separately. License conclusions are not inferred from bundled notices.')
    package('SPDXRef-jar','RAID_Admin.jar',manifest['compatibility_version'],list(entry_ids.values()),'Archive members analyzed; package verification code hashes their uncompressed SHA1 values. Archive checksum is recorded on the separate physical JAR file.')
    covered=set()
    for index,component in enumerate(components):
        names=set(component['files'])
        if covered&names or not names<=set(entries):raise ValueError('Component membership overlaps or omits shipped entries')
        covered|=names
        package('SPDXRef-component-'+str(index),component['name'],component.get('version'),[entry_ids[n] for n in sorted(names)],'Classification and observed version from original project SBOM; current member bytes are measured here. May include narrow compatibility overrides. Upstream exact version may remain unresolved; no upstream distribution checksum or license grant is asserted.')
        relationships.append({'spdxElementId':'SPDXRef-jar','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-component-'+str(index)})
    extra=set(entries)-covered
    package('SPDXRef-compatibility','RAID Admin compatibility additions',manifest['compatibility_version'],[entry_ids[n] for n in sorted(extra)],'Added compatibility classes/resources only; overridden original members remain in their original component classifications.')
    relationships += [{'spdxElementId':'SPDXRef-DOCUMENT','relationshipType':'DESCRIBES','relatedSpdxElement':'SPDXRef-application'},{'spdxElementId':'SPDXRef-application','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-runtime'},{'spdxElementId':'SPDXRef-application','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-jar'},{'spdxElementId':'SPDXRef-jar','relationshipType':'CONTAINS','relatedSpdxElement':'SPDXRef-compatibility'}]
    doc={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'RAID Admin '+manifest['compatibility_version']+' '+manifest['bundled_runtime']['architecture'],'creationInfo':{'created':created,'creators':['Tool: RAID-Admin-spdx-1']},'packages':packages,'files':files,'relationships':relationships,'comment':'Physical app bundle files and virtual uncompressed JAR entries are distinguished by !/ names. NOASSERTION preserves unresolved license/version evidence; metadata license does not change software licenses.'}
    doc['documentNamespace']='https://github.com/mav2287/xserve-raid-admin/spdx/'+digest(doc)
    return doc

def validate(document,cache):
    verify_validator(cache);sys.dont_write_bytecode=True;sys.path.insert(0,str(cache.resolve()))
    import jsonschema,referencing,attrs,rpds,jsonschema_specifications
    for module in (jsonschema,referencing,attrs,rpds,jsonschema_specifications):
        if not Path(module.__file__).resolve().is_relative_to(cache.resolve()):raise ValueError('Validator module origin differs')
    schema=json.loads((ROOT/'audit/spdx-2.3.1-schema.json').read_text())
    def deny(uri):raise ValueError('External schema retrieval prohibited')
    registry=referencing.Registry(retrieve=deny)
    validator=jsonschema.Draft201909Validator(schema,registry=registry)
    if list(validator.iter_errors(document)):raise ValueError('SPDX schema validation failed; detail withheld')
    ids={document['SPDXID']}|{item['SPDXID'] for group in ('files','packages') for item in document[group]}
    if len(ids)!=1+len(document['files'])+len(document['packages']):raise ValueError('Duplicate SPDX ID')
    for relation in document['relationships']:
        if relation['spdxElementId'] not in ids or relation['relatedSpdxElement'] not in ids:raise ValueError('Dangling SPDX relationship')
    values={f['SPDXID']:next(c['checksumValue'] for c in f['checksums'] if c['algorithm']=='SHA1') for f in document['files']}
    for package in document['packages']:
        members=[r['relatedSpdxElement'] for r in document['relationships'] if r['spdxElementId']==package['SPDXID'] and r['relationshipType']=='CONTAINS' and r['relatedSpdxElement'] in values]
        if hashlib.sha1(''.join(sorted(values[m] for m in members)).encode()).hexdigest()!=package['packageVerificationCode']['packageVerificationCodeValue']:raise ValueError('SPDX package verification code differs')
    verify_validator(cache)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--validator',type=Path,required=True);p.add_argument('--created',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify_python()
    if a.output.exists() or a.output.is_symlink() or a.output.resolve().is_relative_to(a.bundle.resolve()) or a.output.resolve().is_relative_to(a.source.resolve()):raise ValueError('SBOM output exists or overlaps inputs')
    measured=check_bundle(a.bundle,a.source);manifest_bytes=(a.bundle/'provenance.json').read_bytes();manifest=json.loads(manifest_bytes);inventory=json.loads((ROOT/'audit/sbom.json').read_text())
    document=generate(a.bundle/'RAID Admin.app',manifest,a.created,inventory['components']);validate(document,a.validator)
    app=a.bundle/'RAID Admin.app'
    if measured!={'files':tree(app),'file_modes':{n:(app/n).stat().st_mode&0o7777 for n in manifest['files']},'directory_modes':directory_modes(app)} or (a.bundle/'provenance.json').read_bytes()!=manifest_bytes:raise ValueError('Bundle changed during SBOM generation')
    with a.output.open('x') as out:out.write(json.dumps(document,sort_keys=True,indent=2)+'\n')
    print('PASS SPDX 2.3 schema, IDs, relationships, verification codes and exact bundle/JAR-entry hashes')
if __name__=='__main__':main()
