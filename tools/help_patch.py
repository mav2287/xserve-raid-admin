"""Exact original UI invocation substitutions; no controller or normal-action event-flow changes."""
import hashlib
from class_patch import ClassFile, word, u2
from sync_ownership_patch import method_code, compose, utf, pool_boundary
TARGETS = {
 'com/apple/xsr/RaidAdmin$HelpListener.class': ('1dea3b8e439a54901dbce7a0daa78e0df6b7d46e02b180e8589cdc23ae1884bf', 'actionPerformed', '(Ljava/awt/event/ActionEvent;)V', 5, 4, 19, 34),
 'com/apple/xsr/SystemMonitorController$UnsupportedOperationDialog.class': ('ff7980a5c9abb60e270caed19092772537daef348a8cfac61982054599da6aac', 'hyperlinkUpdate', '(Ljavax/swing/event/HyperlinkEvent;)V', 14, 68, 190, 281),
}

def extra(count, nat):
    return utf('compat/HelpLauncher') + b'\x07' + word(count) + b'\x0a' + word(count+1) + word(nat)

def plan(entry, data):
    pin, name, descriptor, pc, old_ref, nat, count = TARGETS[entry]
    if hashlib.sha256(data).hexdigest() != pin: raise ValueError('Exact original UI class required')
    c = ClassFile(data); b, e = method_code(c, name, descriptor)
    at = b+14+pc
    if c.pool_count != count or data[at:at+3] != b'\xb8'+word(old_ref):
        raise ValueError('Original browser invocation differs')
    return compose(data, c, [(at+1, at+3, word(count+2))], count+3, extra(count, nat))

def normalize(entry, data):
    pin, name, descriptor, pc, old_ref, nat, count = TARGETS[entry]
    c = ClassFile(data); b, e = method_code(c, name, descriptor); at = b+14+pc
    cut = pool_boundary(c, count)
    if c.pool_count != count+3 or data[cut:c.pool_end] != extra(count, nat) or data[at:at+3] != b'\xb8'+word(count+2):
        raise ValueError('Exact helper pool/invocation differs')
    old = compose(data,c,[(at+1,at+3,word(old_ref))],count,keep_end=cut)
    if hashlib.sha256(old).hexdigest() != pin or plan(entry,old) != data:
        raise ValueError('UI class differs outside the two-byte invocation operand')
    return old

def strip_entries(entries):
    """Comparator only: reverse exactly the locked UI extension, retain all other bytes."""
    import json
    from pathlib import Path
    lock=json.loads((Path(__file__).resolve().parents[1]/'audit/help-patches.json').read_text())
    helpers=lock['helpers'];present=set(helpers)&set(entries)
    if not present:return dict(entries)
    if present!=set(helpers) or any(hashlib.sha256(entries[n]).hexdigest()!=h for n,h in helpers.items()):
        raise ValueError('Incomplete or altered Help helper extension')
    result={n:v for n,v in entries.items() if n not in helpers}
    for entry in TARGETS:result[entry]=normalize(entry,result[entry])
    return result
