from pathlib import Path
import sys
import json
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_security import assert_session_containment
from check_architectures import validate_containment_recovery

class HistoricalAudit14SessionStopGateTests(unittest.TestCase):
    def setUp(self):
        self.text=(Path(__file__).parent/'fixtures/session-stop-prefix.javap').read_text()

    def test_reviewed_report_prefix(self):
        assert_session_containment(self.text)

    def test_missing_or_bypassed_stop_is_rejected(self):
        for before,after in (('shutdown:()V','isStopped:()Z'),('if_acmpeq     18','if_acmpeq     22'),('19: invokevirtual','19: invokestatic'),('18: aload_0','18: nop')):
            with self.subTest(before=before),self.assertRaises(ValueError):assert_session_containment(self.text.replace(before,after))

    def test_wrong_marker_or_ordinary_path_change_is_rejected(self):
        for before,after in (('ConstantValue: int 1','ConstantValue: int 0'),('class compat/UntrustedResponseException','class java/lang/Exception'),('1: ifnull        13','1: ifnull        18'),('17: return','17: nop')):
            with self.subTest(before=before),self.assertRaises(ValueError):assert_session_containment(self.text.replace(before,after))

    def test_shutdown_cannot_be_swallowed_by_exception_handler(self):
        value=self.text.replace('}\n','    Exception table:\n       from    to  target type\n          18    26    29   Class java/lang/Exception\n}\n')
        with self.assertRaises(ValueError):assert_session_containment(value)

    def test_reviewed_recovery_matrix_matches(self):
        lines=json.loads((Path(__file__).resolve().parents[1]/'audit/session-containment-recovery-expected.json').read_text())['lines']
        validate_containment_recovery(lines,lines)

    def test_recovery_missing_duplicate_reordered_or_changed_line_fails(self):
        lines=json.loads((Path(__file__).resolve().parents[1]/'audit/session-containment-recovery-expected.json').read_text())['lines']
        for mode in ('missing','duplicate','reordered','resumed'):
            value=list(lines)
            if mode=='missing':value.pop(1)
            elif mode=='duplicate':value[2]=value[1]
            elif mode=='reordered':value[1],value[2]=value[2],value[1]
            else:
                index=next(i for i,line in enumerate(value) if line.startswith('recovery ') and 'stop=true' in line)
                value[index]=value[index].replace('stop=true','stop=false')
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_containment_recovery(value,lines)
