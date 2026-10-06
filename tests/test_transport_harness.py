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

    def test_containment_requires_blocked_followup_vector(self):
        old=['null_io '+label+' terminal=-102; fixed-no-cause; failed_sends=1; next_distinct=0; worker-survives' for label in ('eof','cause','changing-first-null')]+['null_io changing-first-text ordinary-retry; getMessage_calls=1; sends=2','null_io sync fixed-IOException; no-peer-or-cause; sends=1','PASS null IO policy; guarded_operations=0']
        new=[line.replace('next_distinct=0; worker-survives','next_distinct=-102; session-stopped') for line in old]
        self.assertEqual(check_transport.completed_null_io('\n'.join(new),True),new)
        with self.assertRaises(ValueError):check_transport.completed_null_io('\n'.join(old),True)
        for mode in ('missing','ordinary-retry-changed','duplicate'):
            changed=list(new)
            if mode=='missing':changed.pop(0)
            elif mode=='ordinary-retry-changed':changed[3]=changed[3].replace('sends=2','sends=1')
            else:changed.insert(0,changed[0])
            with self.subTest(mode=mode),self.assertRaises(ValueError):check_transport.completed_null_io('\n'.join(changed),True)
