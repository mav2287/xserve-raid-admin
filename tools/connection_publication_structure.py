"""Independent javap validation of private connection publication; no transformer imports."""
import re

OPS=[(0,'aload_0'),(1,'getfield #14 // Field connection:Lcom/apple/xsr/net/HttpConnection;'),
 (4,'ifnonnull 39'),(7,'new #66 // class com/apple/xsr/net/HttpConnection'),(10,'dup'),
 (11,'aload_0'),(12,'getfield #12 // Field host:Ljava/lang/String;'),
 (15,'invokespecial #67 // Method com/apple/xsr/net/HttpConnection."<init>":(Ljava/lang/String;)V'),
 (18,'astore_1'),(19,'aload_1'),(20,'aload_0'),(21,'getfield #7 // Field persistent:Z'),
 (24,'invokevirtual #68 // Method com/apple/xsr/net/HttpConnection.setPersistent:(Z)V'),
 (27,'aload_1'),(28,'invokevirtual #69 // Method com/apple/xsr/net/HttpConnection.open:()V'),
 (31,'aload_0'),(32,'aload_1'),(33,'putfield #14 // Field connection:Lcom/apple/xsr/net/HttpConnection;'),
 (36,'goto 47'),(39,'getstatic #28 // Field logger:Lorg/apache/log4j/Logger;'),
 (42,'ldc #70 // String Attempt to create a connection with an existing connection open'),
 (44,'invokevirtual #71 // Method org/apache/log4j/Logger.warn:(Ljava/lang/Object;)V'),(47,'return')]

def method(text):
    m=re.search(r'^  private void createConnection\(\) throws java\.io\.IOException;\n.*?(?=^  \S|^})',text,re.M|re.S)
    if m is None:raise ValueError('Private connection method missing')
    return m[0]

def check_publication(text):
    body=method(text)
    if 'descriptor: ()V' not in body or 'flags: ACC_PRIVATE' not in body or 'stack=3, locals=2, args_size=1' not in body:
        raise ValueError('Connection publication identity/frame differs')
    code=re.search(r'^    Code:\n(.*?)(?=^    \S|\Z)',body,re.M|re.S)
    lines=[line.strip() for line in code[1].splitlines() if line.strip()] if code else []
    if len(lines)!=len(OPS)+1 or any(not re.fullmatch(r'\d+:\s+.*',line) for line in lines[1:]):
        raise ValueError('Unexpected connection Code metadata')
    ops=[(int(pc),' '.join(op.split())) for pc,op in re.findall(r'^\s+(\d+):\s+(.*)$',body,re.M)]
    if ops!=OPS:raise ValueError('Connection publication instructions differ')

def normalize_publication(before,after):
    check_publication(after)
    old,new=method(before),method(after)
    block=lambda body:re.search(r'^    Code:\n.*?(?=^    \S|\Z)',body,re.M|re.S)[0]
    oldcode,newcode=block(old),block(new)
    if old.replace(oldcode,'')!=new.replace(newcode,''):
        raise ValueError('Connection method non-Code metadata differs')
    return after.replace(new,new.replace(newcode,oldcode),1)
