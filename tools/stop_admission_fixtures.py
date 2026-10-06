"""Pinned/reversible test-only stop-read hook builder; no product packaging."""
import hashlib,zipfile,struct
from pathlib import Path
from class_patch import ClassFile,transform,word
from sync_ownership_patch import compose,method_code,utf,pool_boundary
from sync_ownership_patch import transform_manager
from worker_exit_patch import plan as worker_plan
from stop_admission_patch import plan,normalize,PIN
ENTRY='com/apple/xsr/net/CommunicationsManager.class'
JAR='9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562'
ORIGINAL='5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449'
TAIL=utf('com/apple/xsr/net/StopAdmissionObservation')+b'\x07'+word(433)+utf('read')+utf('(Lcom/apple/xsr/net/CommunicationsManager;)Z')+b'\x0c'+word(435)+word(436)+b'\x0a'+word(434)+word(437)
def hash(data):return hashlib.sha256(data).hexdigest()
def hook(data):
 c=ClassFile(data);b,e=method_code(c,'dispatchLoop','()V');at=b+14+235
 if c.pool_count!=433 or data[at:at+3]!=bytes.fromhex('b6001b'):raise ValueError('Original stop seam differs')
 return compose(data,c,[(at,at+3,b'\xb8'+word(438))],439,TAIL)
def unhook(data):
 c=ClassFile(data);b,e=method_code(c,'dispatchLoop','()V');at=b+14+235;end=pool_boundary(c,433)
 if c.pool_count!=439 or data[end:c.pool_end]!=TAIL or data[at:at+3]!=b'\xb8'+word(438):raise ValueError('Fixture hook differs')
 return compose(data,c,[(at,at+3,bytes.fromhex('b6001b'))],433,keep_end=end)
def write_fixture(path,entries,manager):
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
  for name,value in sorted(entries.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=(0o40755<<16)|0x10 if name.endswith('/') else 0o100644<<16
   z.writestr(info,manager if name==ENTRY else value)
def build(reference,out):
 reference=Path(reference);out=Path(out)
 if hash(reference.read_bytes())!=JAR:raise ValueError('Unreviewed reference JAR')
 original=Path('original/RAID_Admin_original.jar')
 if hash(original.read_bytes())!=ORIGINAL:raise ValueError('Original changed')
 with zipfile.ZipFile(original) as z:source=worker_plan(transform_manager(transform(ENTRY,z.read(ENTRY))))
 with zipfile.ZipFile(reference) as z:
  names=z.namelist()
  if len(names)!=len(set(names)):raise ValueError('Duplicate reference entries')
  entries={n:z.read(n) for n in names}
 if entries[ENTRY]!=source or hash(source)!=PIN:raise ValueError('Source-reference mismatch')
 guarded=plan(source)
 if normalize(guarded)!=source:raise ValueError('Stop guard reconstruction differs')
 result={}
 for name,data in [('legacy',source),('guarded',guarded)]:
  patched=hook(data)
  if unhook(patched)!=data or hook(unhook(patched))!=patched:raise ValueError('Hook roundtrip differs')
  path=out/(name+'-fixture.jar')
  write_fixture(path,entries,patched)
  with zipfile.ZipFile(path) as z:
   if set(z.namelist())!=set(entries) or any(z.read(n)!=v for n,v in entries.items() if n!=ENTRY):raise ValueError('Fixture changed non-Manager entries')
   if unhook(z.read(ENTRY))!=data:raise ValueError('Written fixture differs')
  result[name]=path
 return result
