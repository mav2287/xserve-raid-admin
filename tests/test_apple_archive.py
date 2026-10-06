import gzip
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from inspect_apple_archive import approved_url, inspect


class AppleArchiveTests(unittest.TestCase):
    def archive(self, rows):
        out=io.BytesIO()
        with tarfile.open(fileobj=out,mode='w',format=tarfile.USTAR_FORMAT) as archive:
            for name,kind in rows:
                info=tarfile.TarInfo(name); info.type=kind
                if kind == tarfile.REGTYPE: info.size=3; archive.addfile(info,io.BytesIO(b'abc'))
                else: info.linkname='target'; archive.addfile(info)
        return gzip.compress(out.getvalue())

    def test_download_origins_are_exactly_https_apple(self):
        for url in ['https://apple.com/a','https://download.info.apple.com/a','https://apple.com:443/a']: approved_url(url)
        for url in ['http://apple.com/a','https://evilapple.com/a','https://apple.com.evil.net/a',
                    'https://apple.com:444/a','https://user@apple.com/a']:
            with self.assertRaises(ValueError): approved_url(url)

    def test_tar_paths_links_and_collisions_rejected(self):
        cases=[[('../escape.jar',tarfile.REGTYPE)],[('/escape.jar',tarfile.REGTYPE)],
               [('link.jar',tarfile.SYMTYPE)],[('link.jar',tarfile.LNKTYPE)],
               [('A.txt',tarfile.REGTYPE),('a.txt',tarfile.REGTYPE)]]
        for rows in cases:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError): inspect(self.archive(rows),Path(tmp))

    def test_identical_members_share_flat_hash_cache_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)
            entries,selected=inspect(self.archive([('a.jar',tarfile.REGTYPE),('b.jar',tarfile.REGTYPE)]),cache)
            self.assertEqual(len(entries),2); self.assertEqual(len(selected),2)
            self.assertEqual(len(list(cache.iterdir())),1)
            self.assertEqual(next(cache.iterdir()).read_bytes(),b'abc')
