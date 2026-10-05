import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import baseline
from diagnose import safe_event


class BaselineTests(unittest.TestCase):
    def test_reference_hash_guard(self):
        baseline.verify_original(baseline.ROOT / 'original/RAID_Admin_original.jar')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.jar'
            p.write_bytes(b'not the reference')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                baseline.verify_original(p)

    def test_deterministic_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.jar', Path(tmp) / 'b.jar'
            baseline.write_jar(a, {'z': b'z', 'a': b'a'})
            baseline.write_jar(b, {'a': b'a', 'z': b'z'})
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as z:
                self.assertEqual(z.namelist(), ['a', 'z'])

    def test_unsafe_archive_entry_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                baseline.write_jar(Path(tmp) / 'bad.jar', {'../escape': b'x'})

    def test_no_arbitrary_diagnostic_text(self):
        # Synthetic sentinel; failures never print the event payload.
        secret = 'synthetic-test-sentinel'
        for key in ['ACP-Password', 'acp-password', 'Authorization', 'saved_credentials', 'body', 'message', 'operation', 'error_code', 'result']:
            self.assertNotIn(secret, json.dumps(safe_event({key: secret})))
        self.assertEqual(safe_event({'operation': 'fixture', 'result': 'pass', 'body': secret}),
                         {'operation': 'fixture', 'result': 'pass'})
        self.assertEqual(safe_event({'operation': {'nested': secret}}), {})


if __name__ == '__main__':
    unittest.main()
