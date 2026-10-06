import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_transport import common_observations

class TransportComparisonTests(unittest.TestCase):
    def test_only_explicit_length_policy_differences_are_allowed(self):
        legacy=['normal','follow_on invalid-length results=-102,-102; sends=1; outstanding=true; reconnects=0','PASS']
        security=['normal']+['security_length '+label+' fixed-marker; closed; no-input-or-cause' for label in ('invalid-length','negative-length','overflow-length')]+['security_length follow-on qualified by recovery fixture','PASS']
        self.assertEqual(common_observations(legacy),common_observations(security))
        for bad in (security[:-2]+['PASS'],security+['security_length invented'],['normal','PASS']):
            with self.assertRaises(ValueError):common_observations(bad)
        self.assertNotEqual(common_observations(legacy),common_observations(['changed']+security[1:]))
