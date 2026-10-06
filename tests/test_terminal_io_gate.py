import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_security import assert_retry_unreachable
from check_transport import common_observations,completed_io,completed_null_io

class TerminalIoGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=(Path(__file__).parent/'fixtures/terminal-io-run.javap').read_text()
    def test_locked_cfg_preserves_prefix_and_excludes_retry(self):
        self.assertTrue(assert_retry_unreachable(self.source)['retry_region_unreachable'])
    def test_wrong_branch_destinations_rejected(self):
        for target in (380,464,562,564,578,352):
            with self.subTest(target=target),self.assertRaises(ValueError):assert_retry_unreachable(self.source.replace('ifeq          563','ifeq          '+str(target)))
    def test_handler_cannot_reenter_retry_region(self):
        source=self.source.replace('   337   Class java/io/IOException','   380   Class java/io/IOException')
        self.assertTrue(source!=self.source)
        with self.assertRaises(ValueError):assert_retry_unreachable(source)
    def test_retry_region_cannot_be_reentered_by_another_branch(self):
        with self.assertRaises(ValueError):assert_retry_unreachable(self.source.replace('goto          459','goto          380'))
    def test_prefix_path_cannot_be_lost(self):
        with self.assertRaises(ValueError):assert_retry_unreachable(self.source.replace('349: ifeq          563','349: goto          563'))
    def test_normal_connection_and_exit_paths_must_remain_reachable(self):
        for old,new in (('226: ifne          234','226: goto          234'),('538: ifnull        548','538: goto          548'),('349: ifeq          563','349: ifeq          563\n     351: goto          563')):
            changed=self.source.replace(old,new)
            self.assertTrue(changed!=self.source)
            with self.subTest(old=old),self.assertRaises(ValueError):assert_retry_unreachable(changed)
    def test_policy_vector_requires_full_evidence(self):
        lines=['dispatch drops=1 malformed=false sends=1 terminal_callbacks=1']*2+['dispatch drops=4 malformed=false sends=1 terminal_callbacks=1','queue_response truncated-terminal result=-102 sends=1 terminal_callbacks=1','queue_order first-only; connections 1; callbacks first-second; blocked-followup=true; reconnects=0','follow_on invalid-length results=-102,-102; sends=1; outstanding=true; reconnects=0']
        self.assertEqual(len(common_observations(lines,require_terminal_io_policy=True)),5)
        for bad in (lines[1:],lines+lines[:1],lines+['dispatch drops=1 malformed=false sends=2 terminal_callbacks=1']):
            with self.assertRaises(ValueError):common_observations(bad,require_terminal_io_policy=True)

class OperationFailureGateTests(unittest.TestCase):
    def test_characterization_requires_exact_failure_sequence(self):
        from check_transport import completed_operation_failures
        for stop in (False,True):
            lines=['operation_failure '+label+' first='+str(-103 if label=='prefix' else -102)+' exception_identity=true stop_before_callback='+str(stop).lower()+' attempts='+str((0 if label=='before-request-creation' else 1)+(0 if stop else 1))+' response_entries='+str((0 if label=='before-request-creation' else 1)+(0 if stop else 1))+' queued_restart='+('blocked' if stop else 'sent') for label in ('prefix','shim','generic','before-request-creation')]+['PASS operation failure characterization; guarded_operations=0']
            self.assertEqual(completed_operation_failures('\n'.join(lines),stop),lines)
            for bad in (lines[1:],lines+lines[:1],lines[:-1],['DO_NOT_RENDER_PEER']+lines):
                with self.assertRaises(ValueError) as caught:completed_operation_failures('\n'.join(bad),stop)
                self.assertNotIn('DO_NOT_RENDER',str(caught.exception))
            with self.assertRaises(ValueError):completed_operation_failures('\n'.join(lines),not stop)

    def test_literal_original_characterization_golden(self):
        from check_transport import completed_operation_failures
        lines=[
            'operation_failure prefix first=-103 exception_identity=true stop_before_callback=false attempts=2 response_entries=2 queued_restart=sent',
            'operation_failure shim first=-102 exception_identity=true stop_before_callback=false attempts=2 response_entries=2 queued_restart=sent',
            'operation_failure generic first=-102 exception_identity=true stop_before_callback=false attempts=2 response_entries=2 queued_restart=sent',
            'operation_failure before-request-creation first=-102 exception_identity=true stop_before_callback=false attempts=1 response_entries=1 queued_restart=sent',
            'PASS operation failure characterization; guarded_operations=0']
        self.assertEqual(completed_operation_failures('\n'.join(lines),False),lines)
