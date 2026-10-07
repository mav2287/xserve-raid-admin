import hashlib,json,struct,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from preference_io_patch import ENTRY,ORIGINAL_SHA,PATCHED_SHA,plan,normalize
from preference_io_structure import check_disassembly,POOL,OLD,NEW
from class_patch import ClassFile
from sync_ownership_patch import method_code

class PreferenceIOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:cls.original=z.read(ENTRY)
        cls.patched=plan(cls.original)
    def test_exact_reverse_and_unchanged_load_constructors(self):
        self.assertEqual(hashlib.sha256(self.patched).hexdigest(),PATCHED_SHA)
        self.assertEqual(normalize(self.patched),self.original)
        a,b=ClassFile(self.original),ClassFile(self.patched)
        self.assertEqual((a.pool_count,b.pool_count,len(a.fields),len(a.methods)),(82,88,1,4))
        for method in a.methods:
            if method['name']=='store':continue
            matches=[m for m in b.methods if (m['name'],m['descriptor'])==(method['name'],method['descriptor'])]
            self.assertEqual(len(matches),1);m=matches[0]
            self.assertEqual(self.original[method['start']:method['end']],self.patched[m['start']:m['end']])
    def test_every_byte_mutation_refused(self):
        for offset in range(len(self.patched)):
            damaged=bytearray(self.patched);damaged[offset]^=1
            with self.subTest(offset=offset),self.assertRaises((ValueError,KeyError,IndexError,UnicodeDecodeError,struct.error)):
                normalize(bytes(damaged))
    def test_wrong_input_stage_and_partial_window_refused(self):
        with self.assertRaises(ValueError):plan(self.patched)
        with self.assertRaises(ValueError):normalize(self.original)
        c=ClassFile(self.patched);b,_=method_code(c,'store','()V')
        for offset,value in ((7,0),(15,0),(18,0x57),(46,0x57)):
            damaged=bytearray(self.patched);damaged[b+14+offset]=value
            with self.assertRaises(ValueError):normalize(bytes(damaged))
    def test_independent_complete_disassembly(self):
        before='major version: 47\nConstant pool:\n{\npublic void load();\n7: new #6\npublic void store();\nstack=7, locals=4, args_size=1\n'+ '\n'.join(OLD)+'\n47: goto 51\nException table:\n7 47 50 Class java/lang/Exception\n7 53 56 any\n56 59 56 any\n}\n'
        after=before.replace('Constant pool:\n','Constant pool:\n'+'\n'.join(POOL)+'\n').replace('\n'.join(OLD),'\n'.join(NEW))
        check_disassembly(before,after)
        for damaged in (after.replace('7: new #6','7: new #7'),after.replace('47: goto 51','47: goto 50'),after.replace('7 47 50','7 46 50'),after.replace('18: nop','18: pop'),after.replace('#87 = Methodref #83.#86','#87 = Methodref #83.#85')):
            with self.assertRaises(ValueError):check_disassembly(before,damaged)
        for old,new in ((before.replace('47: goto 51','47: goto 20'),after.replace('47: goto 51','47: goto 20')),(before.replace('47: goto 51','47: jsr 20'),after.replace('47: goto 51','47: jsr 20')),(before.replace('47: goto 51','51: aload_2'),after.replace('47: goto 51','51: aload_2')),(before.replace('major version: 47','major version: 50'),after.replace('major version: 47','major version: 50')),(before+'StackMapTable:\n',after+'StackMapTable:\n')):
            with self.assertRaises(ValueError):check_disassembly(old,new)
    def test_comparator_requires_exact_helper_and_backend_pair(self):
        from preference_io_patch import strip_entries
        self.assertEqual(strip_entries({ENTRY:self.original,'other':b'same'}),{ENTRY:self.original,'other':b'same'})
        with self.assertRaises(ValueError):strip_entries({ENTRY:self.patched})
        with self.assertRaises(ValueError):strip_entries({ENTRY:self.patched,'compat/PreferenceIO.class':b'altered'})
        with self.assertRaises(ValueError):strip_entries({ENTRY:self.original,'compat/PreferenceIO.class':b'altered'})

if __name__=='__main__':unittest.main()
