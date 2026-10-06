"""Exact audit21-to-audit22 pre-send stop guard; whole-class reversible."""
import hashlib,struct
from class_patch import ClassFile,u2,u4,word
from sync_ownership_patch import method_code,code_attribute,compose
def jump(at,to):return b'\xc8'+struct.pack('>i',to-at)
PIN='bc6ff5078249e584dd81f102799b0c10870d8e37b194b48c3e39dd722c45eda6'
OLD=bytes.fromhex('2a04b5019e')
TAIL=b'\x2a\xb4\x00\x0b\x9a'+struct.pack('>h',280-713)+OLD+jump(721,649)
ROWS=((709,726,462,69),(709,726,337,35),(709,726,462,76),(709,726,525,79))
def plan(data):
 if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('Exact audit21 Manager required')
 c=ClassFile(data);b,e=method_code(c,'dispatchLoop','()V');code=bytearray(data[b+14:b+14+709]);table=data[b+14+709:e]
 if (c.pool_count,len(c.fields),len(c.methods),u4(data,b+10),u2(table,0))!=(433,14,15,709,24) or code[644:649]!=OLD:raise ValueError('Pre-send seam differs')
 code[644:649]=jump(644,709);code.extend(TAIL)
 if len(code)!=726 or len(TAIL)!=17:raise ValueError('Stop guard layout differs')
 table=word(28)+table[2:-2]+b''.join(struct.pack('>HHHH',*row) for row in ROWS)+table[-2:]
 return compose(data,c,[(b,e,code_attribute(data[b:e],data[b+6:b+10],bytes(code),table))],c.pool_count)
def normalize(data):
 c=ClassFile(data);b,e=method_code(c,'dispatchLoop','()V')
 if u4(data,b+10)!=726:raise ValueError('Stop guard Code differs')
 code=bytearray(data[b+14:b+14+709]);code[644:649]=OLD;table=data[b+14+726:e]
 if u2(table,0)!=28:raise ValueError('Stop guard handlers differ')
 table=word(24)+table[2:-34]+table[-2:]
 restored=compose(data,c,[(b,e,code_attribute(data[b:e],data[b+6:b+10],bytes(code),table))],c.pool_count)
 if hashlib.sha256(restored).hexdigest()!=PIN or plan(restored)!=data:raise ValueError('Stop guard reconstruction differs')
 return restored
