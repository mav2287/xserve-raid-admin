"""Independent javap proof of final volatile pre-send read; no class parser."""
import hashlib,re
from pathlib import Path
from sync_ownership_structure import members,ops,rows,metadata
ROOT=Path(__file__).resolve().parents[1]
PIN='72baf5afd5770a4068190df49b5d8eba73236e3d8f2a68bb5fe89371f9e3dbeb'
def normalize_stop_admission(after,required=False):
 p=ROOT/'tests/fixtures/guarded-worker-candidate-manager.javap'
 if hashlib.sha256(p.read_bytes()).hexdigest()!=PIN:raise ValueError('Stop reference changed')
 before=p.read_text();a,b=members(before),members(after);header='private void dispatchLoop();'
 if header not in b:
  if required:raise ValueError('Stop-admission dispatch missing')
  return after
 if (709,'aload_0') not in ops(b[header]):
  if required:raise ValueError('Stop-admission read missing')
  return after
 pool=lambda s:[(i,t,' '.join(v.split())) for i,t,v in re.findall(r'^\s+#(\d+) = (\S+)\s+(.*)$',s,re.M)]
 if pool(before)!=pool(after) or set(a)!=set(b):raise ValueError('Stop-admission pool/members differ')
 identity=lambda s:(re.findall(r'^(?:  (?:minor version|major version|flags):.*|public class .*)$',s,re.M),s.split('InnerClasses:',1)[1].strip())
 if identity(before)!=identity(after):raise ValueError('Stop-admission identity differs')
 expected=[x for x in ops(a[header]) if not 644<=x[0]<649]+[(644,'goto_w 709'),(709,'aload_0'),(710,'getfield #11 // Field stopped:Z'),(713,'ifne 280'),(716,'aload_0'),(717,'iconst_1'),(718,'putfield #414 // Field workerActiveStarted:Z'),(721,'goto_w 649')]
 added=[(709,726,462,'Class sun/io/MalformedInputException'),(709,726,337,'Class java/io/IOException'),(709,726,462,'Class java/lang/Exception'),(709,726,525,'Class java/lang/InterruptedException')]
 if ops(b[header])!=sorted(expected) or rows(b[header])!=rows(a[header])+added or metadata(b[header])!=metadata(a[header]):raise ValueError('Stop-admission decision, exposure or handlers differ')
 for name in a:
  if name!=header and a[name].rstrip()!=b[name].rstrip():raise ValueError('Stop-admission unrelated member differs')
 from check_security import assert_retry_unreachable
 assert_retry_unreachable(b[header],True,(68,246,617))
 return before
