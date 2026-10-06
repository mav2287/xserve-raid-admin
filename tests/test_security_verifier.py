import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_security import plain_constructor_code

class SecurityVerifierTests(unittest.TestCase):
    def test_constructor_rejects_any_extra_code_attribute(self):
        plain='    Code:\n      stack=3, locals=2, args_size=2\n         0: aload_0\n         1: return\n'
        plain_constructor_code(plain)
        plain_constructor_code(plain+'    Exceptions:\n      throws java.io.IOException\n')
        for extra in ('Exception table:', 'LocalVariableTypeTable:', 'RuntimeVisibleTypeAnnotations:', 'UnknownAttribute:'):
            with self.subTest(extra=extra),self.assertRaises(ValueError):plain_constructor_code(plain+'      '+extra+'\n')
