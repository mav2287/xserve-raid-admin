"""Exact ownership predecessor -> guarded worker loop; whole-class reversible."""
import hashlib,struct
from class_patch import ClassFile,u2,u4,word
from sync_ownership_patch import utf,compose,code_attribute,method_code,pool_boundary
PIN='19506d7f3b50bb5a227226ec82547b391bb1bcc38a076e4860c70e766ce5ddce'
WINDOWS={63:bytes.fromhex('c000154c2cc3'),612:bytes.fromhex('2bb6002f3a05'),509:bytes.fromhex('b9004e0400'),514:bytes.fromhex('2a03b5000d')}
CTOR=bytes.fromhex('2a2bb5000e')
CALL=bytes.fromhex('b9004e0400')

def jump(at,to):return b'\xc8'+struct.pack('>i',to-at)

class Pool:
 def __init__(self,c):self.c=c;self.extra=bytearray();self.n=c.pool_count;self.names={v.decode('ascii'):i for i,(tag,v) in c.pool.items() if tag==1}
 def add(self,tag,v):i=self.n;self.n+=1;self.extra.extend(bytes([tag])+v);return i
 def utf(self,s):
  if s not in self.names:
   b=s.encode('ascii');self.names[s]=self.add(1,word(len(b))+b)
  return self.names[s]
 def clazz(self,s):return self.add(7,word(self.utf(s)))
 def member(self,tag,owner,name,desc):
  nat=self.add(12,word(self.utf(name))+word(self.utf(desc)));return self.add(tag,word(owner)+word(nat))


def plan(data):
 if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('Exact revised ownership predecessor required')
 c=ClassFile(data)
 if (c.pool_count,len(c.fields),len(c.methods))!=(408,12,14):raise ValueError('Worker predecessor shape differs')
 p=Pool(c);active_name=p.utf('workerActiveTxn');object_type=p.utf('Ljava/lang/Object;');started_name=p.utf('workerActiveStarted');bool_type=p.utf('Z')
 active=p.member(9,131,'workerActiveTxn','Ljava/lang/Object;');started=p.member(9,131,'workerActiveStarted','Z')
 dispatch_name=p.utf('dispatchLoop');dispatch=p.member(10,131,'dispatchLoop','()V');helper=p.clazz('compat/WorkerExit');prepare=p.member(10,helper,'prepare','()V');ensure=p.member(10,helper,'ensurePrepared','()V')
 exit_ref=p.member(10,helper,'exit','(Lcom/apple/xsr/net/CommunicationsManager;Ljava/util/LinkedList;Ljava/lang/Object;ZLcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/AcpxConnection;Ljava/lang/Throwable;)V')
 connect_callback=p.member(10,helper,'connectCallback','(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/Response;Ljava/lang/Object;)V')
 fields=word(2)+word(active_name)+word(object_type)+word(0)+word(2)+word(started_name)+word(bool_type)+word(0)
 cb,ce=method_code(c,'<init>','(Lcom/apple/xsr/som/RaidSystem;)V');rb,re=method_code(c,'run','()V');db,de=method_code(c,'doConnect','(Lcom/apple/xsr/net/CommunicationHandler;)V')
 ctor=bytearray(data[cb+14:cb+14+64]);run=bytearray(data[rb+14:rb+14+623]);connect=bytearray(data[db+14:db+14+754])
 if u4(data,cb+10)!=64 or u4(data,rb+10)!=623 or u4(data,db+10)!=754 or ctor[30:35]!=CTOR:raise ValueError('Worker Code shape differs')
 ctor[30:35]=jump(30,64);ctor.extend(b'\xb8'+word(prepare)+CTOR+jump(72,35))
 tails=[]
 # Keep the actual dequeued transaction recorded under the original queue lock.
 dq=WINDOWS[63][:4]+b'\x2a\x2b\xb5'+word(active)+b'\x2a\x03\xb5'+word(started)+b'\x2c\xc3'+jump(639,69)
 if len(dq)!=21:raise ValueError('Worker dequeue layout differs')
 tails.append(dq)
 claim=b'\x2a\x04\xb5'+word(started)+WINDOWS[612]+jump(655,618)
 if len(claim)!=16:raise ValueError('Worker exposure layout differs')
 tails.append(claim)
 callback=b'\x2a\xb4'+word(active)+b'\xc6'+struct.pack('>h',682-664)+b'\x2a\x01\xb5'+word(active)+CALL+jump(677,514)+b'\x58\x58'+jump(684,514)
 if len(callback)!=29:raise ValueError('Worker callback layout differs')
 tails.append(callback)
 reset=b'\x2a\x01\xb5'+word(active)+b'\x2a\x03\xb5'+word(started)+WINDOWS[514]+jump(704,519)
 if len(reset)!=20:raise ValueError('Worker reset layout differs')
 tails.append(reset)
 for old,target in ((63,623),(612,644),(509,660),(514,689)):
  if run[old:old+len(WINDOWS[old])]!=WINDOWS[old]:raise ValueError('Worker displaced instructions differ')
  run[old:old+len(WINDOWS[old])]=jump(old,target)+bytes(len(WINDOWS[old])-5)
 run.extend(b''.join(tails))
 if len(run)!=709:raise ValueError('Worker dispatch layout differs')
 table=data[rb+14+623:re]
 if u2(table,0)!=16:raise ValueError('Worker old handler count differs')
 handlers=((623,644,72,0),(623,644,525,79),(644,660,462,69),(644,660,337,35),(644,660,462,76),(644,660,525,79),(660,689,525,79),(689,709,525,79))
 table=word(24)+table[2:-2]+b''.join(struct.pack('>HHHH',*row) for row in handlers)+table[-2:]
 for offset,tail_start,resume in ((409,754,414),(586,769,591)):
  if connect[offset:offset+5]!=CALL:raise ValueError('Connect callback instruction differs')
  connect[offset:offset+5]=jump(offset,tail_start)
  connect.extend(b'\x2a\x01\xb5'+word(active)+b'\xb8'+word(connect_callback)+bytes(2)+jump(tail_start+10,resume))
 if len(connect)!=784:raise ValueError('Connect callback tail layout differs')
 # Direct private call; initialize cause on normal and exceptional paths.
 wrapper=b'\xb8'+word(ensure)+b'\x2a\xb7'+word(dispatch)+b'\x01\x4c\xa7\x00\x04\x4c'
 wrapper+=b'\x2a\x04\xb5\x00\x0b'
 wrapper+=b'\x2a\xb4'+word(active)+b'\x4d\x2a\xb4'+word(started)+b'\x3e'
 wrapper+=b'\x2a\x01\xb5'+word(active)+b'\x2a\x03\xb5'+word(started)
 wrapper+=b'\x2a\x2a\xb4\x00\x0a\x2c\x1d\x2a\xb4\x00\x0e\x2a\xb4\x00\x29\x2b\xb8'+word(exit_ref)+b'\xb1'
 wrapper_tail=word(1)+struct.pack('>HHHH',0,7,12,0)+word(0)
 wrapper_attr=code_attribute(data[rb:rb+2],word(7)+word(4),wrapper,wrapper_tail)
 wrapper_method=word(1)+word(177)+word(174)+word(1)+wrapper_attr
 run_member=next(m for m in c.methods if m['name']=='run')
 edits=[(cb,ce,code_attribute(data[cb:ce],data[cb+6:cb+10],bytes(ctor),data[cb+14+64:ce])),(rb,re,code_attribute(data[rb:re],data[rb+6:rb+10],bytes(run),table)),(db,de,code_attribute(data[db:de],data[db+6:db+10],bytes(connect),data[db+14+754:de])),(run_member['start'],run_member['start']+4,word(2)+word(dispatch_name)),(c.fields[0]['start']-2,c.fields[0]['start'],word(14)),(c.fields[-1]['end'],c.fields[-1]['end']+2,fields+word(15)),(c.methods[-1]['end'],c.methods[-1]['end'],wrapper_method)]
 return compose(data,c,edits,p.n,bytes(p.extra))


def normalize(data):
 c=ClassFile(data)
 if c.pool_count==408:
  if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('Unreviewed worker predecessor')
  return data
 if len(c.fields)!=14 or len(c.methods)!=15:raise ValueError('Worker reconstruction member counts differ')
 cb,ce=method_code(c,'<init>','(Lcom/apple/xsr/som/RaidSystem;)V');rb,re=method_code(c,'dispatchLoop','()V');db,de=method_code(c,'doConnect','(Lcom/apple/xsr/net/CommunicationHandler;)V')
 if (u4(data,cb+10),u4(data,rb+10),u4(data,db+10))!=(77,709,784):raise ValueError('Worker reconstruction Code lengths differ')
 ctor=bytearray(data[cb+14:cb+14+64]);ctor[30:35]=CTOR
 run=bytearray(data[rb+14:rb+14+623])
 for offset,old in WINDOWS.items():run[offset:offset+len(old)]=old
 table=data[rb+14+709:re]
 if u2(table,0)!=24:raise ValueError('Worker reconstruction handlers differ')
 table=word(16)+table[2:-66]+table[-2:]
 connect=bytearray(data[db+14:db+14+754]);connect[409:414]=CALL;connect[586:591]=CALL
 renamed=next(m for m in c.methods if m['name']=='dispatchLoop');wrapper=c.methods[-1]
 edits=[(cb,ce,code_attribute(data[cb:ce],data[cb+6:cb+10],bytes(ctor),data[cb+14+77:ce])),(rb,re,code_attribute(data[rb:re],data[rb+6:rb+10],bytes(run),table)),(db,de,code_attribute(data[db:de],data[db+6:db+10],bytes(connect),data[db+14+784:de])),(renamed['start'],renamed['start']+4,word(1)+word(177)),(c.fields[0]['start']-2,c.fields[0]['start'],word(12)),(c.fields[-2]['start'],c.fields[-1]['end']+2,word(14)),(wrapper['start'],wrapper['end'],b'')]
 restored=compose(data,c,edits,408,keep_end=pool_boundary(c,408))
 if hashlib.sha256(restored).hexdigest()!=PIN or plan(restored)!=data:raise ValueError('Worker edits differ from exact reversible plan')
 return restored
