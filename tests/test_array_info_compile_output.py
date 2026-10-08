import sys
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_array_info_fix import check_compilation, COMPILED_TARGETS


class CompileOutputTests(unittest.TestCase):
    def log(self, directory, methods, failure=False):
        root = ET.Element('hotspot_log')
        for i, name in enumerate(methods):
            ET.SubElement(root, 'nmethod', method=name, compile_id=str(i), level='3')
        if failure:
            task = ET.SubElement(root, 'task', method=COMPILED_TARGETS[0]); ET.SubElement(task, 'failure', reason='fixture-control')
        path = Path(directory) / 'jit.xml'; ET.ElementTree(root).write(path); return path

    def test_requires_exact_method_and_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            result = check_compilation(self.log(directory, COMPILED_TARGETS), True)
            self.assertEqual(set(result['installed_nmethods']), set(COMPILED_TARGETS))
            with self.assertRaises(ValueError): check_compilation(self.log(directory, [COMPILED_TARGETS[0].replace(';)V', ';)I')]), False)

    def test_missing_helper_failed_compilation_and_empty_log_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for methods, failed in [(COMPILED_TARGETS[:1], False), (COMPILED_TARGETS, True), ([], False)]:
                with self.assertRaises(ValueError): check_compilation(self.log(directory, methods, failed), True)

    def test_original_requires_listener_and_forbids_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            check_compilation(self.log(directory, COMPILED_TARGETS[:1]), False)
            with self.assertRaises(ValueError): check_compilation(self.log(directory, COMPILED_TARGETS), False)
