import sys
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from class_patch import ClassFile, transform, assert_connect_failure_stop
from check_connect_stop import terminal_expected, expected
from check_security import independent_preservation
ROOT=Path(__file__).resolve().parents[1]
ENTRY='com/apple/xsr/net/CommunicationsManager.class'

class ConnectStopTests(unittest.TestCase):
    def test_stop_windows_and_tail_are_fully_locked(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:before=z.read(ENTRY)
        after=transform(ENTRY,before);cls=ClassFile(after);m=next(m for m in cls.methods if m['name']=='doConnect');_,b,e=next(a for a in m['attributes'] if a[0]=='Code')
        assert_connect_failure_stop(before,after)
        for offset in list(range(393,401))+list(range(578,583))+list(range(718,754)):
            changed=bytearray(after);changed[b+14+offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):assert_connect_failure_stop(before,bytes(changed))

    def test_metadata_and_every_other_method_are_locked_to_audit17(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:before=z.read(ENTRY)
        after=transform(ENTRY,before);cls=ClassFile(after)
        for m in cls.methods:
            for _,b,e in [a for a in m['attributes'] if a[0]=='Code']:
                for offset in (b+7,b+9,b+14,e-1):
                    changed=bytearray(after);changed[offset]^=1
                    with self.subTest(method=m['name'],offset=offset),self.assertRaises(ValueError):assert_connect_failure_stop(before,bytes(changed))

    def test_independent_javap_pins_stop_order_flag_timing_handlers_and_back_branches(self):
        original=(ROOT/'tests/fixtures/connect-stop-original.javap').read_text();candidate=(ROOT/'tests/fixtures/connect-stop-candidate.javap').read_text()
        def check(text):
            with patch('check_security.disassemble_entries',side_effect=[original,text]):independent_preservation(None,None,None,ENTRY,'run','()V')
        check(candidate)
        for old,new in (('goto_w        718','goto_w        740'),('398: nop','398: athrow'),('goto_w        740','goto_w        744'),('720: putfield      #13','720: putfield      #14'),('724: invokestatic','724: invokevirtual'),('goto_w        401','goto_w        409'),('goto_w        583','goto_w        588'),('stack=6, locals=16','stack=6, locals=17')):
            bad=candidate.replace(old,new);self.assertNotEqual(bad,candidate)
            with self.subTest(old=old),self.assertRaises(ValueError):check(bad)

    def test_terminal_and_legacy_vectors_are_distinct(self):
        for mode in ('single','dual'):
            self.assertNotEqual(terminal_expected(mode),expected(mode));self.assertIn('then_sent=0',terminal_expected(mode)[0]);self.assertIn('then_sent=1',expected(mode)[0])
        self.assertIn('retry_preserved=true',terminal_expected('single-null')[0])
        self.assertIn('commands=1',terminal_expected('nohost-throw')[0])
