"""Exact ownership edits reconstruct the immutable audit.20 predecessor."""
import hashlib
import sys
import struct
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from class_patch import ClassFile,transform
from sync_ownership_structure import check
from sync_ownership_patch import (transform_manager,transform_sender,normalize_manager,
                                 normalize_sender,MANAGER_SHA,SENDER_SHA)
ROOT=Path(__file__).resolve().parents[1]

class SyncOwnershipTests(unittest.TestCase):
    def predecessors(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:
            return [(transform(n,z.read(n)),forward,reverse,pin) for n,forward,reverse,pin in (
                ('com/apple/xsr/net/CommunicationsManager.class',transform_manager,normalize_manager,MANAGER_SHA),
                ('com/apple/xsr/net/CommunicationsManager$SyncSender.class',transform_sender,normalize_sender,SENDER_SHA))]

    def test_exact_predecessors_and_round_trip(self):
        for before,forward,reverse,pin in self.predecessors():
            self.assertEqual(hashlib.sha256(before).hexdigest(),pin)
            self.assertEqual(reverse(forward(before)),before)

    def test_original_and_unreviewed_inputs_rejected(self):
        for before,forward,reverse,_ in self.predecessors():
            bad=bytearray(before);bad[-1]^=1
            with self.assertRaises(ValueError):forward(bytes(bad))
            with self.assertRaises(ValueError):reverse(bytes(bad))
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:
            with self.assertRaises(ValueError):transform_manager(z.read('com/apple/xsr/net/CommunicationsManager.class'))
            with self.assertRaises(ValueError):transform_sender(z.read('com/apple/xsr/net/CommunicationsManager$SyncSender.class'))

    def test_every_method_body_byte_is_locked(self):
        for before,forward,reverse,_ in self.predecessors():
            after=forward(before);cls=ClassFile(after)
            for method in cls.methods:
                for kind,b,e in method['attributes']:
                    if kind!='Code':continue
                    for offset in range(b+6,e):
                        bad=bytearray(after);bad[offset]^=1
                        with self.subTest(method=method['name'],offset=offset),self.assertRaises((ValueError,KeyError,UnicodeDecodeError,IndexError,struct.error)):
                            reverse(bytes(bad))

    def test_added_pool_and_member_flags_are_locked(self):
        for before,forward,reverse,_ in self.predecessors():
            after=forward(before);old=ClassFile(before);cls=ClassFile(after)
            for offset in list(range(old.pool_end,cls.pool_end))+[m['start']+1 for m in cls.methods]+[f['start']+1 for f in cls.fields]:
                bad=bytearray(after);bad[offset]^=1
                with self.subTest(offset=offset),self.assertRaises((ValueError,KeyError,UnicodeDecodeError,IndexError,struct.error)):
                    reverse(bytes(bad))

    def test_independent_javap_structure_and_negative_controls(self):
        for kind in ('manager','sender'):
            before=(ROOT/('tests/fixtures/sync-ownership-reference-'+kind+'.javap')).read_text()
            after=(ROOT/('tests/fixtures/sync-ownership-candidate-'+kind+'.javap')).read_text()
            check(before,after,kind)
            mutations=([('609: ifeq          489','609: ifne          489'),('618: goto_w        247','618: goto_w        255'),('595   623   337','595   622   337'),('623   462   Class sun/io/MalformedInputException','623   337   Class sun/io/MalformedInputException'),('616: astore        5','616: astore        6')] if kind=='manager' else [('151: ifne          24','151: ifeq          24'),('144: ifne          96','144: ifne          60'),('138   159   101','138   159    58'),('flags: ACC_SYNCHRONIZED','flags: ACC_PUBLIC'),('4: ifeq          8','4: ifne          8')])
            for old,new in mutations:
                bad=after.replace(old,new);self.assertNotEqual(bad,after)
                with self.subTest(kind=kind,mutation=old),self.assertRaises(ValueError):check(before,bad,kind)
