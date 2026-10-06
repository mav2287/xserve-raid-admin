import sys
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from class_patch import ClassFile, transform, assert_preserved, assert_sync_preenqueue
from check_sync_posting import expected,check_lines
from check_security import independent_preservation
ROOT=Path(__file__).resolve().parents[1]
ENTRY='com/apple/xsr/net/CommunicationsManager$SyncSender.class'

class SyncPostingTests(unittest.TestCase):
    def test_independent_disassembly_rejects_branch_padding_and_handler_changes(self):
        original=(ROOT/'tests/fixtures/sync-preenqueue-original.javap').read_text()
        candidate=(ROOT/'tests/fixtures/sync-preenqueue-candidate.javap').read_text()
        def check(text):
            with patch('check_security.disassemble_entries',side_effect=[original,text]):
                independent_preservation(None,None,None,ENTRY,'<init>','(Lcom/apple/xsr/net/CommunicationsManager;Lcom/apple/xsr/net/RequestMessage;)V')
        check(candidate)
        for old,new in (('goto          109','goto          129'),('17: nop','17: athrow'),('if_acmpne     129','if_acmpne     131'),('goto          20','goto          24'),('31    55    58','31    55    59'),('132: invokevirtual #4','132: invokevirtual #10'),('123: ldc           #8','123: ldc           #13'),('31: invokestatic  #5','31: invokestatic  #6')):
            bad=candidate.replace(old,new);self.assertNotEqual(bad,candidate)
            with self.assertRaises(ValueError):check(bad)

    def test_original_and_candidate_vectors_are_distinct_and_strict(self):
        for fixed in (False,True):
            lines=expected(fixed);check_lines(lines,fixed)
            for bad in (lines[:-1],lines+lines[:1],list(reversed(lines)),expected(not fixed)):
                with self.assertRaises(ValueError):check_lines(bad,fixed)

    def test_constructor_trampoline_and_dead_padding_are_fully_locked(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:before=z.read(ENTRY)
        after=transform(ENTRY,before);cls=ClassFile(after);m=next(m for m in cls.methods if m['name']=='<init>');_,b,e=next(a for a in m['attributes'] if a[0]=='Code')
        assert_sync_preenqueue(before,after)
        for offset in list(range(14,20))+list(range(109,138)):
            changed=bytearray(after);changed[b+14+offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):assert_sync_preenqueue(before,bytes(changed))

    def test_constructor_metadata_and_other_methods_are_locked(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:before=z.read(ENTRY)
        after=transform(ENTRY,before);cls=ClassFile(after);m=next(m for m in cls.methods if m['name']=='<init>');_,b,e=next(a for a in m['attributes'] if a[0]=='Code')
        for offset in (b+7,b+9,b+13,b+14+24,e-1,e-5):
            changed=bytearray(after);changed[offset]^=1
            with self.assertRaises(ValueError):assert_sync_preenqueue(before,bytes(changed))
        other=next(m for m in cls.methods if m['name']=='handleResponse');_,b,e=next(a for a in other['attributes'] if a[0]=='Code');changed=bytearray(after);changed[b+14]^=1
        with self.assertRaises(ValueError):assert_preserved(before,bytes(changed),'<init>','(Lcom/apple/xsr/net/CommunicationsManager;Lcom/apple/xsr/net/RequestMessage;)V')

    def test_shifted_original_hash_is_rejected(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:before=z.read(ENTRY)
        bad=bytearray(before);bad[-1]^=1
        with self.assertRaises(ValueError):transform(ENTRY,bytes(bad))
