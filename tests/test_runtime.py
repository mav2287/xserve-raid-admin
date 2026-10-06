import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from runtime import extract_archive, verify_runtime
from audit_support import digest, tree, modes


class RuntimeTests(unittest.TestCase):
    def test_archive_rejects_escape_and_links(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('/escape', tarfile.REGTYPE),
                           ('jdk/link', tarfile.SYMTYPE), ('other/file', tarfile.REGTYPE),
                           ('jdk/pipe', tarfile.FIFOTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / 'archive.tar'
                with tarfile.open(archive, 'w') as out:
                    member = tarfile.TarInfo(name); member.type = kind; member.linkname = '../../escape'
                    out.addfile(member, io.BytesIO())
                with self.assertRaises(ValueError): extract_archive(archive, Path(tmp) / 'out', 'jdk')
                self.assertFalse((Path(tmp) / 'out').exists())

    def test_vendor_readonly_mode_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'archive.tar'
            with tarfile.open(archive, 'w') as out:
                member = tarfile.TarInfo('jdk/LICENSE'); member.mode = 0o444; member.size = 7
                out.addfile(member, io.BytesIO(b'fixture'))
            extract_archive(archive, Path(tmp) / 'out', 'jdk')
            self.assertEqual((Path(tmp) / 'out/jdk/LICENSE').stat().st_mode & 0o777, 0o444)

    def test_changed_runtime_or_executable_mode_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); java = root / 'java'; java.write_bytes(b'fixture'); java.chmod(0o755)
            record = {'files':tree(root),'file_modes':modes(root)}
            record['tree_sha256'] = digest(record)
            verify_runtime(root, record)
            java.chmod(0o644)
            with self.assertRaises(ValueError): verify_runtime(root, record)
            java.chmod(0o755); java.write_bytes(b'changed')
            with self.assertRaises(ValueError): verify_runtime(root, record)
