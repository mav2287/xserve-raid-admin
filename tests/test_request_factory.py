import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from check_request_factory import validate, qualification_gate, bootstrap_path, CATALOG, EXPECTED
from audit_support import ROOT
import tempfile


class RequestFactoryTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads(CATALOG.read_text())
        self.expected=json.loads(EXPECTED.read_text())

    def test_complete_fixture_table_and_firmware_exclusion(self):
        self.assertEqual(validate(json.dumps(self.expected),self.catalog),self.expected)
        self.assertEqual(len(self.expected['rows']),116)
        self.assertFalse(any(row['signature'] in self.catalog['excluded'] for row in self.expected['rows']))

    def test_missing_duplicate_or_reordered_factory_rows_fail(self):
        for kind in ('missing','duplicate','reordered'):
            value=copy.deepcopy(self.expected)
            if kind=='missing':value['rows'].pop()
            elif kind=='duplicate':value['rows'][1]=value['rows'][0]
            else:value['rows'][0],value['rows'][1]=value['rows'][1],value['rows'][0]
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate(json.dumps(value),self.catalog)

    def test_bad_body_bounds_and_digests_fail_without_payload(self):
        for key,bad in (('body_size',65537),('body_size',True),('body_sha256','DO_NOT_RENDER')):
            value=copy.deepcopy(self.expected);value['rows'][0][key]=bad
            with self.assertRaises(ValueError) as caught:validate(json.dumps(value),self.catalog)
            self.assertNotIn('DO_NOT_RENDER',str(caught.exception))

    def test_missing_or_invented_enqueue_sharing_fails(self):
        for change in ('missing','changed'):
            value=copy.deepcopy(self.expected)
            if change=='missing':value['enqueue_observations'].pop()
            else:value['enqueue_observations'][0]['body_changed_after_post']=False
            with self.assertRaises(ValueError):validate(json.dumps(value),self.catalog)

    def test_reviewed_table_rejects_any_changed_semantics(self):
        for key,bad in (('shutdown',True),('factory_timeout',1),('factory_timeout',False),('body_sha256','a'*64),('body_size',1),('restart',0),('target','TARGET_TOP'),('shared_headers',False)):
            value=copy.deepcopy(self.expected);value['rows'][0][key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):validate(json.dumps(value),self.catalog,self.expected)
        value=copy.deepcopy(self.expected);value['rows'][0]['extra']='DO_NOT_RENDER'
        with self.assertRaises(ValueError):validate(json.dumps(value),self.catalog,self.expected)

    def test_reviewed_table_rejects_coverage_variants(self):
        for mode in ('signature-missing','signature-extra','signature-order','excluded-row','extra-row'):
            value=copy.deepcopy(self.expected)
            if mode=='signature-missing':value['signatures'].pop()
            elif mode=='signature-extra':value['signatures'].append('invented')
            elif mode=='signature-order':value['signatures'].reverse()
            elif mode=='excluded-row':value['rows'][0]['signature']=self.catalog['excluded'][0]
            else:value['rows'].append(copy.deepcopy(value['rows'][0]))
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate(json.dumps(value),self.catalog,self.expected)

    def test_qualification_requires_clean_both_runtimes_current_candidate(self):
        current='a'*64;both={'aarch64','x64'}
        qualification_gate(False,both,current,current,False)
        for dirty,architectures,candidate,original in ((True,both,current,False),(False,{'aarch64'},current,False),(False,both,'b'*64,False),(False,both,current,True)):
            with self.assertRaises(ValueError):qualification_gate(dirty,architectures,candidate,current,original)

    def test_bootstrap_path_cannot_escape_or_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='factory-path-test-',dir=ROOT/'build') as tmp:
            root=Path(tmp)
            self.assertEqual(bootstrap_path(root/'new.json'),root/'new.json')
            (root/'existing.json').write_text('fixture')
            (root/'outside').symlink_to(ROOT/'audit',target_is_directory=True)
            for path in (root/'existing.json',ROOT/'build/../audit/never-created-factory.json',root/'outside/never-created-factory.json'):
                with self.assertRaises(ValueError):bootstrap_path(path)

    def test_sharing_boolean_coercion_is_rejected(self):
        for replacement in (1,1.0):
            value=copy.deepcopy(self.expected)
            value['enqueue_observations'][0]['header_shared']=replacement
            with self.assertRaises(ValueError):validate(json.dumps(value),self.catalog,self.expected)

    def test_duplicate_json_keys_are_rejected(self):
        raw=json.dumps(self.expected)
        for old,new in (('"header_shared": true','"header_shared": false, "header_shared": true'),('"guarded_operations": 0','"guarded_operations": 1, "guarded_operations": 0')):
            with self.assertRaises(ValueError):validate(raw.replace(old,new,1),self.catalog,self.expected)
