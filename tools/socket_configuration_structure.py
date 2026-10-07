"""Independent javap check for the initial read-timeout delegate; no transformer imports."""
import re

OPS=[(0,'aload_0'),(1,'aload_0'),(2,'getfield #13 // Field host:Ljava/lang/String;'),
     (5,'aload_0'),(6,'getfield #9 // Field timeout:I'),
     (9,'invokestatic #202 // Method compat/SocketConfiguration.open:(Ljava/lang/String;I)Ljava/net/Socket;'),
     (12,'putfield #26 // Field socket:Ljava/net/Socket;'),(15,'return')]
POOL=[('198','Utf8','compat/SocketConfiguration'),('199','Class','#198 // compat/SocketConfiguration'),
      ('200','Utf8','(Ljava/lang/String;I)Ljava/net/Socket;'),
      ('201','NameAndType','#100:#200 // open:(Ljava/lang/String;I)Ljava/net/Socket;'),
      ('202','Methodref','#199.#201 // compat/SocketConfiguration.open:(Ljava/lang/String;I)Ljava/net/Socket;')]

def check_socket_setup(text):
    method=re.search(r'^  private void createSocket\(int\) throws java\.io\.IOException;\n.*?(?=^  \S|^})',text,re.M|re.S)
    if method is None:raise ValueError('Socket delegate method missing')
    body=method[0]
    if 'descriptor: (I)V' not in body or 'flags: ACC_PRIVATE' not in body or 'stack=3, locals=2, args_size=2' not in body:
        raise ValueError('Socket delegate identity/frame differs')
    if 'Exception table:' in body or 'LineNumberTable:' in body or 'StackMapTable:' in body:
        raise ValueError('Unexpected socket delegate Code metadata')
    ops=[(int(pc),' '.join(op.split())) for pc,op in re.findall(r'^\s+(\d+):\s+(.*)$',body,re.M)]
    if ops!=OPS:raise ValueError('Socket delegate argument/publication instructions differ')
    pool=[(i,kind,' '.join(value.split())) for i,kind,value in re.findall(r'^\s+#(\d+) = (\S+)\s+(.*)$',text,re.M) if int(i)>=198]
    if pool!=POOL:raise ValueError('Socket delegate appended pool differs')
