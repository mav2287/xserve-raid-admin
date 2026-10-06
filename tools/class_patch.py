"""Hash-locked method substitutions and operand edits; unrelated bytes stay fixed."""
import hashlib
import struct

TARGETS = {
    'com/apple/xsr/net/CommunicationsManager$SyncSender.class': ('69c71a7d47c4c96c713741a86e2539ca6289c6e6b947aae0dec959d9edc161ab', '<init>', '(Lcom/apple/xsr/net/CommunicationsManager;Lcom/apple/xsr/net/RequestMessage;)V'),
    'com/apple/xsr/net/CommunicationsManager.class': ('c4bd4c0742a5b6d1b746992e0db1b984fd770a9d6b3babbe33e8f78366312dd1', 'run', '()V'),
    'com/apple/xsr/net/AcpxConnection.class': ('f10e7f1c5acf9c03281915ae9ce77adb9f2db9e10f7ed392845f46f6fd8cf125', 'send', '(Lcom/apple/xsr/net/RequestMessage;)Lcom/apple/util/plist/PropertyList;'),
    'com/apple/xsr/net/HttpResponse.class': ('e66bb37d2127151debc9dd0481551bc3a88aaf32aeedc691774c099c52a83e75', 'getBody', '()[B'),
    'com/apple/util/plist/PropertyListUtilities.class':
        ('b900df2b6ec7f7c5fa1548bdc338b5694ebf15d5719e664a508cdb84fc16025a',
         'getParser', '()Ljavax/xml/parsers/SAXParser;'),
    'com/apple/util/plist/PropertyListUtilities$Handler.class':
        ('29c3a81427b07fb9241df9560050dfddd72b231a6b6486686fb8414cbf79cb70',
         'resolveEntity', '(Ljava/lang/String;Ljava/lang/String;)Lorg/xml/sax/InputSource;'),
    'com/apple/xsr/net/AbstractRequestMessage.class':
        ('609356596df9a6bcec557bc79407e440ff3633b0e1611f144faa4ce743689e44', 'toString', '()Ljava/lang/String;'),
    'com/apple/xsr/net/AcpxMessageFactory$AcpxRequestTemplate.class':
        ('8067f54187a63486c30c4969988a3f14b8fdf4c9d4c14842ec8f27556e9b3b37', 'toString', '()Ljava/lang/String;'),
}
SECONDARY = {'com/apple/xsr/net/CommunicationsManager.class': ('doConnect','(Lcom/apple/xsr/net/CommunicationHandler;)V',0x0002)}
AUDIT18_MANAGER_SHA256='a928b493ecf796ab90415339a20f8f7cd4914afaa3add052bdff1796cad70893'
AUDIT17_MANAGER_SHA256='7c07f4c31a6104f52ee151e07141296d5b59ef33fa5105b895c6504c58ac2a1c'
EXPECTED_ACCESS = {entry: (0x000c if name == 'getParser' else 0x0001)
                   for entry, (_, name, _) in TARGETS.items()}
REDACTED = 'RAID Admin request [details redacted]'


def u2(data, at): return struct.unpack_from('>H', data, at)[0]
def u4(data, at): return struct.unpack_from('>I', data, at)[0]
def word(value): return struct.pack('>H', value)


class ClassFile:
    def __init__(self, data):
        if data[:4] != b'\xca\xfe\xba\xbe': raise ValueError('Not a Java class')
        self.data = data
        self.pool_count = u2(data, 8)
        self.pool = {}
        at, index = 10, 1
        sizes = {3:4,4:4,5:8,6:8,7:2,8:2,9:4,10:4,11:4,12:4,15:3,16:2,17:4,18:4,19:2,20:2}
        while index < self.pool_count:
            tag = data[at]; at += 1
            if tag == 1:
                length = u2(data, at); at += 2
            elif tag in sizes: length = sizes[tag]
            else: raise ValueError('Unsupported constant-pool tag')
            value = data[at:at+length]
            if len(value) != length: raise ValueError('Truncated constant pool')
            self.pool[index] = (tag, value); at += length
            index += 2 if tag in (5,6) else 1
        self.pool_end = at
        at += 6
        at += 2 + 2 * u2(data, at)
        field_count = u2(data, at); at += 2
        self.fields=[]
        for _ in range(field_count):
            member,at=self.member(at);self.fields.append(member)
        method_count = u2(data, at); at += 2
        self.methods = []
        for _ in range(method_count):
            member, at = self.member(at); self.methods.append(member)
        self.class_attributes = data[at:]

    def text(self, index):
        tag, value = self.pool[index]
        if tag != 1: raise ValueError('Expected UTF8 constant')
        # Only ASCII identifiers/literals are interpreted. Original bytes are never re-encoded.
        return value.decode('ascii')

    def member(self, at):
        start = at
        access, name, descriptor, count = struct.unpack_from('>HHHH', self.data, at); at += 8
        attrs = []
        for _ in range(count):
            name_index, size = u2(self.data, at), u4(self.data, at+2)
            end = at + 6 + size
            if end > len(self.data): raise ValueError('Truncated attribute')
            attrs.append((self.text(name_index), at, end)); at = end
        return {'start':start,'end':at,'access':access,'name':self.text(name),
                'descriptor':self.text(descriptor),'attributes':attrs}, at


def embedded_dtd(data):
    cls = ClassFile(data)
    found = []
    for tag, value in cls.pool.values():
        if tag == 8:
            target_tag, text = cls.pool[u2(value,0)]
            if target_tag != 1: raise ValueError('String must reference UTF8 constant')
            if text.startswith(b'<!ENTITY % plistObject '): found.append(text)
    if len(found) != 1: raise ValueError('Original embedded DTD not unique')
    found[0].decode('ascii')
    return found[0]


def transform(entry, data):
    result = _transform_reference(entry, data)
    if entry == 'com/apple/xsr/net/CommunicationsManager.class':
        result = stopped_admission(result)
    return result


def _transform_reference(entry, data):
    expected, name, descriptor = TARGETS[entry]
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Original class hash mismatch; refusing method substitution')
    cls = ClassFile(data)
    targets = [m for m in cls.methods if (m['name'],m['descriptor']) == (name,descriptor)]
    if len(targets) != 1 or targets[0]['access'] != EXPECTED_ACCESS[entry]:
        raise ValueError('Target method missing, duplicate or access flags differ')
    codes = [a for a in targets[0]['attributes'] if a[0] == 'Code']
    if len(codes) != 1: raise ValueError('Target must have exactly one Code attribute')
    extra = bytearray(); next_index = cls.pool_count
    def append(tag, value):
        nonlocal next_index
        index = next_index; next_index += 1
        if next_index > 65535: raise ValueError('Constant pool overflow')
        extra.extend(bytes([tag]) + value)
        return index
    def utf8(text):
        value = text.encode('ascii')
        return append(1, word(len(value)) + value)
    if name == '<init>':
        _, begin, end = codes[0]
        if u2(data,6)!=47 or data[begin+6:begin+10]!=bytes.fromhex('00070007') or u4(data,begin+10)!=109:
            raise ValueError('Sync constructor verifier/code shape differs')
        code=data[begin+14:begin+14+109]
        if code[14:20]!=bytes.fromhex('2b2a2cb60004') or code[31:51]!=bytes.fromhex('b800052bb80006a6000dbb0007591208b70009bf'):
            raise ValueError('Sync constructor queue/check windows differ')
        patched=bytearray(code);patched[14:20]=bytes.fromhex('a7005f000000')
        patched.extend(code[31:51]+code[14:20]+bytes.fromhex('a7ff8d'))
        body=data[begin+6:begin+10]+struct.pack('>I',len(patched))+patched+data[begin+14+109:end]
        replacement=data[begin:begin+2]+struct.pack('>I',len(body))+body
        result=data[:begin]+replacement+data[end:]
        assert_preserved(data,result,name,descriptor);assert_sync_preenqueue(data,result)
        return result
    if name in ('run','send'):
        if u2(data,6)!=47: raise ValueError('Unexpected recovery verifier version')
        owner=append(7,word(utf8('compat/RejectionRecovery')))
        desc='(Lcom/apple/xsr/net/CommunicationsManager;Ljava/lang/Exception;)V' if name=='run' else '(Ljava/lang/Throwable;Lcom/apple/xsr/net/AcpxConnection;)Ljava/lang/Throwable;'
        signature=append(12,word(utf8('report' if name=='run' else 'sendFailure'))+word(utf8(desc)))
        reference=append(10,word(owner)+word(signature))
        _,begin,end=codes[0]; n=u4(data,begin+10); original_code=data[begin+14:begin+14+n]
        if name=='run':
            if n!=553 or original_code[464:474]!=bytes.fromhex('b2002619051905b60046'): raise ValueError('Recovery log window differs')
            tail=data[begin+14+n:end]
            expected_tail=bytes.fromhex('000c000700350048000000380045004800000048004b0048000000d701300133004500d701300151002301810189018c0000018c0191018c0000019c01a701aa000001aa01af01aa000000d7013001ce004c0000020a020d004f021602240227004c0000')
            if original_code[349:352]!=bytes.fromhex('99001f') or original_code[339:349]!=bytes.fromhex('1905b600471248b60049') or data[begin+6:begin+10]!=bytes.fromhex('00060009') or tail!=expected_tail:raise ValueError('IO handler window, frames or exact twelve-handler table differs')
            for index,owner_name,method_name,method_descriptor in ((71,'java/io/IOException','getMessage','()Ljava/lang/String;'),(73,'java/lang/String','startsWith','(Ljava/lang/String;)Z')):
                tag,member=cls.pool[index];ot,ov=cls.pool[u2(member,0)];nt,nv=cls.pool[u2(member,2)]
                if tag!=10 or ot!=7 or cls.text(u2(ov,0))!=owner_name or nt!=12 or cls.text(u2(nv,0))!=method_name or cls.text(u2(nv,2))!=method_descriptor:raise ValueError('IO handler original targets differ')
            tag,value=cls.pool[72]
            if tag!=8 or cls.text(u2(value,0))!='PropertyListException':raise ValueError('IO prefix classification differs')
            null_signature=append(12,word(utf8('nullMessage'))+word(utf8('()Ljava/lang/Exception;')))
            null_reference=append(10,word(owner)+word(null_signature))
            retire_signature=append(12,word(utf8('retire'))+word(utf8('(Lcom/apple/xsr/net/CommunicationsManager;)V')))
            retire_reference=append(10,word(owner)+word(retire_signature))
            code=bytearray(original_code)
            code[339:344]=bytes.fromhex('c8000000d6')
            code[350:352]=bytes.fromhex('00d6')
            code[464:474]=b'\x2a\x19\x05\xb8'+word(reference)+bytes(4)
            code.extend(bytes.fromhex('1905b6004759c7000e57b8')+word(null_reference)+bytes.fromhex('3a05c8ffffff98c800000005'))
            code.extend(bytes.fromhex('1248b6004999ffec2ab8')+word(retire_reference)+bytes.fromhex('c8ffffff12'))
            tail=bytearray(tail);tail[30:32]=word(462)
            body=data[begin+6:begin+10]+struct.pack('>I',len(code))+code+tail
            replacement=data[begin:begin+2]+struct.pack('>I',len(body))+body
        else:
            tail=data[begin+14+n:end]
            if n!=392 or tail!=bytes.fromhex('00030020010f0115003700200112013e000001150143013e00000000'):
                raise ValueError('Send Code shape/handlers differ')
            marker=append(7,word(utf8('compat/UntrustedResponseException')))
            added=struct.pack('>HHHH',32,271,392,marker)
            code=original_code+b'\x2a\xb8'+word(reference)+b'\xbf'
            body=data[begin+6:begin+10]+struct.pack('>I',len(code))+code+word(4)+tail[2:10]+added+tail[10:]
            replacement=data[begin:begin+2]+struct.pack('>I',len(body))+body
        edits=[(begin,end,bytes(replacement))]
        if name=='run':
            secondary_name,secondary_descriptor,secondary_access=SECONDARY[entry]
            methods=[m for m in cls.methods if (m['name'],m['descriptor'])==(secondary_name,secondary_descriptor)]
            if len(methods)!=1 or methods[0]['access']!=secondary_access:raise ValueError('Connect method identity differs')
            attrs=[a for a in methods[0]['attributes'] if a[0]=='Code']
            if len(attrs)!=1:raise ValueError('Connect Code missing')
            _,cb,ce=attrs[0];length=u4(data,cb+10)
            original_connect=data[cb+14:cb+14+length]
            if length!=718 or data[cb+6:cb+10]!=bytes.fromhex('00060010') or original_connect[393:401]!=bytes.fromhex('b20026190bb60028') or original_connect[578:583]!=bytes.fromhex('2b2ab4000e'):raise ValueError('Connect failure windows/frames differ')
            connect=bytearray(original_connect);connect[393:401]=bytes.fromhex('c800000145000000');connect[578:583]=bytes.fromhex('c8000000a2')
            connect.extend(bytes.fromhex('2a04b5000d2ab8')+word(retire_reference)+original_connect[393:401]+bytes.fromhex('c8fffffeb2'))
            connect.extend(bytes.fromhex('2ab8')+word(retire_reference)+original_connect[578:583]+bytes.fromhex('c8ffffff5a'))
            body=data[cb+6:cb+10]+struct.pack('>I',len(connect))+connect+data[cb+14+length:ce]
            edits.append((cb,ce,data[cb:cb+2]+struct.pack('>I',len(body))+body))
        tail=bytearray();cursor=cls.pool_end
        for eb,ee,value in sorted(edits):
            if eb<cursor:raise ValueError('Overlapping recovery edits')
            tail.extend(data[cursor:eb]);tail.extend(value);cursor=ee
        tail.extend(data[cursor:])
        result=data[:8]+word(next_index)+data[10:cls.pool_end]+bytes(extra)+bytes(tail)
        if name=='run':
            current=ClassFile(result);stopped=next(f for f in current.fields if f['name']=='stopped');worker=next(m for m in current.methods if m['name']=='run');_,rb,re=next(a for a in worker['attributes'] if a[0]=='Code')
            changed=bytearray(result)
            if stopped['access']!=2 or any(result[rb+14+pc:rb+14+pc+3]!=bytes.fromhex('b6001b') for pc in (18,45)):raise ValueError('Original stop lock windows differ')
            changed[stopped['start']:stopped['start']+2]=word(0x42)
            for pc in (18,45):changed[rb+14+pc:rb+14+pc+3]=bytes.fromhex('b4000b')
            result=bytes(changed)
        assert_preserved(data,result,name,descriptor);assert_recovery_edit(data,result,name)
        return result
    if name == 'getBody':
        if u2(data,6) != 47: raise ValueError('Unexpected legacy verifier version')
        _, begin, end = codes[0]
        start = begin + 14
        if data[start+2:start+9]!=bytes.fromhex('2a1213b600144d'):raise ValueError('Response length lookup window differs')
        for index,expected_name,expected_descriptor in ((20,'getHeaderField','(Ljava/lang/String;)Ljava/lang/String;'),(54,'setHeaderField','(Ljava/lang/String;Ljava/lang/String;)V')):
            tag,member=cls.pool[index];ot,ov=cls.pool[u2(member,0)];nt,nv=cls.pool[u2(member,2)]
            if tag!=10 or ot!=7 or cls.text(u2(ov,0))!='com/apple/xsr/net/HttpResponse' or nt!=12 or cls.text(u2(nv,0))!=expected_name or cls.text(u2(nv,2))!=expected_descriptor:raise ValueError('Original framing method target differs')
        st,sv=cls.pool[19]
        if st!=8 or cls.text(u2(sv,0))!='Content-Length':raise ValueError('Original length lookup key differs')
        if data[start+13:start+23]!=bytes.fromhex('2cb800153c2a1bb50016'):raise ValueError('Response parse instruction window differs')
        pt,pv=cls.pool[21];ot,ov=cls.pool[u2(pv,0)];nt,nv=cls.pool[u2(pv,2)]
        if pt!=10 or ot!=7 or cls.text(u2(ov,0))!='java/lang/Integer' or nt!=12 or cls.text(u2(nv,0))!='parseInt' or cls.text(u2(nv,2))!='(Ljava/lang/String;)I':raise ValueError('Original response parser target differs')
        if data[start+23:start+31] != bytes.fromhex('bb0017591bb70018'):
            raise ValueError('Response allocation instruction window differs')
        class_tag,class_value=cls.pool[23]
        if class_tag != 7 or cls.text(u2(class_value,0)) != 'java/io/ByteArrayOutputStream':
            raise ValueError('Unexpected response allocation class')
        tag, member = cls.pool[24]
        if tag != 10 or u2(member,0) != 23: raise ValueError('Unexpected response constructor owner')
        tag, signature = cls.pool[u2(member,2)]
        if tag != 12 or cls.text(u2(signature,0)) != '<init>' or cls.text(u2(signature,2)) != '(I)V':
            raise ValueError('Unexpected response constructor descriptor')
        owner = append(7,word(utf8('compat/BoundedResponseBuffer')))
        signature = append(12,word(utf8('<init>'))+word(utf8('(I)V')))
        constructor = append(10,word(owner)+word(signature))
        parse_signature=append(12,word(utf8('parseLength'))+word(utf8('(Ljava/lang/String;)I')))
        parse_reference=append(10,word(owner)+word(parse_signature))
        replacement = bytearray(data[begin:end])
        framing_owner=append(7,word(utf8('compat/ResponseFraming')))
        length_signature=append(12,word(utf8('lengthHeader'))+word(utf8('(Lcom/apple/xsr/net/HttpResponse;Ljava/lang/String;)Ljava/lang/String;')))
        length_reference=append(10,word(framing_owner)+word(length_signature))
        set_signature=append(12,word(utf8('setHeader'))+word(utf8('(Lcom/apple/xsr/net/HttpResponse;Ljava/lang/String;Ljava/lang/String;)V')))
        set_reference=append(10,word(framing_owner)+word(set_signature))
        invalid_signature=append(12,word(utf8('invalidHeader'))+word(utf8('()Ljava/lang/RuntimeException;')))
        invalid_reference=append(10,word(framing_owner)+word(invalid_signature))
        replacement[14+5:14+8]=b'\xb8'+word(length_reference)
        replacement[14+15:14+17]=word(parse_reference)
        replacement[14+24:14+26] = word(owner)
        replacement[14+29:14+31] = word(constructor)
        header_owner=append(7,word(utf8('compat/BoundedHeaderStream')))
        header_signature=append(12,word(utf8('wrap'))+word(utf8('(Ljava/io/InputStream;)Ljava/io/InputStream;')))
        header_reference=append(10,word(header_owner)+word(header_signature))
        constructors=[m for m in cls.methods if (m['name'],m['descriptor'])==('<init>','(Lcom/apple/xsr/net/HttpConnection;)V')]
        if len(constructors)!=1 or constructors[0]['access']!=0: raise ValueError('Response constructor identity differs')
        attrs=[a for a in constructors[0]['attributes'] if a[0]=='Code']
        if len(attrs)!=1: raise ValueError('Response constructor Code missing')
        _,cb,ce=attrs[0]
        if u4(data,cb+10)!=44 or data[cb+14+44:ce]!=bytes(4):
            raise ValueError('Response constructor Code shape or nested attributes differ')
        original_code=data[cb+14:cb+14+44]
        if original_code[36:44]!=bytes.fromhex('b5000d2ab7000eb1'): raise ValueError('Response stream assignment differs')
        body=data[cb+6:cb+10]+struct.pack('>I',47)+original_code[:36]+b'\xb8'+word(header_reference)+original_code[36:]+bytes(4)
        constructor_replacement=data[cb:cb+2]+struct.pack('>I',len(body))+body
        headers=[m for m in cls.methods if (m['name'],m['descriptor'])==('parseHeaders','()V')]
        if len(headers)!=1 or headers[0]['access']!=2:raise ValueError('Header parser identity differs')
        attrs=[a for a in headers[0]['attributes'] if a[0]=='Code']
        if len(attrs)!=1:raise ValueError('Header parser Code missing')
        _,hb,he=attrs[0]
        if u4(data,hb+10)!=158 or data[hb+14+88:hb+14+99]!=bytes.fromhex('2a19041905b600361904b6'):raise ValueError('Header assignment window differs')
        code=data[hb+14:hb+14+158]
        if code[130:157]!=bytes.fromhex('bb003a59bb001c59b7001d123bb6001f2cb6001fb60022b7003cbf') or code[157]!=177 or code[58:61]!=bytes.fromhex('9f0048') or code[62:65]!=bytes.fromhex('9e0044') or data[hb+14+158:he]!=bytes(4):raise ValueError('Invalid header window, branches or metadata differ')
        ct,cv=cls.pool[58];st,sv=cls.pool[59];mt,mv=cls.pool[60]
        nt,nv=cls.pool[u2(mv,2)]
        if ct!=7 or cls.text(u2(cv,0))!='java/net/ProtocolException' or st!=8 or cls.text(u2(sv,0))!='Invalid HTTP header: ' or mt!=10 or u2(mv,0)!=58 or nt!=12 or cls.text(u2(nv,0))!='<init>' or cls.text(u2(nv,2))!='(Ljava/lang/String;)V':raise ValueError('Invalid header original linkage differs')
        header_replacement=bytearray(data[hb:he]);header_replacement[14+93:14+96]=b'\xb8'+word(set_reference)
        header_replacement[14+130:14+157]=b'\xb8'+word(invalid_reference)+b'\xbf'+bytes(23)
        edits=sorted([(begin,end,bytes(replacement)),(cb,ce,constructor_replacement),(hb,he,bytes(header_replacement))])
        tail=bytearray();cursor=cls.pool_end
        for eb,ee,value in edits:tail.extend(data[cursor:eb]);tail.extend(value);cursor=ee
        tail.extend(data[cursor:])
        result = data[:8]+word(next_index)+data[10:cls.pool_end]+bytes(extra)+bytes(tail)
        assert_preserved(data,result,name,descriptor)
        assert_allocation_operands(data,result)
        return result
    if name in ('resolveEntity', 'getParser'):
        owner = append(7, word(utf8('compat/SafePlistResolver' if name == 'resolveEntity' else 'compat/SafePlistParser')))
        method_name = utf8('resolve' if name == 'resolveEntity' else 'create')
        method_descriptor = utf8(descriptor)
        signature = append(12, word(method_name) + word(method_descriptor))
        reference = append(10, word(owner) + word(signature))
        code = (b'\x2b\x2c' if name == 'resolveEntity' else b'') + b'\xb8' + word(reference) + b'\xb0'
        stack, local = (2, 3) if name == 'resolveEntity' else (1, 0)
    elif name == 'toString':
        constant = append(8, word(utf8(REDACTED)))
        code = b'\x13' + word(constant) + b'\xb0'  # ldc_w even when the index happens to fit in one byte
        stack, local = 1, 1
    else:
        raise ValueError('Unsupported transformation target')
    _, begin, end = codes[0]
    body = struct.pack('>HHI',stack,local,len(code)) + code + b'\x00\x00\x00\x00'
    replacement = data[begin:begin+2] + struct.pack('>I',len(body)) + body
    result = (data[:8] + word(next_index) + data[10:cls.pool_end] + bytes(extra) +
              data[cls.pool_end:begin] + replacement + data[end:])
    assert_preserved(data, result, name, descriptor)
    return result


def assert_preserved(before, after, name, descriptor):
    if name=='run':after=normalize_stopped_admission(after)
    if name=='run':after=assert_stop_lock_order(before,after)
    old, new = ClassFile(before), ClassFile(after)
    if before[:8] != after[:8] or after[10:old.pool_end] != before[10:old.pool_end]:
        raise ValueError('Original class version or constant pool changed')
    if len(old.methods) != len(new.methods) or old.class_attributes != new.class_attributes:
        raise ValueError('Original method list or class attributes changed')
    if before[old.pool_end:old.methods[0]['start']] != after[new.pool_end:new.methods[0]['start']]:
        raise ValueError('Original class hierarchy, fields or method count changed')
    for a,b in zip(old.methods,new.methods):
        if (a['name'],a['descriptor']) == (name,descriptor) or (name=='run' and (a['name'],a['descriptor'])==SECONDARY['com/apple/xsr/net/CommunicationsManager.class'][:2]) or (name=='getBody' and (a['name'],a['descriptor']) in (('<init>','(Lcom/apple/xsr/net/HttpConnection;)V'),('parseHeaders','()V'))):
            if before[a['start']:a['start']+8] != after[b['start']:b['start']+8]:
                raise ValueError('Target signature/access/attribute count changed')
            old_attrs = [before[s:e] for n,s,e in a['attributes'] if n != 'Code']
            new_attrs = [after[s:e] for n,s,e in b['attributes'] if n != 'Code']
            if old_attrs != new_attrs: raise ValueError('Target non-Code attributes changed')
        elif before[a['start']:a['end']] != after[b['start']:b['end']]:
            raise ValueError('Non-target method changed')

    if name == '<init>': assert_sync_preenqueue(before,after)
    if name == 'run': assert_connect_failure_stop(before,after)
    if name in ('run','send'): assert_recovery_edit(before,after,name)
    if name=='getBody':
        assert_allocation_operands(before,after)
        assert_header_insertion(before,after)
        assert_framing_assignment(before,after)


def assert_allocation_operands(before, after):
    """Only the parse and allocation operands may change; Code subattributes stay fixed."""
    old,new=ClassFile(before),ClassFile(after)
    def code(cls,data):
        methods=[m for m in cls.methods if (m['name'],m['descriptor'])==('getBody','()[B')]
        attrs=[a for a in methods[0]['attributes'] if a[0]=='Code']
        _,start,end=attrs[0]
        return bytearray(data[start:end])
    a,b=code(old,before),code(new,after)
    assert_static_reference(new,b,14+5,'compat/ResponseFraming','lengthHeader','(Lcom/apple/xsr/net/HttpResponse;Ljava/lang/String;)Ljava/lang/String;')
    if b[14+14]!=0xb8:raise ValueError('Length parse opcode differs')
    tag,value=new.pool[u2(b,14+15)]
    if tag!=10:raise ValueError('Length parser must be Methodref')
    ot,ov=new.pool[u2(value,0)];nt,nv=new.pool[u2(value,2)]
    if ot!=7 or new.text(u2(ov,0))!='compat/BoundedResponseBuffer' or nt!=12 or new.text(u2(nv,0))!='parseLength' or new.text(u2(nv,2))!='(Ljava/lang/String;)I':raise ValueError('Length parser helper target differs')
    allocation_class=u2(b,14+24);constructor=u2(b,14+29)
    tag,value=new.pool[allocation_class]
    if tag!=7 or new.text(u2(value,0))!='compat/BoundedResponseBuffer':
        raise ValueError('Response allocation class operand differs')
    tag,value=new.pool[constructor]
    if tag!=10 or u2(value,0)!=allocation_class: raise ValueError('Response constructor operand owner differs')
    tag,signature=new.pool[u2(value,2)]
    if tag!=12 or new.text(u2(signature,0))!='<init>' or new.text(u2(signature,2))!='(I)V':
        raise ValueError('Response constructor operand signature differs')
    if len(a)!=len(b): raise ValueError('Response Code length changed')
    for offset in (14+15,14+24,14+29):
        b[offset:offset+2]=a[offset:offset+2]
    b[14+5:14+8]=a[14+5:14+8]
    if a!=b: raise ValueError('Response modification outside allocation operands')


def assert_static_reference(cls,code,offset,owner,name,descriptor):
    if code[offset]!=0xb8:raise ValueError('Framing opcode differs')
    try:
        tag,value=cls.pool[u2(code,offset+1)];ot,ov=cls.pool[u2(value,0)];nt,nv=cls.pool[u2(value,2)]
        if tag!=10 or ot!=7 or cls.text(u2(ov,0))!=owner or nt!=12 or cls.text(u2(nv,0))!=name or cls.text(u2(nv,2))!=descriptor:raise ValueError('Framing helper target differs')
    except (KeyError,struct.error):raise ValueError('Framing helper reference invalid') from None


def assert_framing_assignment(before,after):
    old,new=ClassFile(before),ClassFile(after)
    def code(cls,data):
        method=next(m for m in cls.methods if (m['name'],m['descriptor'])==('parseHeaders','()V'))
        _,begin,end=next(a for a in method['attributes'] if a[0]=='Code')
        return bytearray(data[begin:end])
    a,b=code(old,before),code(new,after)
    assert_static_reference(new,b,14+93,'compat/ResponseFraming','setHeader','(Lcom/apple/xsr/net/HttpResponse;Ljava/lang/String;Ljava/lang/String;)V')
    assert_static_reference(new,b,14+130,'compat/ResponseFraming','invalidHeader','()Ljava/lang/RuntimeException;')
    if len(a)!=len(b):raise ValueError('Header parser Code length changed')
    if b[14+133:14+157]!=b'\xbf'+bytes(23):raise ValueError('Invalid header terminal block differs')
    b[14+130:14+157]=a[14+130:14+157]
    b[14+93:14+96]=a[14+93:14+96]
    if a!=b:raise ValueError('Header parser differs outside framing assignment')


def assert_header_insertion(before,after):
    old,new=ClassFile(before),ClassFile(after)
    def code(cls,data):
        method=next(m for m in cls.methods if (m['name'],m['descriptor'])==('<init>','(Lcom/apple/xsr/net/HttpConnection;)V'))
        _,begin,end=next(a for a in method['attributes'] if a[0]=='Code')
        return data[begin:end]
    a,b=code(old,before),code(new,after)
    if len(b)!=len(a)+3 or a[:2]!=b[:2] or u4(b,2)!=u4(a,2)+3 or a[6:10]!=b[6:10] or u4(a,10)!=44 or u4(b,10)!=47:
        raise ValueError('Header constructor frame or lengths differ')
    if b[14:50]!=a[14:50] or b[50]!=0xb8 or b[53:61]!=a[50:58] or b[61:]!=a[58:] or a[58:]!=bytes(4):
        raise ValueError('Header constructor differs outside insertion')
    tag,value=new.pool[u2(b,51)]
    if tag!=10: raise ValueError('Header wrapper is not static method reference')
    tag,owner=new.pool[u2(value,0)];nt,signature=new.pool[u2(value,2)]
    if tag!=7 or new.text(u2(owner,0))!='compat/BoundedHeaderStream' or nt!=12 or new.text(u2(signature,0))!='wrap' or new.text(u2(signature,2))!='(Ljava/io/InputStream;)Ljava/io/InputStream;':
        raise ValueError('Header wrapper insertion target differs')


def assert_recovery_edit(before,after,name):
    if name=='run' and stop_is_volatile(after):after=assert_stop_lock_order(before,after)
    old,new=ClassFile(before),ClassFile(after)
    def attribute(cls,data):
        m=next(m for m in cls.methods if m['name']==name)
        _,b,e=next(a for a in m['attributes'] if a[0]=='Code')
        return data[b:e]
    a,b=attribute(old,before),attribute(new,after)
    def methodref(index,method,descriptor):
        try:
            tag,value=new.pool[index]
            if tag!=10: raise ValueError('Recovery target must be Methodref')
            tag,owner=new.pool[u2(value,0)];nt,sig=new.pool[u2(value,2)]
            if tag!=7 or new.text(u2(owner,0))!='compat/RejectionRecovery' or nt!=12 or new.text(u2(sig,0))!=method or new.text(u2(sig,2))!=descriptor:
                raise ValueError('Recovery helper target differs')
        except (KeyError,struct.error):raise ValueError('Recovery helper reference invalid') from None
    if name=='run':
        window=b[14+464:14+474]
        if len(b)!=len(a)+42 or a[:2]!=b[:2] or u4(b,2)!=u4(a,2)+42 or a[6:10]!=b[6:10] or a[6:10]!=bytes.fromhex('00060009') or u4(a,10)!=553 or u4(b,10)!=595 or window[:4]!=b'\x2a\x19\x05\xb8' or window[6:]!=bytes(4):raise ValueError('Recovery run frames or report substitution differs')
        methodref(u2(window,4),'report','(Lcom/apple/xsr/net/CommunicationsManager;Ljava/lang/Exception;)V')
        if a[14+349:14+352]!=bytes.fromhex('99001f') or b[14+349:14+352]!=bytes.fromhex('9900d6') or b[14+380:14+459]!=a[14+380:14+459]:raise ValueError('Ambiguous IO branch or retained retry block differs')
        if b[14+339:14+344]!=bytes.fromhex('c8000000d6'):raise ValueError('IO trampoline entry differs')
        added=b[14+553:14+578]
        if added[:11]!=bytes.fromhex('1905b6004759c7000e57b8') or added[13:]!=bytes.fromhex('3a05c8ffffff98c800000005'):raise ValueError('IO trampoline branches or stack operations differ')
        methodref(u2(added,11),'nullMessage','()Ljava/lang/Exception;')
        tail_block=b[14+578:14+595]
        if tail_block[:10]!=bytes.fromhex('1248b6004999ffec2ab8') or tail_block[12:]!=bytes.fromhex('c8ffffff12'):raise ValueError('Prefix stop tail differs')
        methodref(u2(tail_block,10),'retire','(Lcom/apple/xsr/net/CommunicationsManager;)V')
        if b[14+595+30:14+595+32]!=word(462) or a[14+553+30:14+553+32]!=word(307):raise ValueError('Malformed-input handler routing differs')
        masked=bytearray(b[:14+553]+b[14+595:]);masked[:14]=a[:14]
        masked[14+553+30:14+553+32]=word(307)
        masked[14+339:14+344]=a[14+339:14+344];masked[14+350:14+352]=a[14+350:14+352];masked[14+464:14+474]=a[14+464:14+474]
        if bytes(masked)!=a:raise ValueError('Run changed outside exact IO/report windows and appended block')
    else:
        if len(b)!=len(a)+13 or a[:2]!=b[:2] or u4(b,2)!=u4(a,2)+13 or a[6:10]!=b[6:10] or u4(a,10)!=392 or u4(b,10)!=397 or b[14:406]!=a[14:406]:
            raise ValueError('Send frames/code differ outside appended handler')
        code=b[406:411]
        if code[:2]!=b'\x2a\xb8' or code[4:]!=b'\xbf': raise ValueError('Send recovery handler differs')
        methodref(u2(code,2),'sendFailure','(Ljava/lang/Throwable;Lcom/apple/xsr/net/AcpxConnection;)Ljava/lang/Throwable;')
        if u2(a,406)!=3 or u2(b,411)!=4 or b[413:421]!=a[408:416] or b[429:]!=a[416:]: raise ValueError('Send original handlers/subattributes changed')
        added=b[421:429]
        if added[:6]!=struct.pack('>HHH',32,271,392): raise ValueError('Send marker coverage differs')
        tag,value=new.pool[u2(added,6)]
        if tag!=7 or new.text(u2(value,0))!='compat/UntrustedResponseException': raise ValueError('Send catch marker differs')


def assert_sync_preenqueue(before,after):
    old,new=ClassFile(before),ClassFile(after)
    if before[:old.pool_end]!=after[:new.pool_end]:raise ValueError('Sync original pool changed')
    def body(cls):
        ms=[m for m in cls.methods if m['name']=='<init>']
        if len(ms)!=1:raise ValueError('Sync constructor missing')
        attrs=[a for a in ms[0]['attributes'] if a[0]=='Code']
        if len(attrs)!=1:raise ValueError('Sync Code missing')
        _,begin,end=attrs[0];return cls.data[begin:end]
    a,b=body(old),body(new)
    if u4(a,10)!=109 or u4(b,10)!=138 or a[6:10]!=bytes.fromhex('00070007') or a[6:10]!=b[6:10]:raise ValueError('Sync Code/frame lengths changed')
    if b[14+14:14+20]!=bytes.fromhex('a7005f000000') or b[14+109:14+138]!=a[14+31:14+51]+a[14+14:14+20]+bytes.fromhex('a7ff8d'):raise ValueError('Sync preenqueue trampoline differs')
    restored=bytearray(b[:14+109]+b[14+138:]);restored[2:6]=a[2:6];restored[10:14]=a[10:14];restored[14+14:14+20]=a[14+14:14+20]
    if bytes(restored)!=a:raise ValueError('Sync edit outside preenqueue trampoline')
    if u2(a,14+109)!=3 or a[14+111:14+135]!=bytes.fromhex('001f0037003a000b00180062006500000065006900650000') or a[14+135:]!=bytes(2):raise ValueError('Sync handlers or nested attributes differ')


def assert_connect_failure_stop(before,after):
    if stop_is_volatile(after):after=assert_stop_lock_order(before,after)
    old,new=ClassFile(before),ClassFile(after)
    def locate(cls,name):
        ms=[m for m in cls.methods if m['name']==name]
        if len(ms)!=1:raise ValueError('Connect/worker method missing')
        attrs=[a for a in ms[0]['attributes'] if a[0]=='Code']
        if len(attrs)!=1:raise ValueError('Connect/worker Code missing')
        _,b,e=attrs[0];return b,e,cls.data[b:e]
    ob,oe,a=locate(old,'doConnect');nb,ne,b=locate(new,'doConnect');_,_,run=locate(new,'run')
    if u4(a,10)!=718 or u4(b,10)!=754 or a[6:10]!=bytes.fromhex('00060010') or a[6:10]!=b[6:10]:raise ValueError('Connect length/frame differs')
    if b[14+393:14+401]!=bytes.fromhex('c800000145000000') or b[14+578:14+583]!=bytes.fromhex('c8000000a2'):raise ValueError('Connect stop entry differs')
    reference=run[14+588:14+590]
    assert_static_reference(new,run,14+587,'compat/RejectionRecovery','retire','(Lcom/apple/xsr/net/CommunicationsManager;)V')
    expected=bytes.fromhex('2a04b5000d2ab8')+reference+a[14+393:14+401]+bytes.fromhex('c8fffffeb2')+bytes.fromhex('2ab8')+reference+a[14+578:14+583]+bytes.fromhex('c8ffffff5a')
    if b[14+718:14+754]!=expected:raise ValueError('Connect stop tail differs')
    restored=bytearray(b[:14+718]+b[14+754:]);restored[2:6]=a[2:6];restored[10:14]=a[10:14];restored[14+393:14+401]=a[14+393:14+401];restored[14+578:14+583]=a[14+578:14+583]
    if bytes(restored)!=a:raise ValueError('Connect differs outside stop windows')
    if u2(a,14+718)!=6 or any(u2(a,14+720+i*8+2)>681 for i in range(6)):raise ValueError('Connect handler coverage differs')
    baseline=after[:nb]+a+after[ne:]
    if hashlib.sha256(baseline).hexdigest()!=AUDIT17_MANAGER_SHA256:raise ValueError('Worker/class differs from audit.17 outside connect Code')
    for index,owner,name,descriptor in ((13,'com/apple/xsr/net/CommunicationsManager','connectionFailureSent','Z'),(14,'com/apple/xsr/net/CommunicationsManager','system','Lcom/apple/xsr/som/RaidSystem;'),(38,'com/apple/xsr/net/CommunicationsManager','logger','Lorg/apache/log4j/Logger;')):
        tag,v=new.pool[index];ot,ov=new.pool[u2(v,0)];nt,nv=new.pool[u2(v,2)]
        if tag!=9 or ot!=7 or new.text(u2(ov,0))!=owner or nt!=12 or new.text(u2(nv,0))!=name or new.text(u2(nv,2))!=descriptor:raise ValueError('Connect original field target differs')


def stop_is_volatile(data):
    fields=[f for f in ClassFile(data).fields if f['name']=='stopped' and f['descriptor']=='Z']
    if len(fields)!=1:raise ValueError('Stopped field identity differs')
    return bool(fields[0]['access']&0x40)


def assert_stop_lock_order(before,after):
    """Restore two reads and one field flag to reconstruct the entire audit.18 class."""
    if hashlib.sha256(before).hexdigest()!=TARGETS['com/apple/xsr/net/CommunicationsManager.class'][0]:raise ValueError('Original Manager reference differs')
    after=normalize_stopped_admission(after)
    new=ClassFile(after)
    fields=[f for f in new.fields if f['name']=='stopped' and f['descriptor']=='Z']
    if len(fields)!=1 or fields[0]['access']!=0x42:raise ValueError('Stopped field must be private volatile only')
    field=fields[0];run=next(m for m in new.methods if m['name']=='run');_,b,e=next(a for a in run['attributes'] if a[0]=='Code')
    if u4(after,b+10)!=595 or after[b+6:b+10]!=bytes.fromhex('00060009'):raise ValueError('Stop lock worker frame differs')
    for pc in (18,45):
        if after[b+14+pc:b+14+pc+3]!=bytes.fromhex('b4000b'):raise ValueError('Queue stop read must use direct field')
    tag,v=new.pool[11];ot,ov=new.pool[u2(v,0)];nt,nv=new.pool[u2(v,2)]
    if tag!=9 or ot!=7 or new.text(u2(ov,0))!='com/apple/xsr/net/CommunicationsManager' or nt!=12 or new.text(u2(nv,0))!='stopped' or new.text(u2(nv,2))!='Z':raise ValueError('Direct stop field target differs')
    restored=bytearray(after);restored[field['start']:field['start']+2]=word(2)
    for pc in (18,45):restored[b+14+pc:b+14+pc+3]=bytes.fromhex('b6001b')
    restored=bytes(restored)
    if hashlib.sha256(restored).hexdigest()!=AUDIT18_MANAGER_SHA256:raise ValueError('Class differs from audit.18 outside stop lock edits')
    return restored


AUDIT19_MANAGER_SHA256='cfefcc5b8cb0b0c15b5f63788503c8e41414b01abe2dbcedcc95cdebca8ecc24'
POST_DESCRIPTOR='(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/net/RequestMessage;Ljava/lang/Object;)V'
POST_CODE=bytes.fromhex('00a30000005400060006000000382ab4000a593a04c22ab4000abb0015592b2cb900160100c000172db70018b60019572ab4000ab6001a1904c3a7000b3a051904c31905bfb100020008002c002f0000002f0034002f00000000')


def admission_pool():
    # Append ten exact constants after the measured audit.19 pool. Never renumber it.
    def utf(value):
        data=value.encode('ascii');return b'\x01'+word(len(data))+data
    return (utf('currentThread')+utf('()Ljava/lang/Thread;')+b'\x0c'+word(395)+word(396)+
            b'\x0a'+word(15)+word(397)+utf('compat/StoppedDelivery')+b'\x07'+word(399)+
            utf('deliver')+utf('(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Ljava/lang/Object;Z)V')+
            b'\x0c'+word(401)+word(402)+b'\x0a'+word(400)+word(403))


def admission_code():
    code=bytearray(POST_CODE[14:70]);code[30:34]=bytes.fromhex('a7001a00')
    # Both add and refusal monitorexit lie inside the new [56,84) cleanup range.
    code.extend(bytes.fromhex('2ab4000b99000db8018e2ab40001a6000ab6001957a7ffd5581904c32b2ab4000e2d2bc1001eb80194b1'))
    if len(code)!=98:raise ValueError('Admission code length differs')
    body=bytes.fromhex('00060006')+struct.pack('>I',98)+code+bytes.fromhex('00030008002c002f0000002f0034002f000000380054002f00000000')
    return POST_CODE[:2]+struct.pack('>I',len(body))+body


def post_code(cls):
    methods=[m for m in cls.methods if (m['name'],m['descriptor'])==('postMessageAsync',POST_DESCRIPTOR)]
    if len(methods)!=1 or methods[0]['access']!=1:raise ValueError('Admission target identity differs')
    attrs=[a for a in methods[0]['attributes'] if a[0]=='Code']
    if len(attrs)!=1:raise ValueError('Admission Code missing or duplicated')
    return attrs[0][1:]


def stopped_admission(data):
    if hashlib.sha256(data).hexdigest()!=AUDIT19_MANAGER_SHA256:raise ValueError('Admission reference must be exact audit.19 Manager')
    cls=ClassFile(data);b,e=post_code(cls)
    if cls.pool_count!=395 or data[b:e]!=POST_CODE:raise ValueError('Admission reference shape differs')
    tag,value=cls.pool[15]
    if tag!=7 or cls.text(u2(value,0))!='java/lang/Thread':raise ValueError('Admission Thread target differs')
    result=data[:8]+word(405)+data[10:cls.pool_end]+admission_pool()+data[cls.pool_end:b]+admission_code()+data[e:]
    if normalize_stopped_admission(result)!=data:raise ValueError('Admission reconstruction differs')
    return result


def normalize_stopped_admission(data):
    cls=ClassFile(data);b,e=post_code(cls)
    if data[b:e]==POST_CODE:return data  # Exact unchanged historical post Code only.
    if cls.pool_count!=405 or data[b:e]!=admission_code():raise ValueError('Stopped admission differs from exact reviewed Code')
    # Pool indices 1..394 and every unrelated byte must reconstruct the full prior class.
    at=10
    for index,(tag,value) in cls.pool.items():
        if index < 395:at+=1+len(value)+(2 if tag==1 else 0)
    if data[at:cls.pool_end]!=admission_pool():raise ValueError('Admission constant-pool tail differs')
    restored=data[:8]+word(395)+data[10:at]+data[cls.pool_end:b]+POST_CODE+data[e:]
    if hashlib.sha256(restored).hexdigest()!=AUDIT19_MANAGER_SHA256:raise ValueError('Class differs outside stopped admission edits')
    return restored
