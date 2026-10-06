import hashlib
import json
from pathlib import Path
import sys
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from class_patch import TARGETS, ClassFile, transform, assert_preserved, embedded_dtd, assert_allocation_operands, assert_header_insertion, assert_recovery_edit
from audit_support import ROOT


class ClassPatchTests(unittest.TestCase):
    def test_golden_outputs_preserve_every_non_target_method(self):
        golden = json.loads((ROOT/'audit/security-patches.json').read_text())
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as archive:
            for entry, (_,name,descriptor) in TARGETS.items():
                with self.subTest(entry=entry):
                    before = archive.read(entry); after = transform(entry,before)
                    self.assertEqual(hashlib.sha256(after).hexdigest(),golden[entry]['patched_sha256'])
                    self.assertEqual(after,transform(entry,before))
                    assert_preserved(before,after,name,descriptor)
                    original, candidate = ClassFile(before), ClassFile(after)
                    self.assertEqual(before[:8],after[:8])
                    self.assertEqual(before[10:original.pool_end],after[10:original.pool_end])
                    self.assertGreater(candidate.pool_count,original.pool_count)
                    changed = bytearray(before); changed[-1] ^= 1
                    with self.assertRaises(ValueError): transform(entry,bytes(changed))
                    with self.assertRaises(ValueError): transform(entry,after)
                    for method in candidate.methods:
                        if method['name'] != name:
                            mutated = bytearray(after); mutated[method['end']-1] ^= 1
                            with self.assertRaises(ValueError): assert_preserved(before,bytes(mutated),name,descriptor)
                            break

    def test_allocation_code_preserves_handlers_frames_and_subattributes(self):
        entry='com/apple/xsr/net/HttpResponse.class'
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as archive: before=archive.read(entry)
        after=transform(entry,before)
        assert_allocation_operands(before,after)
        cls=ClassFile(after)
        method=next(m for m in cls.methods if m['name']=='getBody')
        _,begin,end=next(a for a in method['attributes'] if a[0]=='Code')
        for offset in (begin+14+15,begin+14+24,begin+14+29):
            changed=bytearray(after);changed[offset:offset+2]=b'\x00\x17'
            with self.subTest(operand=offset),self.assertRaises(ValueError):assert_allocation_operands(before,bytes(changed))
        for offset in (begin+7,begin+14+40,end-1):
            changed=bytearray(after);changed[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):assert_allocation_operands(before,bytes(changed))

    def test_header_insertion_preserves_original_constructor_and_rejects_changes(self):
        entry='com/apple/xsr/net/HttpResponse.class'
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as archive:before=archive.read(entry)
        after=transform(entry,before);assert_header_insertion(before,after)
        cls=ClassFile(after);method=next(m for m in cls.methods if m['name']=='<init>')
        _,begin,end=next(a for a in method['attributes'] if a[0]=='Code')
        for offset in (begin+6,begin+14+20,begin+14+36,begin+14+37,begin+14+38,begin+14+44,end-1):
            changed=bytearray(after);changed[offset]^=1
            with self.subTest(offset=offset),self.assertRaises((ValueError,KeyError)):assert_header_insertion(before,bytes(changed))

        changed=bytearray(after);changed[begin+14+37:begin+14+39]=b'\x00\x0e'
        with self.assertRaises(ValueError):assert_header_insertion(before,bytes(changed))
        for value in (b'compat/BoundedHeaderStream',b'wrap',b'(Ljava/io/InputStream;)Ljava/io/InputStream;'):
            offset=after.rfind(value);self.assertGreaterEqual(offset,0)
            changed=bytearray(after);changed[offset]^=1
            with self.subTest(target=value),self.assertRaises(ValueError):assert_header_insertion(before,bytes(changed))

    def test_recovery_run_only_changes_report_window(self):
        entry='com/apple/xsr/net/CommunicationsManager.class'
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as archive:before=archive.read(entry)
        after=transform(entry,before);assert_recovery_edit(before,after,'run')
        cls=ClassFile(after);m=next(m for m in cls.methods if m['name']=='run');_,begin,end=next(a for a in m['attributes'] if a[0]=='Code')
        for offset in (begin+6,begin+14+200,begin+14+464,begin+14+467,begin+14+473,end-1):
            changed=bytearray(after);changed[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):assert_recovery_edit(before,bytes(changed),'run')
        changed=bytearray(after);changed[begin+14+468:begin+14+470]=b'\x00\x46'
        with self.assertRaises(ValueError):assert_recovery_edit(before,bytes(changed),'run')

    def test_send_preserves_code_handlers_and_exact_marker_range(self):
        entry='com/apple/xsr/net/AcpxConnection.class'
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as archive:before=archive.read(entry)
        after=transform(entry,before);assert_recovery_edit(before,after,'send')
        cls=ClassFile(after);m=next(m for m in cls.methods if m['name']=='send');_,begin,end=next(a for a in m['attributes'] if a[0]=='Code')
        for offset in (begin+6,begin+14+200,begin+14+392,begin+14+396,begin+411,begin+413,begin+421,begin+425,end-1):
            changed=bytearray(after);changed[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):assert_recovery_edit(before,bytes(changed),'send')
        changed=bytearray(after);changed[begin+14+394:begin+14+396]=b'\x00\x40'
        with self.assertRaises(ValueError):assert_recovery_edit(before,bytes(changed),'send')

    def test_dtd_is_exact_embedded_literal_with_no_external_declarations(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as archive:
            dtd = embedded_dtd(archive.read('com/apple/util/plist/PropertyListUtilities$Handler.class'))
        expected = json.loads((ROOT/'audit/security-patches.json').read_text())['compat/PropertyList.dtd']
        self.assertEqual(hashlib.sha256(dtd).hexdigest(),expected['sha256'])
        self.assertNotIn(b'SYSTEM',dtd); self.assertNotIn(b'PUBLIC',dtd)
