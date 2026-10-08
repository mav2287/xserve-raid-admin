import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_array_info_fix import validate_output


class CompileOutputTests(unittest.TestCase):
    def test_exact_interpreted_marker(self):
        self.assertEqual(validate_output(b'PASS\n', b'PASS\n', '-Xint', False), [])
        with self.assertRaises(ValueError): validate_output(b'WARNING\nPASS\n', b'PASS\n', '-Xint', False)

    def test_requires_both_actual_compiled_methods(self):
        listener = b' 100 1 b 3 com.apple.xsr.SystemInfoPane$5::propertyChange (82 bytes)\n'
        helper = b' 101 2 b 3 compat.ArrayInfoSelection::setArrayIndex (15 bytes)\n'
        self.assertEqual(len(validate_output(listener + helper + b'PASS\n', b'PASS\n', '-Xcomp', True)), 2)
        with self.assertRaises(ValueError): validate_output(listener + b'PASS\n', b'PASS\n', '-Xcomp', True)
        with self.assertRaises(ValueError): validate_output(b'PASS\n', b'PASS\n', '-Xcomp', False)
        with self.assertRaises(ValueError): validate_output(listener.replace(b'bytes)', b'bytes) made not entrant') + b'PASS\n', b'PASS\n', '-Xcomp', False)

    def test_warnings_unexpected_compilation_and_extra_markers_rejected(self):
        listener = b' 100 1 b 3 com.apple.xsr.SystemInfoPane$5::propertyChange (82 bytes)\n'
        for extra in [b'CodeCache: disabled\n', b' 102 3 b 3 unexpected.Class::method (4 bytes)\n', b'PASS\n']:
            with self.assertRaises(ValueError): validate_output(listener + extra + b'PASS\n', b'PASS\n', '-Xcomp', False)
