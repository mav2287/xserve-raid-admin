"""Exact worker transformation and independent semantic negative controls."""
import hashlib
from pathlib import Path
import struct
import sys
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from class_patch import ClassFile,transform,transform_current,normalize_current_extensions
from sync_ownership_patch import transform_manager
from worker_exit_patch import plan,normalize,PIN
from worker_exit_structure import normalize_worker,normalize_extensions
ROOT=Path(__file__).resolve().parents[1]
ENTRY='com/apple/xsr/net/CommunicationsManager.class'

class WorkerExitTests(unittest.TestCase):
 def predecessor(self):
  with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:return transform_manager(transform(ENTRY,z.read(ENTRY)))
 def test_exact_pipeline_and_round_trip(self):
  before=self.predecessor();self.assertEqual(hashlib.sha256(before).hexdigest(),PIN)
  after=plan(before);self.assertEqual(normalize(after),before)
  with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:
   self.assertEqual(transform_current(ENTRY,z.read(ENTRY)),after)
   self.assertEqual(normalize_current_extensions(after),transform(ENTRY,z.read(ENTRY)))
 def test_every_code_byte_is_locked(self):
  after=plan(self.predecessor())
  for method in ClassFile(after).methods:
   for kind,b,e in method['attributes']:
    if kind!='Code':continue
    for offset in range(b+6,e):
     changed=bytearray(after);changed[offset]^=1
     with self.subTest(method=method['name'],offset=offset),self.assertRaises((ValueError,KeyError,UnicodeDecodeError,IndexError,struct.error)):
      normalize(bytes(changed))
 def test_pool_fields_and_method_flags_are_locked(self):
  before=self.predecessor();after=plan(before);old,cls=ClassFile(before),ClassFile(after)
  for offset in list(range(old.pool_end,cls.pool_end))+[m['start']+1 for m in cls.methods]+[f['start']+1 for f in cls.fields]:
   changed=bytearray(after);changed[offset]^=1
   with self.subTest(offset=offset),self.assertRaises((ValueError,KeyError,UnicodeDecodeError,IndexError,struct.error)):normalize(bytes(changed))
 def test_independent_javap_controls(self):
  after=(ROOT/'tests/fixtures/guarded-worker-candidate-manager.javap').read_text();normalize_worker(after,True);normalize_extensions(after)
  for old,new in [('15: putfield      #11','15: putfield      #12'),('664: ifnull        682','664: ifnonnull     682'),('672: invokeinterface #78,  4','672: invokeinterface #78,  3'),('646: putfield      #414','646: putfield      #412'),('0: invokestatic  #425','0: invokestatic  #422'),('623   644    72','623   644   525'),('682: pop2','682: pop'),('72: goto_w        35','72: goto_w        36')]:
   changed=after.replace(old,new);self.assertNotEqual(changed,after,old)
   with self.subTest(mutation=old),self.assertRaises(ValueError):normalize_worker(changed,True)
