from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_transport


class TransportHarnessTests(unittest.TestCase):
    def test_successful_exit_without_completion_is_rejected(self):
        for output in ('', 'response http-200 result=0\n',
                       'PASS memory-only transport and queue observations; real reconnection/backoff excluded\nextra\n'):
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                check_transport.completed(output)

    def test_completed_transcript_is_retained(self):
        lines = ['response http-200 result=0',
                 'PASS memory-only transport and queue observations; real reconnection/backoff excluded']
        self.assertEqual(check_transport.completed('\n'.join(lines) + '\n'), lines)

    def test_symlink_candidate_is_rejected_before_jdk_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'target.jar').write_bytes(b'fixture')
            (root / 'link.jar').symlink_to(root / 'target.jar')
            with patch.object(sys, 'argv', ['check_transport', '--jdk', temporary, str(root / 'link.jar')]), \
                 patch.object(check_transport, 'verify_jdk') as verify, \
                 self.assertRaises(ValueError):
                check_transport.main()
            verify.assert_not_called()
