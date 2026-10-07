import hashlib,struct,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from help_patch import TARGETS,plan,normalize
from class_patch import ClassFile
class HelpPatchTests(unittest.TestCase):
    def test_exact_round_trip_and_all_other_bytes_preserved(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:
            for entry, spec in TARGETS.items():
                original=z.read(entry); patched=plan(entry,original)
                self.assertEqual(normalize(entry,patched),original)
                a,b=ClassFile(original),ClassFile(patched)
                self.assertEqual(original[:8],patched[:8]);self.assertEqual(original[10:a.pool_end],patched[10:a.pool_end])
                self.assertEqual(a.class_attributes,b.class_attributes)
                self.assertEqual((len(a.fields),len(a.methods)),(len(b.fields),len(b.methods)))
    def test_every_byte_mutation_refused(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:
            for entry in TARGETS:
                patched=plan(entry,z.read(entry))
                for i in range(len(patched)):
                    damaged=bytearray(patched);damaged[i]^=1
                    with self.subTest(entry=entry,offset=i),self.assertRaises((ValueError,KeyError,IndexError,UnicodeDecodeError,struct.error)):
                        normalize(entry,bytes(damaged))
    def test_wrong_stage_and_cross_entry_refused(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:
            names=list(TARGETS)
            for entry in names:
                old=z.read(entry);new=plan(entry,old)
                with self.assertRaises(ValueError):plan(entry,new)
                with self.assertRaises((ValueError,KeyError,IndexError,struct.error)):normalize(entry,old)
                with self.assertRaises(ValueError):plan(entry,z.read(names[1] if entry==names[0] else names[0]))
    def test_independent_disassembly_comparison_refuses_other_changes(self):
        from help_structure import EXPECTED,check_operand
        for entry,(pc,old,new) in EXPECTED.items():
            before='    stack=1, locals=3, args_size=2\n       0: aload_0\n       '+str(pc)+': invokestatic #'+str(old)+' // Method edu/stanford/ejalbert/BrowserLauncher.openURL:(Ljava/lang/String;)V\n'
            after=before.replace('#'+str(old)+' // Method edu/stanford/ejalbert/BrowserLauncher','#'+str(new)+' // Method compat/HelpLauncher')
            check_operand(entry,before,after)
            for bad in (after.replace('aload_0','aload_1'),after.replace('stack=1','stack=2'),after.replace('invokestatic','invokevirtual')):
                with self.assertRaises(ValueError):check_operand(entry,before,bad)
    def test_comparator_refuses_incomplete_extension(self):
        from help_patch import strip_entries
        self.assertEqual(strip_entries({'fixture':b'unchanged'}),{'fixture':b'unchanged'})
        with self.assertRaises(ValueError):strip_entries({'compat/HelpLauncher.class':b'altered-helper'})
