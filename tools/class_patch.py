"""Hash-locked method substitutions and operand edits; unrelated bytes stay fixed."""
import hashlib
import struct

TARGETS = {
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
        for _ in range(field_count): _, at = self.member(at)
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
    if name == 'getBody':
        if u2(data,6) != 47: raise ValueError('Unexpected legacy verifier version')
        _, begin, end = codes[0]
        start = begin + 14
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
        replacement = bytearray(data[begin:end])
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
        edits=sorted([(begin,end,bytes(replacement)),(cb,ce,constructor_replacement)])
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
    else:
        constant = append(8, word(utf8(REDACTED)))
        code = b'\x13' + word(constant) + b'\xb0'  # ldc_w even when the index happens to fit in one byte
        stack, local = 1, 1
    _, begin, end = codes[0]
    body = struct.pack('>HHI',stack,local,len(code)) + code + b'\x00\x00\x00\x00'
    replacement = data[begin:begin+2] + struct.pack('>I',len(body)) + body
    result = (data[:8] + word(next_index) + data[10:cls.pool_end] + bytes(extra) +
              data[cls.pool_end:begin] + replacement + data[end:])
    assert_preserved(data, result, name, descriptor)
    return result


def assert_preserved(before, after, name, descriptor):
    old, new = ClassFile(before), ClassFile(after)
    if before[:8] != after[:8] or after[10:old.pool_end] != before[10:old.pool_end]:
        raise ValueError('Original class version or constant pool changed')
    if len(old.methods) != len(new.methods) or old.class_attributes != new.class_attributes:
        raise ValueError('Original method list or class attributes changed')
    if before[old.pool_end:old.methods[0]['start']] != after[new.pool_end:new.methods[0]['start']]:
        raise ValueError('Original class hierarchy, fields or method count changed')
    for a,b in zip(old.methods,new.methods):
        if (a['name'],a['descriptor']) == (name,descriptor) or (name=='getBody' and (a['name'],a['descriptor'])==('<init>','(Lcom/apple/xsr/net/HttpConnection;)V')):
            if before[a['start']:a['start']+8] != after[b['start']:b['start']+8]:
                raise ValueError('Target signature/access/attribute count changed')
            old_attrs = [before[s:e] for n,s,e in a['attributes'] if n != 'Code']
            new_attrs = [after[s:e] for n,s,e in b['attributes'] if n != 'Code']
            if old_attrs != new_attrs: raise ValueError('Target non-Code attributes changed')
        elif before[a['start']:a['end']] != after[b['start']:b['end']]:
            raise ValueError('Non-target method changed')

    if name=='getBody':
        assert_allocation_operands(before,after)
        assert_header_insertion(before,after)


def assert_allocation_operands(before, after):
    """Only allocation-owner operands may change; even Code subattributes are fixed."""
    old,new=ClassFile(before),ClassFile(after)
    def code(cls,data):
        methods=[m for m in cls.methods if (m['name'],m['descriptor'])==('getBody','()[B')]
        attrs=[a for a in methods[0]['attributes'] if a[0]=='Code']
        _,start,end=attrs[0]
        return bytearray(data[start:end])
    a,b=code(old,before),code(new,after)
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
    for offset in (14+24,14+29):
        b[offset:offset+2]=a[offset:offset+2]
    if a!=b: raise ValueError('Response modification outside allocation operands')


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
