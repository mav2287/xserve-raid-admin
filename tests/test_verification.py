import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import baseline
from audit_support import tree, modes, digest, sha
from verify_builds import entries, verify, check_artifact
from diagnose import diagnose

class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name); self.a=root/'a'; self.b=root/'b'; self.expected=root/'expected.json'
        reference=entries(baseline.ROOT/'original/RAID_Admin_original.jar')
        reference.update({n:b'synthetic patch fixture' for n in baseline.ALLOWED_JAR_CHANGES})
        reference['META-INF/MANIFEST.MF']=b'Manifest-Version: 1.0\r\nMain-Class: Launcher\r\n\r\n'
        lock=json.loads((baseline.ROOT/'audit/jdk-lock.json').read_text())
        for output in [self.a,self.b]:
            app=output/'RAID Admin.app'; resources=app/'Contents/Resources'; resources.mkdir(parents=True)
            launch=app/'Contents/MacOS/RAIDAdmin'; launch.parent.mkdir(); launch.write_text('#!/bin/sh\n'); launch.chmod(0o755)
            baseline.write_jar(resources/'RAID_Admin.jar',reference)
            manifest={'schema':2,'files':tree(app),'file_modes':modes(app),'input_hashes':{'build.sh':sha(baseline.ROOT/'build.sh')},'jdk':{k:v for k,v in lock.items() if k!='files'},'original_jar_sha256':baseline.ORIGINAL_SHA256,'builder':{},'source_commit':'0'*40,'source_dirty':False,'compatibility_version':baseline.VERSION}
            manifest['bundle_tree_sha256']=digest({k:manifest[k] for k in ['files','file_modes']})
            (output/'provenance.json').write_text(json.dumps(manifest))
        with contextlib.redirect_stdout(io.StringIO()): verify(self.a,self.b,expected_path=self.expected,update_reason='synthetic test baseline')

    def test_clean_fixtures_match_expected(self):
        with contextlib.redirect_stdout(io.StringIO()): verify(self.a,self.b,expected_path=self.expected)
        self.assertTrue(diagnose(self.a)['matches_build_manifest'])
        self.assertIsInstance(diagnose(self.a)['build_jdk'],dict)

    def test_lost_executable_bit_rejected(self):
        (self.a/'RAID Admin.app/Contents/MacOS/RAIDAdmin').chmod(0o644)
        with self.assertRaisesRegex(ValueError,'modes'): check_artifact(self.a)
        self.assertFalse(diagnose(self.a)['matches_build_manifest'])

    def test_both_self_consistent_changed_builds_fail_expected_gate(self):
        for output in [self.a,self.b]:
            app=output/'RAID Admin.app'; (app/'Contents/MacOS/RAIDAdmin').write_text('#!/bin/sh\nexit 1\n')
            p=output/'provenance.json'; m=json.loads(p.read_text()); m['files']=tree(app); m['bundle_tree_sha256']=digest({k:m[k] for k in ['files','file_modes']}); p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'reviewed expected'): verify(self.a,self.b,expected_path=self.expected)

    def test_unallowlisted_class_change_rejected_even_with_matching_manifest(self):
        app=self.a/'RAID Admin.app'; jar=app/'Contents/Resources/RAID_Admin.jar'; data=entries(jar); data['com/apple/xsr/Main.class']=b'corrupted'; baseline.write_jar(jar,data)
        p=self.a/'provenance.json'; m=json.loads(p.read_text()); m['files']=tree(app); m['bundle_tree_sha256']=digest({k:m[k] for k in ['files','file_modes']}); p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'allowlist'): check_artifact(self.a)

    def test_diagnostics_do_not_echo_untrusted_jdk_fields(self):
        p=self.a/'provenance.json'; m=json.loads(p.read_text()); m['jdk']['vendor']='synthetic-secret'; p.write_text(json.dumps(m))
        self.assertNotIn('synthetic-secret',json.dumps(diagnose(self.a)))
        self.assertEqual(diagnose(self.a)['build_jdk'],'unrecognized build JDK')

    def test_diagnostics_reject_unknown_schema_without_echo(self):
        for schema in [True, 4, 'synthetic-secret', None]:
            p=self.a/'provenance.json'; m=json.loads(p.read_text()); m['schema']=schema; p.write_text(json.dumps(m))
            result=diagnose(self.a)
            self.assertFalse(result['matches_build_manifest'])
            self.assertNotIn('synthetic-secret',json.dumps(result))

    def test_diagnostics_commit_requires_string_and_correct_digest(self):
        p=self.a/'provenance.json'; m=json.loads(p.read_text()); m['source_commit']=['a']*40
        m['bundle_tree_sha256']='0'*64; p.write_text(json.dumps(m))
        result=diagnose(self.a)
        self.assertEqual(result['source_commit'],'unknown')
        self.assertFalse(result['matches_build_manifest'])

    def test_diagnostics_bound_and_malformed_manifest(self):
        p=self.a/'provenance.json'
        for data in [b'{"synthetic-secret":', b' '* (1024*1024+1), b'['*5000]:
            p.write_bytes(data); result=diagnose(self.a)
            self.assertFalse(result['matches_build_manifest'])
            self.assertNotIn('synthetic-secret',json.dumps(result))

    def test_diagnostics_reject_fifo_and_symlink(self):
        p=self.a/'provenance.json'; p.unlink(); os.mkfifo(p)
        self.assertFalse(diagnose(self.a)['matches_build_manifest'])
        p.unlink(); p.symlink_to(self.b/'provenance.json')
        self.assertFalse(diagnose(self.a)['matches_build_manifest'])

if __name__ == '__main__': unittest.main()
