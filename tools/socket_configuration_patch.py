"""Exact original HttpConnection -> initial read-timeout safety delegate."""
import hashlib
from class_patch import ClassFile,word
from sync_ownership_patch import compose,method_code,code_attribute,pool_boundary,utf
ENTRY='com/apple/xsr/net/HttpConnection.class'
PIN='c8a632a9c5c76e94fe1c3a9e23b6e362d8e50fff75eeb26ee7379ab6c7159303'
OLD=bytes.fromhex('00580000003c00050003000000282abb0031592ab4000d1050b70032b5001a2ab4001a2ab40009b60022a7000b4db2001d2cb60033b100010011001c001f00230000')
POOL=utf('compat/SocketConfiguration')+b'\x07'+word(198)+utf('(Ljava/lang/String;I)Ljava/net/Socket;')+b'\x0c'+word(100)+word(200)+b'\x0a'+word(199)+word(201)
CODE=bytes.fromhex('2a2ab4000d2ab40009b800cab5001ab1')
def plan(data):
 if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('Exact original HttpConnection required')
 c=ClassFile(data);b,e=method_code(c,'createSocket','(I)V')
 if (c.pool_count,len(c.fields),len(c.methods))!=(198,14,19) or data[b:e]!=OLD:raise ValueError('Socket setup predecessor shape differs')
 replacement=code_attribute(OLD,word(3)+word(2),CODE,word(0)+word(0))
 return compose(data,c,[(b,e,replacement)],203,POOL)
def normalize(data):
 c=ClassFile(data);b,e=method_code(c,'createSocket','(I)V');end=pool_boundary(c,198)
 if c.pool_count!=203 or data[end:c.pool_end]!=POOL:raise ValueError('Socket setup pool differs')
 restored=compose(data,c,[(b,e,OLD)],198,keep_end=end)
 if hashlib.sha256(restored).hexdigest()!=PIN or plan(restored)!=data:raise ValueError('Socket setup is not exact reversible substitution')
 return restored
