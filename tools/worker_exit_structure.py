"""Independent javap worker/ownership gates, using hash-pinned reviewed predecessors."""
import hashlib
import re
from pathlib import Path
from sync_ownership_structure import members,ops,rows,metadata,check
ROOT=Path(__file__).resolve().parents[1]
PINS={
 'sync-ownership-candidate-manager':'86aebc2d839bbab959dfcea1befbaa1349baf53f64bf1f1ba2b01c77ae3d2a8f',
 'sync-ownership-reference-sender':'dd4058119dbfbbf8c666baaf6356bcc6d9f1c45b9da694882518ed8e01ede3a2',
 'sync-ownership-reference-manager':'dbba63fa559f71c1b507bdffa695af05d9b928830627a0e99ed41a813747ee6e',
}

def reference(name):
 p=ROOT/'tests/fixtures'/f'{name}.javap'
 if name not in PINS or hashlib.sha256(p.read_bytes()).hexdigest()!=PINS[name]:raise ValueError('Independent predecessor text differs')
 return p.read_text()


def pool(text):return [(int(i),tag,' '.join(v.split())) for i,tag,v in re.findall(r'^\s+#(\d+) = (\S+)\s+(.*)$',text,re.M)]

POOL=[
 (408,'Utf8','workerActiveTxn'),(409,'Utf8','Ljava/lang/Object;'),(410,'Utf8','workerActiveStarted'),
 (411,'NameAndType','#408:#409 // workerActiveTxn:Ljava/lang/Object;'),(412,'Fieldref','#131.#411 // com/apple/xsr/net/CommunicationsManager.workerActiveTxn:Ljava/lang/Object;'),
 (413,'NameAndType','#410:#153 // workerActiveStarted:Z'),(414,'Fieldref','#131.#413 // com/apple/xsr/net/CommunicationsManager.workerActiveStarted:Z'),
 (415,'Utf8','dispatchLoop'),(416,'NameAndType','#415:#174 // dispatchLoop:()V'),(417,'Methodref','#131.#416 // com/apple/xsr/net/CommunicationsManager.dispatchLoop:()V'),
 (418,'Utf8','compat/WorkerExit'),(419,'Class','#418 // compat/WorkerExit'),(420,'Utf8','prepare'),(421,'NameAndType','#420:#174 // prepare:()V'),(422,'Methodref','#419.#421 // compat/WorkerExit.prepare:()V'),
 (423,'Utf8','ensurePrepared'),(424,'NameAndType','#423:#174 // ensurePrepared:()V'),(425,'Methodref','#419.#424 // compat/WorkerExit.ensurePrepared:()V'),
 (426,'Utf8','(Lcom/apple/xsr/net/CommunicationsManager;Ljava/util/LinkedList;Ljava/lang/Object;ZLcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/AcpxConnection;Ljava/lang/Throwable;)V'),
 (427,'NameAndType','#173:#426 // exit:(Lcom/apple/xsr/net/CommunicationsManager;Ljava/util/LinkedList;Ljava/lang/Object;ZLcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/AcpxConnection;Ljava/lang/Throwable;)V'),
 (428,'Methodref','#419.#427 // compat/WorkerExit.exit:(Lcom/apple/xsr/net/CommunicationsManager;Ljava/util/LinkedList;Ljava/lang/Object;ZLcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/AcpxConnection;Ljava/lang/Throwable;)V'),
 (429,'Utf8','connectCallback'),(430,'Utf8','(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/Response;Ljava/lang/Object;)V'),(431,'NameAndType','#429:#430 // connectCallback:(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/Response;Ljava/lang/Object;)V'),(432,'Methodref','#419.#431 // compat/WorkerExit.connectCallback:(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/Response;Ljava/lang/Object;)V')]
ACTIVE='Field workerActiveTxn:Ljava/lang/Object;';STARTED='Field workerActiveStarted:Z'
CALL='invokeinterface #78, 4 // InterfaceMethod com/apple/xsr/net/CommunicationHandler.handleResponse:(Lcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/Response;Ljava/lang/Object;)V'
TAIL=[
 (623,'checkcast #21 // class com/apple/xsr/net/CommunicationsManager$Transaction'),(626,'astore_1'),(627,'aload_0'),(628,'aload_1'),(629,'putfield #412 // '+ACTIVE),(632,'aload_0'),(633,'iconst_0'),(634,'putfield #414 // '+STARTED),(637,'aload_2'),(638,'monitorexit'),(639,'goto_w 69'),
 (644,'aload_0'),(645,'iconst_1'),(646,'putfield #414 // '+STARTED),(649,'aload_1'),(650,'invokevirtual #47 // Method com/apple/xsr/net/CommunicationsManager$Transaction.getMessage:()Lcom/apple/xsr/net/RequestMessage;'),(653,'astore 5'),(655,'goto_w 618'),
 (660,'aload_0'),(661,'getfield #412 // '+ACTIVE),(664,'ifnull 682'),(667,'aload_0'),(668,'aconst_null'),(669,'putfield #412 // '+ACTIVE),(672,CALL),(677,'goto_w 514'),(682,'pop2'),(683,'pop2'),(684,'goto_w 514'),
 (689,'aload_0'),(690,'aconst_null'),(691,'putfield #412 // '+ACTIVE),(694,'aload_0'),(695,'iconst_0'),(696,'putfield #414 // '+STARTED),(699,'aload_0'),(700,'iconst_0'),(701,'putfield #13 // Field connectionFailureSent:Z'),(704,'goto_w 519')]
WRAPPER=[(0,'invokestatic #425 // Method compat/WorkerExit.ensurePrepared:()V'),(3,'aload_0'),(4,'invokespecial #417 // Method dispatchLoop:()V'),(7,'aconst_null'),(8,'astore_1'),(9,'goto 13'),(12,'astore_1'),(13,'aload_0'),(14,'iconst_1'),(15,'putfield #11 // Field stopped:Z'),(18,'aload_0'),(19,'getfield #412 // '+ACTIVE),(22,'astore_2'),(23,'aload_0'),(24,'getfield #414 // '+STARTED),(27,'istore_3'),(28,'aload_0'),(29,'aconst_null'),(30,'putfield #412 // '+ACTIVE),(33,'aload_0'),(34,'iconst_0'),(35,'putfield #414 // '+STARTED),(38,'aload_0'),(39,'aload_0'),(40,'getfield #10 // Field queue:Ljava/util/LinkedList;'),(43,'aload_2'),(44,'iload_3'),(45,'aload_0'),(46,'getfield #14 // Field system:Lcom/apple/xsr/som/RaidSystem;'),(49,'aload_0'),(50,'getfield #41 // Field connection:Lcom/apple/xsr/net/AcpxConnection;'),(53,'aload_1'),(54,'invokestatic #428 // Method compat/WorkerExit.exit:(Lcom/apple/xsr/net/CommunicationsManager;Ljava/util/LinkedList;Ljava/lang/Object;ZLcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/AcpxConnection;Ljava/lang/Throwable;)V'),(57,'return')]


def normalize_worker(after,required=False):
 if 'private void dispatchLoop();' not in after:
  if required:raise ValueError('Worker wrapper missing')
  return after
 before=reference('sync-ownership-candidate-manager');a,b=members(before),members(after)
 if pool(after)!=pool(before)+POOL:raise ValueError('Independent worker pool differs')
 identity=lambda s:(re.findall(r'^(?:  (?:minor version|major version|flags):.*|public class .*)$',s,re.M), s.split('InnerClasses:',1)[1].strip())
 if identity(before)!=identity(after):raise ValueError('Independent worker identity/inner metadata differs')
 field='private java.lang.Object workerActiveTxn;';started='private boolean workerActiveStarted;';dispatch='private void dispatchLoop();';run='public void run();';ctor='public com.apple.xsr.net.CommunicationsManager(com.apple.xsr.som.RaidSystem);';connect='private void doConnect(com.apple.xsr.net.CommunicationHandler);'
 if set(b)!=set(a)|{field,started,dispatch}:raise ValueError('Worker member list differs')
 for header,desc in ((field,'Ljava/lang/Object;'),(started,'Z')):
  if b[header].rstrip()!=f'  {header}\n    descriptor: {desc}\n    flags: ACC_PRIVATE':raise ValueError('Worker field flags/types differ')
 expected=[x for x in ops(a[ctor]) if not 30<=x[0]<35]+[(30,'goto_w 64'),(64,'invokestatic #422 // Method compat/WorkerExit.prepare:()V'),(67,'aload_0'),(68,'aload_1'),(69,'putfield #14 // Field system:Lcom/apple/xsr/som/RaidSystem;'),(72,'goto_w 35')]
 if ops(b[ctor])!=sorted(expected) or rows(b[ctor]) or metadata(a[ctor])!=metadata(b[ctor]):raise ValueError('Constructor readiness seam differs')
 windows=((63,69,623),(612,618,644),(509,514,660),(514,519,689))
 expected=[x for x in ops(a[run]) if not any(lo<=x[0]<hi for lo,hi,_ in windows)]
 expected += [(lo,'goto_w '+str(target)) for lo,hi,target in windows]+[(68,'nop'),(617,'nop')]+TAIL
 if ops(b[dispatch])!=sorted(expected):raise ValueError('Worker tracking/callback instructions differ')
 added=[(623,644,72,'any'),(623,644,525,'Class java/lang/InterruptedException'),(644,660,462,'Class sun/io/MalformedInputException'),(644,660,337,'Class java/io/IOException'),(644,660,462,'Class java/lang/Exception'),(644,660,525,'Class java/lang/InterruptedException'),(660,689,525,'Class java/lang/InterruptedException'),(689,709,525,'Class java/lang/InterruptedException')]
 if rows(b[dispatch])!=rows(a[run])+added or metadata(b[dispatch]).replace('  private void dispatchLoop();','  public void run();').replace('flags: ACC_PRIVATE','flags: ACC_PUBLIC')!=metadata(a[run]):raise ValueError('Worker handler/frame/rename differs')
 expected=[x for x in ops(a[connect]) if x[0] not in (409,586)]+[(409,'goto_w 754'),(586,'goto_w 769')]
 for start,resume in ((754,414),(769,591)):
  expected += [(start,'aload_0'),(start+1,'aconst_null'),(start+2,'putfield #412 // '+ACTIVE),(start+5,'invokestatic #432 // Method compat/WorkerExit.connectCallback:(Lcom/apple/xsr/net/CommunicationHandler;Lcom/apple/xsr/som/RaidSystem;Lcom/apple/xsr/net/Response;Ljava/lang/Object;)V'),(start+8,'nop'),(start+9,'nop'),(start+10,'goto_w '+str(resume))]
 if ops(b[connect])!=sorted(expected) or rows(b[connect])!=rows(a[connect]) or metadata(b[connect])!=metadata(a[connect]):raise ValueError('Connect callback-attempt guards differ')
 if ops(b[run])!=WRAPPER or rows(b[run])!=[(0,7,12,'any')] or metadata(b[run]).rstrip()!='  public void run();\n    descriptor: ()V\n    flags: ACC_PUBLIC\n    Code:\n      stack=7, locals=4, args_size=1\n      Exception table:\n         from    to  target type':raise ValueError('Worker wrapper stop/exit shape differs')
 for h in (field,started,dispatch):del b[h]
 for h in (ctor,run,connect):b[h]=a[h]
 if {k:v.rstrip() for k,v in b.items()}!={k:v.rstrip() for k,v in a.items()}:raise ValueError('Worker changed unrelated member')
 from check_security import assert_retry_unreachable
 assert_retry_unreachable(members(after)[dispatch],True,(68,246,617))
 return before


def normalize_manager_ownership(after):
 if 'SyncSender.claim:()Z' not in after:return after
 before=reference('sync-ownership-reference-manager');check(before,after,'manager');return before


def normalize_extensions(after):
 after=normalize_manager_ownership(normalize_worker(after))
 if "synchronized boolean claim();" in after:
  before=reference("sync-ownership-reference-sender");check(before,after,"sender");return before
 return after
