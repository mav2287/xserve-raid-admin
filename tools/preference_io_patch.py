"""Exact store-only stream-ownership boundary; all other class bytes preserved."""
import hashlib
from class_patch import ClassFile, word, u2, u4
from sync_ownership_patch import method_code, compose, utf, pool_boundary
ENTRY='com/apple/util/prefs/FileBasedPreferences.class'
ORIGINAL_SHA='9a9a41cf9982b5413dddec7f73c84bd644617b417e4602b53a551589de968d6d'
PATCHED_SHA='76935f031ec1555f7e2f267d74d32be46de8f39257d84f1fc34ae102fbdf3b5a'
EXTRA=utf('compat/PreferenceIO')+b'\x07'+word(82)+utf('write')+utf('(Ljava/lang/String;Ljava/lang/Object;)V')+b'\x0c'+word(84)+word(85)+b'\x0a'+word(83)+word(86)
WINDOW=bytes.fromhex('2ab400042ab40010b8')+word(87)+b'\0'*29
def shape(data,c,b):
    if data[6:8]!=word(47) or u4(data,b+10)!=62:raise ValueError('Exact preference class version/code length required')
    at=b+14+62
    if u2(data,at)!=3:raise ValueError('Preference exception handlers differ')
    expected=b''.join(word(v) for row in ((7,47,50,17),(7,53,56,0),(56,59,56,0)) for v in row)
    if data[at+2:at+26]!=expected:raise ValueError('Preference window exception coverage differs')
def plan(data):
    if hashlib.sha256(data).hexdigest()!=ORIGINAL_SHA:raise ValueError('Exact original preference backend required')
    c=ClassFile(data);b,_=method_code(c,'store','()V')
    shape(data,c,b)
    if c.pool_count!=82 or len(WINDOW)!=40:raise ValueError('Preference patch shape differs')
    result=compose(data,c,[(b+21,b+61,WINDOW)],88,EXTRA)
    if hashlib.sha256(result).hexdigest()!=PATCHED_SHA:raise ValueError("Preference override differs from reviewed bytes")
    return result
def normalize(data):
    c=ClassFile(data);b,_=method_code(c,'store','()V');cut=pool_boundary(c,82)
    shape(data,c,b)
    if c.pool_count!=88 or data[cut:c.pool_end]!=EXTRA or data[b+21:b+61]!=WINDOW:raise ValueError('Preference patch differs')
    # The original operand bytes are independently copied from the pinned reference.
    original=bytes.fromhex('bb001559bb001659bb0006592ab40004b70007b70017120cb700184d2ab400102cb800192cb6001a')
    old=compose(data,c,[(b+21,b+61,original)],82,keep_end=cut)
    if hashlib.sha256(old).hexdigest()!=ORIGINAL_SHA or plan(old)!=data:raise ValueError('Unexpected preference changes')
    return old


def strip_entries(entries):
    """Comparison only: remove exactly the hash-bound preference extension."""
    import json
    from pathlib import Path
    result=dict(entries)
    lock=json.loads((Path(__file__).resolve().parents[1]/'audit/preference-io-patches.json').read_text())
    if lock['entry']!=ENTRY or lock['original_sha256']!=ORIGINAL_SHA or lock['patched_sha256']!=PATCHED_SHA or lock['pool_counts']!=[82,88] or lock['store_window']!=[7,47] or set(lock['helpers'])!={'compat/PreferenceIO.class'}:raise ValueError('Preference lock shape differs')
    helpers=lock['helpers']
    present=set(helpers)&set(result)
    original=ENTRY not in result or hashlib.sha256(result[ENTRY]).hexdigest()==ORIGINAL_SHA
    if original:
        if present:raise ValueError('Preference helper without exact backend override')
        return result
    if present!=set(helpers) or any(hashlib.sha256(result[n]).hexdigest()!=h for n,h in helpers.items()):raise ValueError('Preference helper missing or altered')
    result[ENTRY]=normalize(result[ENTRY])
    for n in helpers:del result[n]
    return result
