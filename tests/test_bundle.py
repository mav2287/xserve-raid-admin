from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_support import tree, modes
from bundle import copy_verified


class BundleTests(unittest.TestCase):
    def test_modified_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'source'; src.mkdir(); file = src / 'fixture'; file.write_bytes(b'original')
            files, permissions = tree(src), modes(src)
            file.write_bytes(b'changed')
            with self.assertRaises(ValueError): copy_verified(src, Path(tmp) / 'out', files, permissions)
            self.assertFalse((Path(tmp) / 'out').exists())

    def test_verified_copy_preserves_bytes_modes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'source'; src.mkdir(); file = src / 'fixture'; file.write_bytes(b'original'); file.chmod(0o755)
            dst = Path(tmp) / 'out'; copy_verified(src, dst, tree(src), modes(src))
            self.assertEqual(tree(src), tree(dst)); self.assertEqual(modes(src), modes(dst))
            with self.assertRaises(FileExistsError): copy_verified(src, dst, tree(src), modes(src))
