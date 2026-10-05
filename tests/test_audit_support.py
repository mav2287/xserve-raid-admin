import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_support import isolated_env, tree, verify_jdk

class IsolationTests(unittest.TestCase):
    def test_ambient_options_and_secrets_are_not_forwarded(self):
        with patch.dict(os.environ, {'JAVA_TOOL_OPTIONS': 'synthetic-secret', 'CLASSPATH': '/bad', '_JAVA_OPTIONS': 'bad', 'ANTHROPIC_API_KEY': 'synthetic-secret'}):
            result = isolated_env()
        self.assertEqual(set(result), {'PATH','LANG','LC_ALL','TZ'})
        self.assertNotIn('synthetic-secret', str(result))

    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'real').write_text('fixture'); (root/'link').symlink_to(root/'real')
            with self.assertRaisesRegex(ValueError,'Symlinks'): tree(root)

    def test_jdk_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'JDK differs'): verify_jdk(Path(tmp))

if __name__ == '__main__': unittest.main()
