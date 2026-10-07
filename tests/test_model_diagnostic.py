import hashlib,struct,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from model_diagnostic_patch import ENTRY,ORIGINAL_SHA,PATCHED_SHA,plan,normalize,strip_entries
from class_patch import ClassFile,word
from sync_ownership_patch import method_code

class ModelDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:cls.original=z.read(ENTRY)
        cls.patched=plan(cls.original)
    def test_exact_round_trip_and_shape(self):
        self.assertEqual(hashlib.sha256(self.original).hexdigest(),ORIGINAL_SHA)
        self.assertEqual(hashlib.sha256(self.patched).hexdigest(),PATCHED_SHA)
        self.assertEqual(normalize(self.patched),self.original)
        a,b=ClassFile(self.original),ClassFile(self.patched)
        self.assertEqual((len(a.fields),len(a.methods),a.class_attributes),(109,139,b.class_attributes))
        self.assertEqual((len(a.fields),len(a.methods)),(len(b.fields),len(b.methods)))
        self.assertEqual(self.original[:8],self.patched[:8]);self.assertEqual(self.original[10:a.pool_end],self.patched[10:a.pool_end])
    def test_every_byte_mutation_is_refused(self):
        for i in range(len(self.patched)):
            damaged=bytearray(self.patched);damaged[i]^=1
            with self.subTest(offset=i),self.assertRaises((ValueError,KeyError,IndexError,UnicodeDecodeError,struct.error)):
                normalize(bytes(damaged))
    def test_partial_and_wrong_windows_are_refused(self):
        c=ClassFile(self.patched);b,_=method_code(c,'paramString','()Ljava/lang/String;')
        for pc,window in ((156,bytes.fromhex('2ab4004a')),(190,bytes.fromhex('2ab4004b')),(156,b'\x13'+word(1184)+b'\x00'),(156,b'\x00\x13'+word(1185))):
            bad=bytearray(self.patched);bad[b+14+pc:b+18+pc]=window
            with self.assertRaises(ValueError):normalize(bytes(bad))
        bad=bytearray(self.patched);bad[8:10]=word(1184)
        with self.assertRaises((ValueError,KeyError,IndexError,struct.error)):normalize(bytes(bad))
    def test_wrong_stage_input_and_comparator_fail_closed(self):
        with self.assertRaises(ValueError):plan(self.patched)
        with self.assertRaises(ValueError):plan(self.original[:-1]+b'\x01')
        with self.assertRaises(ValueError):normalize(self.original)
        for data in (self.original,self.patched):self.assertEqual(strip_entries({ENTRY:data,'other':b'unchanged'}),{ENTRY:self.original,'other':b'unchanged'})
        with self.assertRaises(ValueError):strip_entries({ENTRY:self.patched[:-1]+b'\x01'})
    def test_independent_checker_refuses_other_instruction_or_metadata_changes(self):
        from model_diagnostic_structure import check_disassembly
        old='Classfile original\n  Last modified ignored\n  MD5 checksum ignored\nConstant pool:\n  #76 = Fieldref same\n{\n    stack=3, locals=10, args_size=1\n       156: aload_0\n       157: getfield #74 // Field monitoringPassword:Ljava/lang/String;\n       190: aload_0\n       191: getfield #75 // Field managementPassword:Ljava/lang/String;\n       200: getfield #76 // Field managementPasswordSaved:Z\n       999: areturn\n}\n'
        new=old.replace('#76 = Fieldref same\n','#76 = Fieldref same\n  #1184 = Utf8 <redacted>\n  #1185 = String #1184 // <redacted>\n').replace('156: aload_0\n       157: getfield #74 // Field monitoringPassword:Ljava/lang/String;','156: ldc_w #1185 // String <redacted>\n       159: nop').replace('190: aload_0\n       191: getfield #75 // Field managementPassword:Ljava/lang/String;','190: ldc_w #1185 // String <redacted>\n       193: nop')
        check_disassembly(old,new)
        for bad in (new.replace('locals=10','locals=11'),new.replace('999: areturn','999: athrow'),new.replace('200: getfield #76','200: putfield #76'),new.replace('159: nop','159: pop')):
            with self.assertRaises(ValueError):check_disassembly(old,bad)

if __name__=='__main__':unittest.main()
