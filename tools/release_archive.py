#!/usr/bin/env python3
"""Deterministic unsigned app ZIP and verified extraction; never installs or launches."""
import argparse,hashlib,json,stat,tempfile,zipfile,os,unicodedata,io,platform,subprocess,shutil
from audit_support import ROOT, isolated_env
from pathlib import Path,PurePosixPath
from audit_support import tree,modes,digest,sha,verify_python
from runtime import directory_modes,verify_runtime,runtime_manifest
from verify_bundles import check_bundle

def canonical(name):return unicodedata.normalize('NFD',unicodedata.normalize('NFD',name).casefold())

def clean_state():
    state={'commit':subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip(),'dirty':bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))}
    if state['dirty']:raise ValueError('Clean release preparation source required')
    return state

def snapshot(app):
    # tree/modes reject symlinks and non-regular files before any content is copied.
    return {'files':tree(app),'file_modes':modes(app),'directory_modes':directory_modes(app)}

def _write_archive(app,target):
    app,target=Path(app),Path(target);before=snapshot(app)
    if target.exists() or target.is_symlink():raise ValueError('Archive output exists')
    records={app.name+'/'+n:(False,before['file_modes'][n]) for n in before['files']}
    records.update({app.name+('/' if n=='.' else '/'+n+'/'):(True,m) for n,m in before['directory_modes'].items()})
    if len({canonical(n.rstrip('/')) for n in records})!=len(records):raise ValueError('Case-colliding archive entries')
    if any(mode&0o7022 for directory,mode in records.values()):raise ValueError('Unsafe source modes')
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_STORED) as z:
        for name,(directory,mode) in sorted(records.items()):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3
            info.external_attr=((stat.S_IFDIR if directory else stat.S_IFREG)|mode)<<16
            if directory:info.external_attr|=0x10
            data=b'' if directory else (app.parent/name).read_bytes()
            if not directory and hashlib.sha256(data).hexdigest()!=before['files'][name[len(app.name)+1:]]:raise ValueError('Source changed while archiving')
            z.writestr(info,data)
    if snapshot(app)!=before:raise ValueError('Source changed while archiving')
    return before

def write_archive(app,target):
    target=Path(target)
    if target.exists() or target.is_symlink():raise ValueError('Archive output exists')
    with tempfile.TemporaryDirectory(prefix='.raid-archive-',dir=target.parent) as t:
        staged=Path(t)/'candidate.zip';identity=_write_archive(app,staged)
        os.link(staged,target)  # Exclusive publication; never replaces an existing path.
        return identity

def _extract_archive(archive,destination,root):
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise ValueError('Extraction output exists')
    with zipfile.ZipFile(archive) as z:
        seen={};entries=z.infolist()
        for item in entries:
            p=PurePosixPath(item.filename);kind=stat.S_IFMT(item.external_attr>>16);mode=stat.S_IMODE(item.external_attr>>16)
            if (p.is_absolute() or not p.parts or p.parts[0]!=root or '..' in p.parts or
                canonical(str(p)) in seen or '\\' in item.filename or
                kind not in (stat.S_IFREG,stat.S_IFDIR) or mode&0o7022 or (kind==stat.S_IFDIR and mode&0o500!=0o500) or
                (kind==stat.S_IFDIR)!=item.is_dir() or item.filename!=str(p)+('/' if item.is_dir() else '') or
                item.compress_type!=zipfile.ZIP_STORED or item.compress_size!=item.file_size or item.flag_bits&1 or
                (item.is_dir() and item.file_size!=0)):raise ValueError('Unsafe app archive entry')
            seen[canonical(str(p))]=kind
        if seen.get(canonical(root))!=stat.S_IFDIR:raise ValueError('App root directory missing')
        for name in seen:
            parents=[str(parent) for parent in PurePosixPath(name).parents if str(parent)!='.']
            if any(seen.get(parent)==stat.S_IFREG for parent in parents):raise ValueError('Archive traverses regular file')
            if any(seen.get(parent)!=stat.S_IFDIR for parent in parents):raise ValueError('Explicit parent directory missing')
        destination.mkdir()
        for item in entries:
            path=destination/item.filename
            if item.is_dir():path.mkdir(parents=True,exist_ok=True)
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as out:out.write(z.read(item))
        # Restore read-only vendor modes after all children have been created.
        for item in sorted(entries,key=lambda i:len(PurePosixPath(i.filename).parts),reverse=True):(destination/item.filename).chmod(stat.S_IMODE(item.external_attr>>16))
    return destination/root

def extract_archive(archive,destination,root):
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise ValueError('Extraction output exists')
    try:return _extract_archive(archive,destination,root)
    except BaseException:
        if destination.exists():
            for path in [destination]+list(destination.rglob('*')):
                if path.is_dir():path.chmod(0o700)
            shutil.rmtree(destination)
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--record',type=Path,required=True);a=p.parse_args();verify_python()
    if a.output.exists() or a.output.is_symlink() or a.record.exists() or a.record.is_symlink():raise ValueError('Release output exists')
    source,bundle,output,record=[path.resolve() for path in (a.source,a.bundle,a.output,a.record)]
    if output==record or any(path.is_relative_to(root) for path in (output,record) for root in (source,bundle)):raise ValueError('Release paths overlap inputs or each other')
    initial=clean_state()
    paths=[ROOT/n for n in ('tools/release_archive.py','tools/audit_support.py','tools/runtime.py','tools/verify_bundles.py','tools/verify_builds.py','tools/baseline.py','tools/help_patch.py','tools/model_diagnostic_patch.py','tools/preference_io_patch.py','audit/preference-io-patches.json','audit/model-diagnostic-patches.json','tools/class_patch.py','tools/sync_ownership_patch.py','audit/runtime-lock.json','audit/python-lock.json','audit/expected-build.json','audit/help-patches.json')]
    sources={str(path.relative_to(ROOT)):sha(path) for path in paths}
    manifests={path:path.read_bytes() for path in (bundle/'provenance.json',source/'provenance.json')}
    if any(json.loads(data).get('source_dirty') is not False for data in manifests.values()) or json.loads(manifests[bundle/'provenance.json']).get('packager_dirty') is not False:raise ValueError('Clean source artifacts required')
    measured=check_bundle(bundle,source);app=bundle/'RAID Admin.app'
    provenance=json.loads(manifests[bundle/'provenance.json']);arch=provenance['bundled_runtime']['architecture']
    with tempfile.TemporaryDirectory(prefix='.raid-release-',dir=output.parent) as t, tempfile.TemporaryDirectory(prefix='.raid-record-',dir=record.parent) as rt:
        staged=Path(t)/'candidate.zip';identity=write_archive(app,staged)
        if measured!=identity:raise ValueError('Source bundle changed')
        archive_bytes=staged.read_bytes();archive_sha=hashlib.sha256(archive_bytes).hexdigest()
        extracted=extract_archive(io.BytesIO(archive_bytes),Path(t)/'extracted',app.name)
        if snapshot(extracted)!=identity:raise ValueError('Extracted archive differs')
        verify_runtime(extracted/'Contents/PlugIns/Runtime.jdk',runtime_manifest()['architectures'][arch])
        if sha(staged)!=archive_sha or snapshot(app)!=identity or sources!={str(path.relative_to(ROOT)):sha(path) for path in paths} or any(path.read_bytes()!=data for path,data in manifests.items()):raise ValueError('Release input changed during verification')
        state=clean_state()
        if state!=initial:raise ValueError('Release source state changed')
        metadata={'schema':1,'archive_sha256':archive_sha,'archive_bytes':len(archive_bytes),'bundle_tree_sha256':digest(identity),'architecture':arch,'bundle_provenance_sha256':hashlib.sha256(manifests[bundle/'provenance.json']).hexdigest(),'source_provenance_sha256':hashlib.sha256(manifests[source/'provenance.json']).hexdigest(),'source_hashes':sources,'execution_state':state,'python':platform.python_version(),'format':'ZIP_STORED; sorted POSIX names; 1980-01-01 timestamps; exact files and directory modes; no links or xattrs','extraction':'verified exact files/modes/directories and vendor signature','application_signing':None,'application_notarization':'not performed','limits':'Local unsigned distributable candidate; no Finder/Gatekeeper/controller or redistribution-rights acceptance'}
        staged_record=Path(rt)/'record.json';staged_record.write_text(json.dumps(metadata,sort_keys=True,indent=2)+'\n')
        os.link(staged,output)
        try:os.link(staged_record,record)
        except BaseException:
            if output.stat().st_ino==staged.stat().st_ino and output.stat().st_dev==staged.stat().st_dev:output.unlink()
            raise
    print('PASS deterministic unsigned archive and extraction; vendor runtime signature preserved')
if __name__=='__main__':main()
