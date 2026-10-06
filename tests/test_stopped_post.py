import hashlib
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from class_patch import ClassFile,transform,normalize_stopped_admission,AUDIT19_MANAGER_SHA256,post_code
from stopped_post_structure import normalize_admission
from check_security import independent_preservation
ROOT=Path(__file__).resolve().parents[1];ENTRY='com/apple/xsr/net/CommunicationsManager.class'

class StoppedPostTests(unittest.TestCase):
    def candidate(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:before=z.read(ENTRY)
        return before,transform(ENTRY,before)

    def test_exact_audit19_reconstruction(self):
        before,after=self.candidate();restored=normalize_stopped_admission(after)
        self.assertEqual(hashlib.sha256(restored).hexdigest(),AUDIT19_MANAGER_SHA256)
        self.assertEqual(ClassFile(after).pool_count,405)

    def test_each_code_and_pool_byte_is_locked(self):
        before,after=self.candidate();cls=ClassFile(after);b,e=post_code(cls);old=ClassFile(normalize_stopped_admission(after));extra_length=cls.pool_end-old.pool_end
        for pos in list(range(b,e))+list(range(cls.pool_end-extra_length,cls.pool_end)):
            changed=bytearray(after);changed[pos]^=1
            with self.subTest(offset=pos),self.assertRaises((ValueError,KeyError,UnicodeDecodeError)):
                normalize_stopped_admission(bytes(changed))

    def test_unrelated_method_byte_cannot_change(self):
        _,after=self.candidate();cls=ClassFile(after)
        for method in cls.methods:
            for _,b,e in [a for a in method['attributes'] if a[0]=='Code']:
                changed=bytearray(after);changed[b+14]^=1
                with self.subTest(method=method['name']),self.assertRaises(ValueError):normalize_stopped_admission(bytes(changed))

    def test_independent_javap_gate_and_negative_windows(self):
        before=(ROOT/'tests/fixtures/connect-stop-original.javap').read_text();after=(ROOT/'tests/fixtures/stopped-post-candidate.javap').read_text()
        normalize_admission(before,after,True)
        with patch('check_security.disassemble_entries',side_effect=[before,after]):independent_preservation(None,None,None,ENTRY,'run','()V')
        for old,new in [('80: pop2','80: pop'),('70: if_acmpne     80','70: if_acmpeq     80'),('56    84    47','56    98    47'),('84: aload_1','84: aload_2'),('57: getfield      #11','57: invokevirtual #27'),('91: instanceof    #30','91: instanceof    #23'),('java/lang/Thread.currentThread:()Ljava/lang/Thread;','java/lang/Thread.interrupted:()Z')]:
            bad=after.replace(old,new);self.assertNotEqual(bad,after)
            with self.subTest(old=old),self.assertRaises(ValueError):normalize_admission(before,bad,True)

    def test_required_gate_rejects_historical_no_admission(self):
        before=(ROOT/'tests/fixtures/connect-stop-original.javap').read_text()
        with self.assertRaises(ValueError):normalize_admission(before,before,True)

    def test_unexpected_stderr_is_rejected_without_exposure(self):
        from audit_support import run_jdk
        from types import SimpleNamespace
        result=SimpleNamespace(returncode=0,stdout=b'fixed fixture line',stderr=b'synthetic-sensitive-canary')
        with patch('audit_support.subprocess.run',return_value=result):
            with self.assertRaises(RuntimeError) as captured:run_jdk('/fixture','java',[],require_empty_stderr=True)
            self.assertNotIn('canary',str(captured.exception))
            self.assertEqual(run_jdk('/fixture','java',[]),'fixed fixture line')
