import hashlib
from pathlib import Path
import struct
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from array_info_patch import ENTRY, PIN, plan, normalize, verify_delta
from class_patch import ClassFile
from sync_ownership_patch import method_code


class ArrayInfoPatchTests(unittest.TestCase):
    def original(self):
        with zipfile.ZipFile(ROOT / 'original/RAID_Admin_original.jar') as archive:
            return archive.read(ENTRY)

    def test_exact_invocation_only_and_reversal(self):
        original = self.original(); patched = plan(original)
        self.assertEqual(hashlib.sha256(original).hexdigest(), PIN)
        self.assertEqual(normalize(patched), original)
        a, b = ClassFile(original), ClassFile(patched)
        self.assertEqual(original[10:a.pool_end], patched[10:a.pool_end])
        at = method_code(a, 'propertyChange', '(Ljava/beans/PropertyChangeEvent;)V')[0] + 14 + 30
        tail = bytearray(patched[b.pool_end:])
        tail[at-a.pool_end:at-a.pool_end+3] = original[at:at+3]
        self.assertEqual(bytes(tail), original[a.pool_end:])

    def test_all_byte_mutations_rejected(self):
        patched = plan(self.original())
        for at in range(len(patched)):
            damaged = bytearray(patched); damaged[at] ^= 1
            with self.subTest(at=at), self.assertRaises((ValueError, KeyError, IndexError, UnicodeDecodeError, struct.error)):
                normalize(bytes(damaged))

    def test_wrong_stage_refused(self):
        original = self.original()
        with self.assertRaises(ValueError): plan(plan(original))
        with self.assertRaises(ValueError): normalize(original)

    def test_other_entry_mutation_refused(self):
        original = self.original()
        # Structural helper bytes are enough for this dictionary-boundary control.
        helper = b'\xca\xfe\xba\xbe\x00\x00\x00\x34'
        before = {ENTRY: original, 'unchanged': b'reference'}
        after = {ENTRY: plan(original), 'unchanged': b'reference', 'compat/ArrayInfoSelection.class': helper}
        verify_delta(before, after, helper)
        for changed in ({**after, 'unchanged': b'changed'}, {**after, 'extra': b'added'}, {k:v for k,v in after.items() if k != 'unchanged'}):
            with self.assertRaises(ValueError): verify_delta(before, changed, helper)
        for changed in ({**after, 'compat/ArrayInfoSelection.class': b'wrong'},
                        {k:v for k,v in after.items() if k != 'compat/ArrayInfoSelection.class'},
                        {k:v for k,v in after.items() if k != ENTRY}):
            with self.assertRaises(ValueError): verify_delta(before, changed, helper)
        wrong_version = helper[:6] + b'\x00\x35'
        with self.assertRaises(ValueError): verify_delta(before, {**after, 'compat/ArrayInfoSelection.class': wrong_version}, wrong_version)
