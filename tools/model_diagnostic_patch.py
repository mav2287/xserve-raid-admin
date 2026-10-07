"""Hash-locked redaction of two diagnostic field reads; model state is unchanged."""
import hashlib
from class_patch import ClassFile, word
from sync_ownership_patch import method_code, compose, utf, pool_boundary

ENTRY = 'com/apple/xsr/som/RaidSystem.class'
ORIGINAL_SHA = '870f5f3ee880f1bfa1875a87f1dd3b4904f24cbd016a2eb4742c2cf4d627c632'
PATCHED_SHA = 'f2b2c2f5b7c3e3eb941c16436cb41f2a64b0630a6dabf722fb36470e11858f2c'
TOKEN = '<redacted>'
EXTRA = utf(TOKEN) + b'\x08' + word(1184)
WINDOW = b'\x13' + word(1185) + b'\x00'
ORIGINAL_WINDOWS = {156: bytes.fromhex('2ab4004a'), 190: bytes.fromhex('2ab4004b')}

def plan(data):
    if hashlib.sha256(data).hexdigest() != ORIGINAL_SHA:
        raise ValueError('Exact original RaidSystem required')
    c = ClassFile(data); b, _ = method_code(c, 'paramString', '()Ljava/lang/String;')
    if c.pool_count != 1184 or any(data[b+14+pc:b+18+pc] != v for pc, v in ORIGINAL_WINDOWS.items()):
        raise ValueError('Original model diagnostic windows differ')
    result = compose(data, c, [(b+14+pc, b+18+pc, WINDOW) for pc in ORIGINAL_WINDOWS], 1186, EXTRA)
    if hashlib.sha256(result).hexdigest() != PATCHED_SHA:
        raise ValueError('Model redaction differs from reviewed bytes')
    return result

def normalize(data):
    c = ClassFile(data); b, _ = method_code(c, 'paramString', '()Ljava/lang/String;'); cut = pool_boundary(c, 1184)
    if c.pool_count != 1186 or data[cut:c.pool_end] != EXTRA or any(data[b+14+pc:b+18+pc] != WINDOW for pc in ORIGINAL_WINDOWS):
        raise ValueError('Exact model redaction differs')
    old = compose(data, c, [(b+14+pc, b+18+pc, v) for pc, v in ORIGINAL_WINDOWS.items()], 1184, keep_end=cut)
    if hashlib.sha256(old).hexdigest() != ORIGINAL_SHA or plan(old) != data:
        raise ValueError('Model changes beyond exact diagnostic redaction')
    return old

def strip_entries(entries):
    """Comparison only. Accept the pinned original or exactly reversible override."""
    result = dict(entries)
    if ENTRY in result and hashlib.sha256(result[ENTRY]).hexdigest() != ORIGINAL_SHA:
        result[ENTRY] = normalize(result[ENTRY])
    return result
