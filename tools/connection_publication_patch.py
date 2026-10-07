"""Exact private Acpx createConnection override: publish only after open succeeds."""
import hashlib
from class_patch import ClassFile,word
from sync_ownership_patch import compose,method_code,code_attribute
ENTRY='com/apple/xsr/net/AcpxConnection.class'
PIN='5506cd12209500212af4af4810a5a7ac0245939f89b4b0df1bc5950778f12a0e'
OLD=bytes.fromhex('007a0000004000040001000000342ab4000ec700272abb0042592ab4000cb70043b5000e2ab4000e2ab40007b600442ab4000eb60045a7000bb2001c1246b60047b100000000')
CODE=bytes.fromhex('2ab4000ec70023bb0042592ab4000cb700434c2b2ab40007b600442bb600452a2bb5000ea7000bb2001c1246b60047b1')
def plan(data):
    if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('Exact audit23 Acpx required')
    c=ClassFile(data);b,e=method_code(c,'createConnection','()V')
    if data[b:e]!=OLD:raise ValueError('Original private connection method differs')
    return compose(data,c,[(b,e,code_attribute(OLD,word(3)+word(2),CODE,word(0)+word(0)))],c.pool_count)
def normalize(data):
    c=ClassFile(data);b,e=method_code(c,'createConnection','()V')
    old=compose(data,c,[(b,e,OLD)],c.pool_count)
    if hashlib.sha256(old).hexdigest()!=PIN or plan(old)!=data:raise ValueError('Exact connection publication reversal differs')
    return old
