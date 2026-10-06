"""Integrated stop guard: exact reversal and independent semantic controls."""
import sys,hashlib,zipfile,struct
from pathlib import Path
import unittest,tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from class_patch import ClassFile,transform
from sync_ownership_patch import transform_manager
from worker_exit_patch import plan as worker_plan
from stop_admission_patch import plan,normalize,PIN
from stop_admission_structure import normalize_stop_admission
from stop_admission_fixtures import hook,unhook
ENTRY='com/apple/xsr/net/CommunicationsManager.class'
class StopAdmissionTests(unittest.TestCase):
 def predecessor(self):
  with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:return worker_plan(transform_manager(transform(ENTRY,z.read(ENTRY))))
 def test_roundtrip_and_test_hook_boundaries(self):
  before=self.predecessor();self.assertEqual(hashlib.sha256(before).hexdigest(),PIN)
  after=plan(before);self.assertEqual(normalize(after),before)
  for data in (before,after):self.assertEqual(unhook(hook(data)),data)
  self.assertNotIn(b'StopAdmissionObservation',after)
 def test_all_code_bytes_and_pool_are_locked(self):
  after=plan(self.predecessor());cls=ClassFile(after)
  positions=set(range(10,cls.pool_end))
  for method in cls.methods:
   positions.add(method['start']+1)
   for kind,b,e in method['attributes']:
    if kind=='Code':positions.update(range(b+6,e))
  for f in cls.fields:positions.add(f['start']+1)
  for at in sorted(positions):
   data=bytearray(after);data[at]^=1
   with self.subTest(offset=at),self.assertRaises((ValueError,KeyError,UnicodeDecodeError,IndexError,struct.error)):normalize(bytes(data))
 def test_independent_semantic_mutants(self):
  after=(ROOT/'tests/fixtures/stop-admission-candidate-manager.javap').read_text();normalize_stop_admission(after,True)
  for old,new in [('713: ifne','713: ifeq'),('710: getfield      #11','710: getfield      #13'),('718: putfield      #414','718: putfield      #412'),('721: goto_w        649','721: goto_w        247')]:
   changed=after.replace(old,new);self.assertNotEqual(changed,after)
   with self.subTest(mutation=old),self.assertRaises(ValueError):normalize_stop_admission(changed,True)

 def test_fixture_archives_ignore_clock_and_input_order(self):
  import stop_admission_fixtures,stop_exposure_fixtures
  entries={ENTRY:b'old-manager','resource.txt':b'untouched-resource','folder/':b'','folder/é.txt':b'utf8-name'}
  for builder in (stop_admission_fixtures,stop_exposure_fixtures):
   with tempfile.TemporaryDirectory() as tmp:
    a,b=Path(tmp)/'a.jar',Path(tmp)/'b.jar'
    with patch('zipfile.time.localtime',return_value=(2001,2,3,4,5,6,0,0,0)):
     builder.write_fixture(a,entries,b'new-manager')
    with patch('zipfile.time.localtime',return_value=(2031,5,6,7,8,9,0,0,0)):
     builder.write_fixture(b,dict(reversed(list(entries.items()))),b'new-manager')
    self.assertEqual(a.read_bytes(),b.read_bytes())
    self.assertEqual(hashlib.sha256(a.read_bytes()).hexdigest(),'bad6276dc8d9f5cfbb5e0067b01b920d681582337966d4ff41ab35e699022869')
    with zipfile.ZipFile(a) as z:
     self.assertEqual(z.read(ENTRY),b'new-manager')
     self.assertEqual(z.read('resource.txt'),entries['resource.txt'])
     self.assertEqual(set(z.namelist()),set(entries))
     self.assertTrue(all(i.date_time==(1980,1,1,0,0,0) and i.create_system==3 for i in z.infolist()))
     self.assertEqual(z.getinfo('folder/').external_attr,(0o40755<<16)|0x10)
     self.assertEqual(z.getinfo('resource.txt').external_attr,0o100644<<16)
     self.assertEqual(z.read('folder/é.txt'),b'utf8-name')
