"""Trust-boundary checks: a self-consistent manifest must not bless modified content."""
import hashlib
import json
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_support import ROOT, digest, sha
from diagnose import diagnose


class BundledDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        reference = json.loads((ROOT/'audit/expected-build.json').read_text())['expected']
        source = json.loads((ROOT/'audit/security-clean-provenance.json').read_text())
        self.files = dict(reference['files']); self.modes = dict(reference['file_modes'])
        metadata = plistlib.loads((ROOT/'packaging/audit-Info.plist').read_bytes())
        metadata.update(CFBundleIdentifier='org.xserve-raid-admin.audit',
                        CFBundleShortVersionString=source['compatibility_version'], CFBundleVersion='4',
                        LSMinimumSystemVersion='11.0')
        self.files['Contents/Info.plist'] = hashlib.sha256(plistlib.dumps(metadata,sort_keys=True)).hexdigest()
        self.files['Contents/MacOS/RAIDAdmin'] = sha(ROOT/'packaging/RAIDAdmin')
        self.files['Contents/Resources/AppIcon.png'] = sha(ROOT/'packaging/AppIcon.png')
        self.modes['Contents/Resources/AppIcon.png'] = 0o644
        runtime = json.loads((ROOT/'audit/runtime-lock.json').read_text())['architectures']['aarch64']
        prefix = 'Contents/PlugIns/Runtime.jdk/'
        self.files.update({prefix+k:v for k,v in runtime['files'].items()})
        self.modes.update({prefix+k:v for k,v in runtime['file_modes'].items()})
        self.dirs = {str(p):0o755 for name in self.files for p in Path(name).parents}
        self.dirs.update({prefix[:-1] if k == '.' else prefix+k:v for k,v in runtime['directory_modes'].items()})

    def measure(self):
        # The filesystem reader is mocked; both claimed and measured data agree.
        # Only the independent repository anchors can reject the mutations below.
        measured = {'files':self.files,'file_modes':self.modes,'directory_modes':self.dirs}
        manifest = dict(measured, schema=3, bundle_tree_sha256=digest(measured),
                        source_commit=['a']*40, compatibility_version='synthetic-secret',
                        bundled_runtime={'architecture':'synthetic-secret','vendor':'synthetic-secret'})
        (self.output/'provenance.json').write_text(json.dumps(manifest))
        with patch('diagnose.tree',return_value=self.files), patch('diagnose.modes',return_value=self.modes), patch('diagnose.directory_modes',return_value=self.dirs):
            return diagnose(self.output)

    def test_bundled_identity_comes_from_lock_not_manifest(self):
        result = self.measure()
        self.assertTrue(result['matches_build_manifest'])
        self.assertTrue(result['matches_reviewed_artifact'])
        self.assertEqual(result['bundled_jre']['architecture'],'aarch64')
        self.assertEqual(result['event']['result'],'pass')
        self.assertNotIn('synthetic-secret',json.dumps(result))

    def test_self_consistent_changed_launcher_is_rejected(self):
        self.files['Contents/MacOS/RAIDAdmin']='0'*64
        result=self.measure()
        self.assertTrue(result['matches_build_manifest'])
        self.assertFalse(result['matches_reviewed_artifact'])
        self.assertEqual(result['event']['result'],'fail')

    def test_extra_file_is_rejected(self):
        self.files['Contents/unexpected']='0'*64; self.modes['Contents/unexpected']=0o644
        self.assertFalse(self.measure()['matches_reviewed_artifact'])

    def test_changed_runtime_permission_is_rejected(self):
        self.modes['Contents/PlugIns/Runtime.jdk/Contents/Home/bin/java']=0o644
        result=self.measure()
        self.assertEqual(result['bundled_jre'],'unrecognized')
        self.assertFalse(result['matches_reviewed_artifact'])

    def test_changed_runtime_directory_is_rejected(self):
        self.dirs['Contents/PlugIns/Runtime.jdk']=0o700
        self.assertFalse(self.measure()['matches_reviewed_artifact'])

    def test_extra_empty_directory_is_rejected(self):
        self.dirs['Contents/unexpected']=0o755
        self.assertFalse(self.measure()['matches_reviewed_artifact'])
