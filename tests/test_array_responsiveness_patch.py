import struct
import sys
import unittest
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from array_responsiveness_patch import SPECS,HELPERS,plan,normalize,verify_delta
from class_patch import ClassFile
from sync_ownership_patch import method_code

class ResponsivenessPatchTests(unittest.TestCase):
    def originals(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:
            return {entry:z.read(entry) for entry in SPECS}

    def test_exact_three_invocations_and_full_reversal(self):
        for entry,original in self.originals().items():
            patched=plan(entry,original);a,b=ClassFile(original),ClassFile(patched)
            self.assertEqual(normalize(entry,patched),original)
            self.assertEqual(original[10:a.pool_end],patched[10:a.pool_end])
            tail=bytearray(patched[b.pool_end:]);spec=SPECS[entry]
            start,_=method_code(a,spec[2],spec[3])
            for pc,_ in spec[4]:
                at=start+14+pc;tail[at-a.pool_end:at-a.pool_end+3]=original[at:at+3]
            self.assertEqual(bytes(tail),original[a.pool_end:])

    def test_every_byte_tamper_rejected(self):
        for entry,original in self.originals().items():
            patched=plan(entry,original)
            for at in range(len(patched)):
                bad=bytearray(patched);bad[at]^=1
                with self.subTest(entry=entry,at=at),self.assertRaises((ValueError,KeyError,IndexError,UnicodeDecodeError,struct.error)):
                    normalize(entry,bytes(bad))

    def test_wrong_stage_rejected(self):
        for entry,original in self.originals().items():
            with self.assertRaises(ValueError):plan(entry,plan(entry,original))
            with self.assertRaises(ValueError):normalize(entry,original)

    def test_inventory_and_other_bytes_locked(self):
        before={**self.originals(),'unchanged':b'reference'}
        helper=next(iter(HELPERS));helpers={helper:b'\xca\xfe\xba\xbe\x00\x00\x00\x34'}
        after={**before,**{entry:plan(entry,before[entry]) for entry in SPECS},**helpers}
        verify_delta(before,after,helpers)
        for bad in [{**after,'unchanged':b'changed'},{**after,'extra':b'extra'},{k:v for k,v in after.items() if k!=helper}]:
            with self.assertRaises(ValueError):verify_delta(before,bad,helpers)
        with self.assertRaises(ValueError):verify_delta(before,{**after,helper:b'wrong'},helpers)
