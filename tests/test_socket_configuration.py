"""Hash-locked socket override and independent argument/publication checks."""
import hashlib,struct,sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from class_patch import ClassFile,TARGETS,CURRENT_TARGETS,transform_current
from socket_configuration_patch import ENTRY,PIN,plan,normalize
from socket_configuration_structure import check_socket_setup

class SocketConfigurationTests(unittest.TestCase):
    def original(self):
        with zipfile.ZipFile(ROOT/'original/RAID_Admin_original.jar') as jar:return jar.read(ENTRY)
    def test_exact_roundtrip_and_current_only_extension(self):
        old=self.original();self.assertEqual(hashlib.sha256(old).hexdigest(),PIN)
        after=plan(old);self.assertEqual(normalize(after),old)
        self.assertEqual(transform_current(ENTRY,old),after)
        self.assertNotIn(ENTRY,TARGETS);self.assertIn(ENTRY,CURRENT_TARGETS)
    def test_every_pool_code_and_member_mutation_rejected(self):
        after=plan(self.original());cls=ClassFile(after);positions=set(range(10,cls.pool_end))
        for method in cls.methods:
            positions.add(method['start']+1)
            for kind,b,e in method['attributes']:
                if kind=='Code':positions.update(range(b+6,e))
        for field in cls.fields:positions.add(field['start']+1)
        for offset in sorted(positions):
            damaged=bytearray(after);damaged[offset]^=1
            with self.subTest(offset=offset),self.assertRaises((ValueError,KeyError,UnicodeDecodeError,IndexError,struct.error)):
                normalize(bytes(damaged))
    def test_independent_argument_publication_and_pool_mutations(self):
        text=(ROOT/'tests/fixtures/socket-configuration-candidate-http.javap').read_text();check_socket_setup(text)
        mutations=[('6: getfield      #9','6: getfield      #8'),
                   ('2: getfield      #13','2: getfield      #9'),
                   ('12: putfield      #26','12: putfield      #9'),
                   ('stack=3, locals=2, args_size=2','stack=4, locals=2, args_size=2'),
                   ('#199.#201','#199.#200')]
        for before,after in mutations:
            damaged=text.replace(before,after);self.assertNotEqual(damaged,text)
            with self.subTest(mutation=before),self.assertRaises(ValueError):check_socket_setup(damaged)
