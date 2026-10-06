import json
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_transport import common_observations, completed_io

class TransportComparisonTests(unittest.TestCase):
    def test_io_gate_rejects_invented_success_without_exposing_payload(self):
        with self.assertRaises(ValueError) as caught:
            completed_io('io null-message callbacks=1 DO_NOT_RENDER\nPASS IO characterization; guarded_operations=0')
        self.assertNotIn('DO_NOT_RENDER',str(caught.exception))
    def test_io_gate_requires_fixed_and_legacy_vectors_explicitly(self):
        record=Path(__file__).resolve().parents[1]/'audit/io-characterization-clean-results.json'
        legacy=json.loads(record.read_text())['io_observations'][0]['results']
        fixed=list(legacy);fixed[:3]=['io invalid-header message_has_peer_line=false; direct_sends=1','queue_response invalid-header-read-terminal result=-102 sends=1 terminal_callbacks=1','queue_response invalid-header-mutation-terminal result=-102 sends=1 terminal_callbacks=1']
        fixed.insert(-1,'io sync invalid-header fixed-IOException; no-peer-or-cause; sends=1')
        self.assertEqual(completed_io('\n'.join(fixed),True),fixed)
        for lines,mode in ((legacy,True),(fixed,False)):
            with self.assertRaises(ValueError):completed_io('\n'.join(lines),mode)
    def test_invalid_header_gate_cannot_accept_legacy_outcome(self):
        legacy=['response invalid-header protocol-error','follow_on invalid-length results=-102,-102; sends=1; outstanding=true; reconnects=0']
        fixed=['response invalid-header framing-rejected']+legacy[1:]
        self.assertEqual(common_observations(legacy),common_observations(fixed,require_invalid_header_policy=True))
        for bad in (legacy,fixed+fixed[:1],fixed+legacy[:1]):
            with self.assertRaises(ValueError):common_observations(bad,require_invalid_header_policy=True)
    def test_framing_changes_require_complete_explicit_evidence(self):
        legacy=['response missing-length empty','response missing-length-idle empty','response duplicate-last-valid result=0','response duplicate-last-zero empty','response chunked empty','response lowercase-length empty','queue_response lowercase-length-empty-success result=0 sends=1 terminal_callbacks=1','follow_on invalid-length results=-102,-102; sends=1; outstanding=true; reconnects=0']
        candidate=['response missing-length framing-rejected','response missing-length-idle framing-rejected','response duplicate-last-valid framing-rejected','response duplicate-last-zero framing-rejected','response chunked framing-rejected','response lowercase-length result=0','queue_response lowercase-length-parsed-success result=0 sends=1 terminal_callbacks=1']+legacy[-1:]
        self.assertEqual(common_observations(legacy),common_observations(candidate,require_framing_policy=True))
        for bad in (candidate[1:],candidate+candidate[:1],candidate+legacy[:1]):
            with self.assertRaises(ValueError):common_observations(bad,require_framing_policy=True)
        with self.assertRaises(ValueError):common_observations(legacy,require_framing_policy=True)
    def test_only_explicit_length_policy_differences_are_allowed(self):
        legacy=['normal','follow_on invalid-length results=-102,-102; sends=1; outstanding=true; reconnects=0','PASS']
        security=['normal']+['security_length '+label+' fixed-marker; closed; no-input-or-cause' for label in ('invalid-length','negative-length','overflow-length')]+['security_length follow-on qualified by recovery fixture','PASS']
        self.assertEqual(common_observations(legacy),common_observations(security))
        for bad in (security[:-2]+['PASS'],security+['security_length invented'],['normal','PASS']):
            with self.assertRaises(ValueError):common_observations(bad)
        with self.assertRaises(ValueError):common_observations(legacy,True)
        self.assertEqual(common_observations(security,True),common_observations(legacy))
        self.assertNotEqual(common_observations(legacy),common_observations(['changed']+security[1:]))
