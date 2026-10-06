"""Independent javap ownership verification; no transformer or class parser import."""
import re

MANAGER_TAIL=[(595,'aload_2'),(596,'instanceof #30 // class com/apple/xsr/net/CommunicationsManager$SyncSender'),(599,'ifeq 612'),(602,'aload_2'),(603,'checkcast #30 // class com/apple/xsr/net/CommunicationsManager$SyncSender'),(606,'invokevirtual #407 // Method com/apple/xsr/net/CommunicationsManager$SyncSender.claim:()Z'),(609,'ifeq 489'),(612,'aload_1'),(613,'invokevirtual #47 // Method com/apple/xsr/net/CommunicationsManager$Transaction.getMessage:()Lcom/apple/xsr/net/RequestMessage;'),(616,'astore 5'),(618,'goto_w 247')]
INTERRUPT_TAIL=[(138,'astore 4'),(140,'aload_0'),(141,'getfield #3 // Field handled:Z'),(144,'ifne 96'),(147,'aload_0'),(148,'getfield #75 // Field claimed:Z'),(151,'ifne 24'),(154,'goto_w 60')]
RESPONSE_GUARD=[(0,'aload_0'),(1,'getfield #3 // Field handled:Z'),(4,'ifeq 8'),(7,'return')]
CLAIM_OPS=[(0,'aload_0'),(1,'getfield #3 // Field handled:Z'),(4,'ifne 21'),(7,'aload_0'),(8,'getfield #75 // Field claimed:Z'),(11,'ifne 21'),(14,'aload_0'),(15,'iconst_1'),(16,'putfield #75 // Field claimed:Z'),(19,'iconst_1'),(20,'ireturn'),(21,'iconst_0'),(22,'ireturn')]
MANAGER_POOL=[(405,'Utf8','claim'),(406,'NameAndType','#405:#171 // claim:()Z'),(407,'Methodref','#30.#406 // com/apple/xsr/net/CommunicationsManager$SyncSender.claim:()Z')]
SENDER_POOL=[(73,'Utf8','claimed'),(74,'NameAndType','#73:#25 // claimed:Z'),(75,'Fieldref','#19.#74 // com/apple/xsr/net/CommunicationsManager$SyncSender.claimed:Z'),(76,'Utf8','claim'),(77,'Utf8','()Z')]


def ops(text):return [(int(pc),' '.join(rest.split())) for pc,rest in re.findall(r'^\s+(\d+):\s+(.*)$',text,re.M)]
def rows(text):return [(int(a),int(b),int(c),kind) for a,b,c,kind in re.findall(r'^\s+(\d+)\s+(\d+)\s+(\d+)\s+(any|Class \S+)\s*$',text,re.M)]
def metadata(text):return '\n'.join(line for line in text.splitlines() if not re.match(r'^\s+\d+(?::|\s+\d+\s+\d+\s+)',line))
def members(text):
 result={}
 for m in re.finditer(r'^  (\S[^\n]*;)\n.*?(?=^  \S|^})',text,re.M|re.S):
  if m[1] in result:raise ValueError('Duplicate javap member')
  result[m[1]]=m[0]
 return result


def check(before,after,kind):
 if kind not in ('manager','sender'):raise ValueError('Unknown ownership class')
 pool=lambda text:[(int(i),tag,' '.join(v.split())) for i,tag,v in re.findall(r'^\s+#(\d+) = (\S+)\s+(.*)$',text,re.M)]
 if pool(after)!=pool(before)+(MANAGER_POOL if kind=='manager' else SENDER_POOL):raise ValueError('Independent ownership pool differs')
 a,b=members(before),members(after)
 if kind=='manager':
  header='public void run();'
  if set(a)!=set(b):raise ValueError('Ownership Manager members differ')
  ai,bi=ops(a[header]),ops(b[header]);old=[(241,'aload_1'),(242,'invokevirtual #47 // Method com/apple/xsr/net/CommunicationsManager$Transaction.getMessage:()Lcom/apple/xsr/net/RequestMessage;'),(245,'astore 5')]
  if [op for op in ai if 241<=op[0]<247]!=old or [op for op in bi if 241<=op[0]<247]!=[(241,'goto_w 595'),(246,'nop')]:raise ValueError('Independent claim entry differs')
  if [op for op in bi if op[0]>=595]!=MANAGER_TAIL or [op for op in bi if op[0]<595 and not 241<=op[0]<247]!=[op for op in ai if not 241<=op[0]<247]:raise ValueError('Independent claim instructions differ')
  covering=[(handler,typ) for start,end,handler,typ in rows(a[header]) if start<=241 and end>=247]
  expected=[(462,'Class sun/io/MalformedInputException'),(337,'Class java/io/IOException'),(462,'Class java/lang/Exception'),(525,'Class java/lang/InterruptedException')]
  if covering!=expected or rows(b[header])!=rows(a[header])+[(595,623,h,t) for h,t in expected]:raise ValueError('Independent claim exception coverage differs')
  if metadata(a[header])!=metadata(b[header]):raise ValueError('Independent worker metadata differs')
  b[header]=a[header]
 else:
  field='private boolean claimed;';claim='synchronized boolean claim();'
  if set(b)!=set(a)|{field,claim}:raise ValueError('Ownership Sender members differ')
  if b[field]!='  private boolean claimed;\n    descriptor: Z\n    flags: ACC_PRIVATE\n\n':raise ValueError('Independent claimed field differs')
  if metadata(b[claim])!='  synchronized boolean claim();\n    descriptor: ()Z\n    flags: ACC_SYNCHRONIZED\n    Code:\n      stack=2, locals=1, args_size=1' or rows(b[claim]) or ops(b[claim])!=CLAIM_OPS:raise ValueError('Independent claim method differs')
  ctor='public com.apple.xsr.net.CommunicationsManager$SyncSender(com.apple.xsr.net.CommunicationsManager, com.apple.xsr.net.RequestMessage);'
  response='public synchronized void handleResponse(com.apple.xsr.som.RaidSystem, com.apple.xsr.net.Response, java.lang.Object);'
  if ops(b[ctor])!=ops(a[ctor])+INTERRUPT_TAIL:raise ValueError('Independent interrupt instructions differ')
  original=[(31,55,58,'Class java/lang/InterruptedException'),(24,98,101,'any'),(101,105,101,'any')]
  expected=[(31,55,138,'Class java/lang/InterruptedException')]+original[1:]+[(138,159,101,'any')]
  if rows(a[ctor])!=original or rows(b[ctor])!=expected or metadata(a[ctor])!=metadata(b[ctor]):raise ValueError('Independent interrupt cleanup/frame differs')
  if ops(b[response])!=RESPONSE_GUARD+[(pc+8,op) for pc,op in ops(a[response])] or metadata(a[response])!=metadata(b[response]) or rows(b[response]):raise ValueError('Independent first reply guard differs')
  del b[field];del b[claim];b[ctor]=a[ctor];b[response]=a[response]
 if {k:v.rstrip() for k,v in a.items()}!={k:v.rstrip() for k,v in b.items()}:raise ValueError('Unrelated ownership members differ')
