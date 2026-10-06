"""Exact audit.20 -> ownership edits, with whole-class reconstruction pins."""
import hashlib
import struct
from class_patch import ClassFile,u2,u4,word

MANAGER_SHA='ddd62642900262d6c99b14777c79ddd22a54b97ef506e7984daff46b3bb7bbfd'
SENDER_SHA='9313aae6769e648e0611e1590de96e0826bf77a45feda06608fbc5abb881170c'
CONSTRUCTOR='(Lcom/apple/xsr/net/CommunicationsManager;Lcom/apple/xsr/net/RequestMessage;)V'
RESPONSE='(Lcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/Response;Ljava/lang/Object;)V'
MANAGER_WINDOW=bytes.fromhex('2bb6002f3a05')
MANAGER_ENTRY=bytes.fromhex('c80000016200')
MANAGER_TAIL=bytes.fromhex('2cc1001e99000d2cc0001eb6019799ff882bb6002f3a05c8fffffe8d')
MANAGER_HANDLERS=((595,623,462,69),(595,623,337,35),(595,623,462,76),(595,623,525,79))
MANAGER_TABLE=b''.join(struct.pack('>HHHH',*entry) for entry in MANAGER_HANDLERS)
INTERRUPT_TAIL=bytes.fromhex('3a042ab400039affd02ab4004b9aff81c8ffffffa2')
RESPONSE_GUARD=bytes.fromhex('2ab40003990004b1')
CLAIM_CODE=bytes.fromhex('2ab400039a00112ab4004b9a000a2a04b5004b04ac03ac')
CLAIM_FIELD=bytes.fromhex('0002004900190000')


def utf(value):
    data=value.encode('ascii');return b'\x01'+word(len(data))+data


def sender_pool():
    return utf('claimed')+b'\x0c'+word(73)+word(25)+b'\x09'+word(19)+word(74)+utf('claim')+utf('()Z')


def manager_pool():
    return utf('claim')+b'\x0c'+word(405)+word(171)+b'\x0a'+word(30)+word(406)


def method_code(cls,name,descriptor):
    methods=[m for m in cls.methods if (m['name'],m['descriptor'])==(name,descriptor)]
    if len(methods)!=1:raise ValueError('Ownership method identity differs')
    codes=[a for a in methods[0]['attributes'] if a[0]=='Code']
    if len(codes)!=1:raise ValueError('Ownership Code identity differs')
    return codes[0][1:]


def pool_boundary(cls,count):
    return 10+sum(1+len(v)+(2 if tag==1 else 0) for i,(tag,v) in cls.pool.items() if i<count)


def compose(data,cls,edits,count,extra=b'',keep_end=None):
    tail=bytearray();cursor=cls.pool_end
    for b,e,value in sorted(edits):
        if b<cursor or e<b:raise ValueError('Overlapping ownership edits')
        tail.extend(data[cursor:b]);tail.extend(value);cursor=e
    tail.extend(data[cursor:])
    return data[:8]+word(count)+data[10:cls.pool_end if keep_end is None else keep_end]+extra+tail


def code_attribute(original,frame,code,tail):
    body=frame+struct.pack('>I',len(code))+code+tail
    return original[:2]+struct.pack('>I',len(body))+body


def claim_method():
    body=bytes.fromhex('00020001')+struct.pack('>I',23)+CLAIM_CODE+bytes(4)
    return bytes.fromhex('0020004c004d0001001f')+struct.pack('>I',len(body))+body


def transform_sender(data):
    if hashlib.sha256(data).hexdigest()!=SENDER_SHA:raise ValueError('Ownership sender must be exact audit.20')
    cls=ClassFile(data);cb,ce=method_code(cls,'<init>',CONSTRUCTOR);hb,he=method_code(cls,'handleResponse',RESPONSE)
    if cls.pool_count!=73 or len(cls.fields)!=3 or len(cls.methods)!=3 or u2(data,6)!=47 or u4(data,cb+10)!=138 or u4(data,hb+10)!=15:raise ValueError('Ownership sender shape differs')
    table=bytearray(data[cb+14+138:ce])
    if bytes(table)!=bytes.fromhex('0003001f0037003a000b001800620065000000650069006500000000'):raise ValueError('Original sender monitor table differs')
    table[0:2]=word(4);table[6:8]=word(138);table[26:26]=struct.pack('>HHHH',138,159,101,0)
    ctor=code_attribute(data[cb:ce],data[cb+6:cb+10],data[cb+14:cb+152]+INTERRUPT_TAIL,bytes(table))
    response=code_attribute(data[hb:he],data[hb+6:hb+10],RESPONSE_GUARD+data[hb+14:hb+29],data[hb+29:he])
    fields_count=cls.fields[0]['start']-2;methods_count=cls.fields[-1]['end'];end_methods=cls.methods[-1]['end']
    edits=[(cb,ce,ctor),(hb,he,response),(fields_count,fields_count+2,word(4)),(methods_count,methods_count+2,CLAIM_FIELD+word(4)),(end_methods,end_methods,claim_method())]
    result=compose(data,cls,edits,78,sender_pool())
    if normalize_sender(result)!=data:raise ValueError('Ownership sender round trip differs')
    return result


def normalize_sender(data):
    cls=ClassFile(data)
    if cls.pool_count==73:
        if hashlib.sha256(data).hexdigest()!=SENDER_SHA:raise ValueError('Unreviewed unmodified ownership sender')
        return data
    cb,ce=method_code(cls,'<init>',CONSTRUCTOR);hb,he=method_code(cls,'handleResponse',RESPONSE)
    if cls.pool_count!=78 or len(cls.fields)!=4 or len(cls.methods)!=4 or u4(data,cb+10)!=159 or u4(data,hb+10)!=23 or data[cb+6:cb+10]!=bytes.fromhex('00070007') or data[hb+6:hb+10]!=bytes.fromhex('00020004'):raise ValueError('Ownership sender shape differs')
    at=pool_boundary(cls,73)
    if data[at:cls.pool_end]!=sender_pool() or data[cb+14+138:cb+14+159]!=INTERRUPT_TAIL or data[hb+14:hb+22]!=RESPONSE_GUARD:raise ValueError('Ownership sender pool/trampolines differ')
    field=cls.fields[-1];method=cls.methods[-1]
    if data[field['start']:field['end']]!=CLAIM_FIELD or data[method['start']:method['end']]!=claim_method():raise ValueError('Ownership field or claim method differs')
    table=data[cb+14+159:ce]
    expected=bytes.fromhex('0004001f0037008a000b00180062006500000065006900650000008a009f006500000000')
    if table!=expected:raise ValueError('Ownership interrupt cleanup coverage differs')
    oldtable=bytearray(table[:26]+table[34:]);oldtable[0:2]=word(3);oldtable[6:8]=word(58)
    ctor=code_attribute(data[cb:ce],data[cb+6:cb+10],data[cb+14:cb+14+138],bytes(oldtable))
    response=code_attribute(data[hb:he],data[hb+6:hb+10],data[hb+22:hb+14+23],data[hb+14+23:he])
    count=cls.fields[0]['start']-2
    edits=[(cb,ce,ctor),(hb,he,response),(count,count+2,word(3)),(field['start'],field['end']+2,word(3)),(method['start'],method['end'],b'')]
    restored=compose(data,cls,edits,73,keep_end=at)
    if hashlib.sha256(restored).hexdigest()!=SENDER_SHA:raise ValueError('Sender differs outside exact ownership edits')
    return restored


def transform_manager(data):
    if hashlib.sha256(data).hexdigest()!=MANAGER_SHA:raise ValueError('Ownership manager must be exact audit.20')
    cls=ClassFile(data);b,e=method_code(cls,'run','()V');n=u4(data,b+10)
    if cls.pool_count!=405 or n!=595 or data[b+14+241:b+14+247]!=MANAGER_WINDOW:raise ValueError('Ownership worker shape/window differs')
    code=bytearray(data[b+14:b+14+n]);code[241:247]=MANAGER_ENTRY;code.extend(MANAGER_TAIL)
    table=data[b+14+n:e]
    if u2(table,0)!=12 or table[-2:]!=bytes(2):raise ValueError('Ownership worker table differs')
    original_entries=[struct.unpack_from('>HHHH',table,2+8*i) for i in range(12)]
    covering=[(handler,kind) for start,end,handler,kind in original_entries if start<=241 and end>=247]
    if covering!=[(462,69),(337,35),(462,76),(525,79)]:raise ValueError('Original worker window handler order differs')
    table=word(16)+table[2:-2]+MANAGER_TABLE+table[-2:]
    result=compose(data,cls,[(b,e,code_attribute(data[b:e],data[b+6:b+10],bytes(code),table))],408,manager_pool())
    if normalize_manager(result)!=data:raise ValueError('Ownership worker round trip differs')
    return result


def normalize_manager(data):
    cls=ClassFile(data)
    if cls.pool_count<408:
        if hashlib.sha256(data).hexdigest()!=MANAGER_SHA:raise ValueError('Unreviewed unmodified ownership manager')
        return data
    b,e=method_code(cls,'run','()V');at=pool_boundary(cls,405)
    if cls.pool_count!=408 or u4(data,b+10)!=623 or data[b+6:b+10]!=bytes.fromhex('00060009') or data[at:cls.pool_end]!=manager_pool():raise ValueError('Ownership worker pool/frame differs')
    code=bytearray(data[b+14:b+14+623]);table=data[b+14+623:e]
    if code[241:247]!=MANAGER_ENTRY or code[595:]!=MANAGER_TAIL or u2(table,0)!=16 or table[-34:-2]!=MANAGER_TABLE:raise ValueError('Ownership worker trampoline/coverage differs')
    code[241:247]=MANAGER_WINDOW
    oldtable=word(12)+table[2:-34]+table[-2:]
    restored=compose(data,cls,[(b,e,code_attribute(data[b:e],data[b+6:b+10],bytes(code[:595]),oldtable))],405,keep_end=at)
    if hashlib.sha256(restored).hexdigest()!=MANAGER_SHA:raise ValueError('Manager differs outside exact ownership edits')
    return restored
