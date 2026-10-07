"""Exact/reversible memory-only hook at pre-exposure seam, after SyncSender claim."""
import zipfile,hashlib,struct
from pathlib import Path
from class_patch import ClassFile,transform,word,u4,u2
from sync_ownership_patch import compose,method_code,utf,pool_boundary,code_attribute
from sync_ownership_patch import transform_manager
from worker_exit_patch import plan as worker_plan
from stop_admission_patch import plan,normalize,PIN,jump,OLD
ENTRY='com/apple/xsr/net/CommunicationsManager.class'
JAR='9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562'
ORIGINAL='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
TAIL=utf('com/apple/xsr/net/StopExposureObservation')+b'\x07'+word(433)+utf('pause')+utf('(Lcom/apple/xsr/net/CommunicationsManager;)V')+b'\x0c'+word(435)+word(436)+b'\x0a'+word(434)+word(437)
def hash(data):return hashlib.sha256(data).hexdigest()
def hook(data):
 c=ClassFile(data);b,e=method_code(c,'dispatchLoop','()V');length=u4(data,b+10);code=bytearray(data[b+14:b+14+length]);table=data[b+14+length:e]
 expected=OLD if length==709 else jump(644,709)
 if c.pool_count!=433 or length not in (709,726) or code[644:649]!=expected:raise ValueError('Exposure seam differs')
 code[644:649]=jump(644,length);extra=b'\x2a\xb8'+word(438)+(OLD+jump(length+9,649) if length==709 else jump(length+4,709));code.extend(extra)
 rows=[(length,len(code),target,kind) for target,kind in ((462,69),(337,35),(462,76),(525,79))]
 table=word(u2(table,0)+4)+table[2:-2]+b''.join(struct.pack('>HHHH',*r) for r in rows)+table[-2:]
 return compose(data,c,[(b,e,code_attribute(data[b:e],data[b+6:b+10],bytes(code),table))],439,TAIL)
def unhook(data,reference):
 c=ClassFile(data);b,e=method_code(c,'dispatchLoop','()V');rc=ClassFile(reference);rb,re=method_code(rc,'dispatchLoop','()V');length=u4(reference,rb+10);end=pool_boundary(c,433)
 code=bytearray(data[b+14:b+14+length]);code[644:649]=reference[rb+14+644:rb+14+649];table=data[b+14+u4(data,b+10):e]
 restored=compose(data,c,[(b,e,code_attribute(data[b:e],data[b+6:b+10],bytes(code),word(u2(table,0)-4)+table[2:-34]+table[-2:]))],433,keep_end=end)
 if restored!=reference or hook(restored)!=data:raise ValueError('Whole exposure hook differs')
 return restored
def write_fixture(path,entries,manager):
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
  for name,value in sorted(entries.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=(0o40755<<16)|0x10 if name.endswith('/') else 0o100644<<16
   z.writestr(info,manager if name==ENTRY else value)
def build(reference,out,*,basis=None):
 reference=Path(reference);out=Path(out)
 if hash(reference.read_bytes())!=JAR:raise ValueError('Unreviewed reference JAR')
 original=Path('original/RAID_Admin_original.jar')
 if hash(original.read_bytes())!=ORIGINAL:raise ValueError('Original changed')
 with zipfile.ZipFile(original) as z:source=worker_plan(transform_manager(transform(ENTRY,z.read(ENTRY))))
 with zipfile.ZipFile(reference) as z:
  names=z.namelist()
  if len(names)!=len(set(names)):raise ValueError('Duplicate reference entries')
  entries={n:z.read(n) for n in names}
 if source!=entries[ENTRY] or hash(source)!=PIN:raise ValueError('Source-reference mismatch')
 guarded=plan(source)
 if normalize(guarded)!=source:raise ValueError('Guard reconstruction differs')
 if basis is not None:
  from stop_admission_fixtures import select_basis
  entries=select_basis(entries,guarded,basis)
 result={}
 for name,data in [('legacy',source),('guarded',guarded)]:
  patched=hook(data);unhook(patched,data);path=out/(name+'-exposure-fixture.jar')
  write_fixture(path,entries,patched)
  with zipfile.ZipFile(path) as z:
   if set(z.namelist())!=set(entries) or any(z.read(n)!=v for n,v in entries.items() if n!=ENTRY):raise ValueError('Non-Manager fixture changes')
   unhook(z.read(ENTRY),data)
  result[name]=path
 return result
