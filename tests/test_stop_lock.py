import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from class_patch import ClassFile,transform,assert_stop_lock_order,AUDIT18_MANAGER_SHA256,u2,word
from check_security import independent_preservation
from check_stop_lock import subclass_inventory,expected
ROOT=Path(__file__).resolve().parents[1];ENTRY='com/apple/xsr/net/CommunicationsManager.class'

class StopLockTests(unittest.TestCase):
    def original(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:return z.read(ENTRY)

    def test_exact_audit18_reconstruction_and_every_edit_byte(self):
        before=self.original();after=transform(ENTRY,before);restored=assert_stop_lock_order(before,after);self.assertEqual(hashlib.sha256(restored).hexdigest(),AUDIT18_MANAGER_SHA256)
        cls=ClassFile(after);f=next(f for f in cls.fields if f['name']=='stopped');_,b,e=next(a for m in cls.methods if m['name']=='run' for a in m['attributes'] if a[0]=='Code')
        positions=list(range(f['start'],f['start']+2))+[b+14+pc+i for pc in (18,45) for i in range(3)]
        for pos in positions:
            bad=bytearray(after);bad[pos]^=1
            with self.subTest(offset=pos),self.assertRaises(ValueError):assert_stop_lock_order(before,bytes(bad))

    def test_reference_pin_rejects_mutated_original(self):
        before=bytearray(self.original());after=transform(ENTRY,bytes(before));before[-1]^=1
        with self.assertRaises(ValueError):assert_stop_lock_order(bytes(before),after)

    def test_other_methods_frames_and_field_flags_cannot_change(self):
        before=self.original();after=transform(ENTRY,before);cls=ClassFile(after)
        for m in cls.methods:
            for _,b,e in [a for a in m['attributes'] if a[0]=='Code']:
                bad=bytearray(after);bad[b+14]^=1
                with self.subTest(method=m['name']),self.assertRaises(ValueError):assert_stop_lock_order(before,bytes(bad))
        for f in cls.fields:
            bad=bytearray(after);bad[f['start']+1]^=1
            with self.subTest(field=f['name']),self.assertRaises(ValueError):assert_stop_lock_order(before,bytes(bad))

    def test_javap_field_and_both_windows_are_independently_locked(self):
        original=(ROOT/'tests/fixtures/connect-stop-original.javap').read_text();candidate=(ROOT/'tests/fixtures/stop-lock-candidate.javap').read_text()
        def check(text):
            with patch('check_security.disassemble_entries',side_effect=[original,text]):independent_preservation(None,None,None,ENTRY,'run','()V')
        check(candidate)
        for old,new in (('private volatile boolean stopped','private boolean stopped'),('ACC_PRIVATE, ACC_VOLATILE','ACC_PUBLIC, ACC_VOLATILE'),('18: getfield      #11','18: getfield      #12'),('45: getfield      #11','45: invokevirtual #27')):
            bad=candidate.replace(old,new);self.assertNotEqual(bad,candidate)
            with self.subTest(old=old),self.assertRaises(ValueError):check(bad)

    def test_superclass_inventory_rejects_any_manager_subclass(self):
        self.assertEqual(subclass_inventory(ROOT/'original/RAID_Admin_original.jar')['class_count'],2844)
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:data=z.read('com/apple/xsr/net/CommunicationsManager$SyncSender.class')
        cls=ClassFile(data);owner=next(i for i,(tag,v) in cls.pool.items() if tag==7 and cls.text(u2(v,0))=='com/apple/xsr/net/CommunicationsManager');bad=bytearray(data);bad[cls.pool_end+4:cls.pool_end+6]=word(owner)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'subclass.jar'
            with zipfile.ZipFile(p,'w') as z:z.writestr('Synthetic.class',bad)
            with self.assertRaises(ValueError):subclass_inventory(p)

    def test_deadlock_and_safe_vectors_are_distinct(self):
        for mode in ('pc18','pc45'):
            self.assertNotEqual(expected(mode,False),expected(mode,True));self.assertIn('exact-deadlock-pair',expected(mode,True)[0]);self.assertIn('completed',expected(mode,False)[0])
