from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_security import assert_worker_failure_stop,assert_retry_unreachable

class WorkerStopGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper=(Path(__file__).parent/'fixtures/worker-stop-helper.javap').read_text()
        cls.run_text=(Path(__file__).parent/'fixtures/worker-stop-run.javap').read_text()
    def test_reviewed_helper_and_worker_cfg(self):
        assert_worker_failure_stop(self.helper)
        self.assertTrue(assert_retry_unreachable(self.run_text,True)['retry_region_unreachable'])
    def test_helper_stop_calls_cannot_be_bypassed(self):
        for before,after in (('Method shutdownRequired:','Method retireConnection:'),('1: invokestatic','1: invokevirtual'),('STOPS_OPERATION_FAILURES = true','STOPS_OPERATION_FAILURES = false'),('24: invokevirtual','24: invokestatic')):
            with self.subTest(before=before),self.assertRaises(ValueError):assert_worker_failure_stop(self.helper.replace(before,after))
    def test_required_stop_cannot_swallow_failure_or_preserve_cause(self):
        for before,after in (('40: athrow','40: return'),('51: athrow','51: return'),('23    27    30','0    27    30'),('Response session stop failed','DO_NOT_RENDER_UNTRUSTED_FAILURE')):
            with self.subTest(before=before),self.assertRaises(ValueError):assert_worker_failure_stop(self.helper.replace(before,after))
    def test_report_stop_cannot_be_covered_by_logging_handler(self):
        with self.assertRaises(ValueError):assert_worker_failure_stop(self.helper.replace('4     8    11','0     8    11'))
    def test_old_handler_or_tail_reentry_rejected(self):
        for before,after in (('462   Class sun/io/MalformedInputException','307   Class sun/io/MalformedInputException'),('573: goto_w        578','573: goto_w        344'),('590: goto_w        352','590: goto_w        489'),('583: ifeq          563','583: goto          563')):
            changed=self.run_text.replace(before,after);self.assertTrue(changed!=self.run_text)
            with self.subTest(before=before),self.assertRaises(ValueError):assert_retry_unreachable(changed,True)
    def test_operation_prefix_cleanup_call_cannot_be_skipped(self):
        with self.assertRaises(ValueError):assert_retry_unreachable(self.run_text.replace('583: ifeq          563','583: ifeq          352'),True)

    def test_prefix_retire_stop_cannot_be_swallowed(self):
        value=self.helper.replace('        8: return\n','        8: return\n    Exception table:\n       from    to  target type\n           0     4     8   Class java/lang/Throwable\n',1)
        self.assertTrue(value!=self.helper)
        with self.assertRaises(ValueError):assert_worker_failure_stop(value)
