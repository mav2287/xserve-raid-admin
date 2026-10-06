import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from check_shared_stream import completed, EXPECTED, FRAMING_EXPECTED


class SharedStreamEvidenceTests(unittest.TestCase):
    def test_framing_mode_requires_security_results_and_preserved_known_limit(self):
        self.assertEqual(completed('\n'.join(FRAMING_EXPECTED),True),FRAMING_EXPECTED)
        for lines in (EXPECTED,FRAMING_EXPECTED[:-2]+FRAMING_EXPECTED[-1:],FRAMING_EXPECTED+['uncontrolled sentinel']):
            with self.assertRaises(ValueError):completed('\n'.join(lines),True)
    def test_incomplete_or_changed_evidence_is_rejected_without_raw_output(self):
        self.assertEqual(completed('\n'.join(EXPECTED)+'\n'), EXPECTED)
        changed = list(EXPECTED)
        changed[2] = changed[2].replace('second=prior-body', 'second=second')
        counts = list(EXPECTED)
        counts[6] = counts[6].replace('pending_after_second=118', 'pending_after_second=0')
        for lines in (EXPECTED[:-1], EXPECTED+['uncontrolled sentinel'], changed, counts, list(reversed(EXPECTED))):
            with self.assertRaises(ValueError) as failure:
                completed('\n'.join(lines))
            self.assertNotIn('sentinel', str(failure.exception))
