"""Independent javap admission check; does not import the bytecode transformer."""
import re

HEADER='  public void postMessageAsync(com.apple.xsr.net.CommunicationHandler, com.apple.xsr.net.RequestMessage, java.lang.Object);'
TAIL=[
 (56,'aload_0'),(57,'getfield #11 // Field stopped:Z'),(60,'ifeq 73'),
 (63,'invokestatic #398 // Method java/lang/Thread.currentThread:()Ljava/lang/Thread;'),
 (66,'aload_0'),(67,'getfield #1 // Field thread:Ljava/lang/Thread;'),(70,'if_acmpne 80'),
 (73,'invokevirtual #25 // Method java/util/LinkedList.add:(Ljava/lang/Object;)Z'),(76,'pop'),(77,'goto 34'),
 (80,'pop2'),(81,'aload 4'),(83,'monitorexit'),(84,'aload_1'),(85,'aload_0'),
 (86,'getfield #14 // Field system:Lcom/apple/xsr/som/RaidSystem;'),(89,'aload_3'),(90,'aload_1'),
 (91,'instanceof #30 // class com/apple/xsr/net/CommunicationsManager$SyncSender'),
 (94,'invokestatic #404 // Method compat/StoppedDelivery.deliver:(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Ljava/lang/Object;Z)V'),(97,'return')]

def part(text):
    m=re.search('^'+re.escape(HEADER)+r'\n.*?(?=^  \S|^})',text,re.M|re.S)
    if m is None:raise ValueError('Independent admission descriptor missing')
    return m[0]


def normalize_admission(before,after,required=False):
    a,b=part(before),part(after)
    def ops(text):return [(int(pc),' '.join(rest.split())) for pc,rest in re.findall(r'^\s+(\d+):\s+(.*)$',text,re.M)]
    ai,bi=ops(a),ops(b)
    if not any(pc>=56 for pc,_ in bi):
        if required:raise ValueError('Stopped admission missing')
        return after
    if [(pc,op) for pc,op in bi if pc>=56]!=TAIL or [(pc,op) for pc,op in bi if 30<=pc<34]!=[(30,'goto 56'),(33,'nop')]:raise ValueError('Independent admission instructions differ')
    if [(pc,op) for pc,op in ai if pc not in (30,33)]!=[(pc,op) for pc,op in bi if pc<56 and pc not in (30,33)]:raise ValueError('Admission changed original clone/notify/monitor instructions')
    rows=lambda text:re.findall(r'^\s+(\d+)\s+(\d+)\s+(\d+)\s+(any|Class \S+)\s*$',text,re.M)
    if rows(a)!=[('8','44','47','any'),('47','52','47','any')] or rows(b)!=rows(a)+[('56','84','47','any')]:raise ValueError('Admission monitor cleanup coverage differs')
    def metadata(text):return '\n'.join(line for line in text.splitlines() if not re.match(r'^\s+\d+(?::|\s+\d+\s+\d+\s+)',line))
    if metadata(a)!=metadata(b) or 'stack=6, locals=6, args_size=4' not in b:raise ValueError('Admission metadata/frame differs')
    expected=[
      ('395','Utf8','currentThread'),('396','Utf8','()Ljava/lang/Thread;'),('397','NameAndType','#395:#396 // currentThread:()Ljava/lang/Thread;'),('398','Methodref','#15.#397 // java/lang/Thread.currentThread:()Ljava/lang/Thread;'),
      ('399','Utf8','compat/StoppedDelivery'),('400','Class','#399 // compat/StoppedDelivery'),('401','Utf8','deliver'),('402','Utf8','(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Ljava/lang/Object;Z)V'),('403','NameAndType','#401:#402 // deliver:(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Ljava/lang/Object;Z)V'),('404','Methodref','#400.#403 // compat/StoppedDelivery.deliver:(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Ljava/lang/Object;Z)V')]
    pool=[(i,t,' '.join(v.split())) for i,t,v in re.findall(r'^\s+#(\d+) = (\S+)\s+(.*)$',after,re.M) if int(i)>=395]
    if pool!=expected:raise ValueError('Independent admission constant pool differs')
    return after.replace(b,a,1)
