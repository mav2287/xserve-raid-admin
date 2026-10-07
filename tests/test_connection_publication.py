"""Exact private publication override, immutable predecessor and independent structure."""
import hashlib,struct,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from class_patch import ClassFile,transform
from connection_publication_patch import ENTRY,PIN,plan,normalize
from connection_publication_structure import check_publication

class ConnectionPublicationTests(unittest.TestCase):
    def predecessor(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as z:return transform(ENTRY,z.read(ENTRY))
    def test_exact_roundtrip_preserves_predecessor(self):
        old=self.predecessor();self.assertEqual(hashlib.sha256(old).hexdigest(),PIN)
        new=plan(old);self.assertEqual(normalize(new),old)
        a,b=ClassFile(old),ClassFile(new)
        self.assertEqual((a.pool_count,len(a.fields),len(a.methods)),(301,13,12))
        self.assertEqual(old[10:a.pool_end],new[10:b.pool_end])
    def test_pool_code_and_member_mutations_are_refused(self):
        new=plan(self.predecessor());c=ClassFile(new);positions=set(range(10,c.pool_end))
        for m in c.methods:
            positions.add(m['start']+1)
            for kind,b,e in m['attributes']:
                if kind=='Code':positions.update(range(b+6,e))
        for f in c.fields:positions.add(f['start']+1)
        for offset in sorted(positions):
            altered=bytearray(new);altered[offset]^=1
            with self.subTest(offset=offset),self.assertRaises((ValueError,KeyError,UnicodeDecodeError,IndexError,struct.error)):
                normalize(bytes(altered))
    def test_independent_publication_and_frame_mutations(self):
        text=(ROOT/'tests/fixtures/connection-publication-candidate-acpx.javap').read_text();check_publication(text)
        for old,new in [('ifnonnull     39','ifnonnull     36'),('33: putfield      #14','33: putfield      #12'),
                        ('28: invokevirtual #69','28: invokevirtual #68'),('stack=3, locals=2, args_size=1','stack=4, locals=2, args_size=1')]:
            damaged=text.replace(old,new);self.assertNotEqual(text,damaged)
            with self.assertRaises(ValueError):check_publication(damaged)
