"""Explicit bridge from frozen clean product to reviewed packaging-only revisions."""
import hashlib,json,subprocess
from pathlib import Path
import secure_build
from audit_support import ROOT,sha,isolated_env
PRODUCT_COMMIT='e005b9a2877133d98af4cf86fd5b625532b06fcb'
MANIFESTS={'0f697d42502c2493d460faf87a2c727903853f288005522e0c66b5150426b35e','fbbd90ceda92a0d4429411437886ee7c29330d74c3fdf5cc69bc6c32f03e2819'}
ADDITIONS={'tools/historical_secure.py','tools/secure_release.py','tools/check_secure_release.py','tools/secure_release_gate.py','audit/SECURE-PREFERENCES.md','audit/claude-review/SECURE-RELEASE-QUALIFICATION-FOLLOWUP.txt','audit/claude-review/SECURE-RELEASE-BRIDGE.txt','audit/claude-review/SECURE-RELEASE-FINAL.txt'}

def check_historical_artifact(output):
    initial=secure_build.state()
    if initial['dirty']:raise ValueError('Clean release bridge source required')
    manifest=output/'provenance.json';anchor=sha(manifest)
    record=json.loads(manifest.read_bytes())
    if record['source_commit']==initial['commit']:
        identity,verified=secure_build.check_secure_artifact(output)
        return identity,verified,{'scope':'Current clean-source artifact verified directly','execution_commit':initial['commit'],'product_source_commit':initial['commit'],'product_manifest_sha256':anchor}
    if anchor not in MANIFESTS or record['source_commit']!=PRODUCT_COMMIT or record['source_dirty']:raise ValueError('Unrecognized frozen clean secure product')
    subprocess.check_call(['/usr/bin/git','merge-base','--is-ancestor',PRODUCT_COMMIT,'HEAD'],cwd=ROOT,env=isolated_env())
    raw=subprocess.check_output(['/usr/bin/git','diff','--no-renames','--name-status','-z',PRODUCT_COMMIT,'HEAD'],cwd=ROOT,env=isolated_env()).decode().split('\0')
    if raw[-1]!='' or len(raw)%2!=1:raise ValueError('Malformed Git change inventory')
    changes=[]
    for status,name in zip(raw[:-1:2],raw[1:-1:2]):
        if status!='A' or not (name in ADDITIONS or (name.startswith('audit/secure-release/') and Path(name).suffix in {'.json','.txt'})):raise ValueError('Release bridge permits only reviewed additions: '+name)
        current=sha(ROOT/name)
        data=subprocess.check_output(['/usr/bin/git','show','HEAD:'+name],cwd=ROOT,env=isolated_env())
        if hashlib.sha256(data).hexdigest()!=current:raise ValueError('Added release input differs from HEAD: '+name)
        changes.append({'status':status,'path':name,'sha256':current})
    proofs={}
    for name,expected in record['input_hashes'].items():
        if name.startswith('/') or '..' in Path(name).parts:raise ValueError('Unsafe source provenance path')
        data=subprocess.check_output(['/usr/bin/git','show',PRODUCT_COMMIT+':'+name],cwd=ROOT,env=isolated_env())
        if hashlib.sha256(data).hexdigest()!=expected or sha(ROOT/name)!=expected:raise ValueError('Product source differs from historical Git: '+name)
        proofs[name]=expected
    identity,verified=secure_build.check_secure_artifact(output)
    if sha(manifest)!=anchor or secure_build.state()!=initial:raise ValueError('Release bridge input changed')
    bridge={'product_source_commit':PRODUCT_COMMIT,'execution_commit':initial['commit'],'product_manifest_sha256':anchor,'reviewed_tree_additions':changes,'historical_input_proofs':proofs,'checker_sha256':sha(ROOT/'tools/secure_build.py'),'bridge_sha256':sha(ROOT/'tools/historical_secure.py'),'scope':'Unmodified complete artifact checker; no hash substitutions. Original tools/source remain byte-identical; release tools and audit evidence are additions only.'}
    return identity,verified,bridge
