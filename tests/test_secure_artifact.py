import json,os,plistlib,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_support import tree,modes,digest
from secure_build import check_secure_artifact

@unittest.skipUnless(os.environ.get('RAID_SECURE_BUILD'),'explicit secure fixture artifact required')
class SecureArtifactTests(unittest.TestCase):
 def setUp(self):
  self.temporary=tempfile.TemporaryDirectory(prefix='secure-artifact-',dir=ROOT/'build');self.addCleanup(self.temporary.cleanup);self.output=Path(self.temporary.name);source=Path(os.environ['RAID_SECURE_BUILD'])
  for name in ['RAID Admin.app','audit27-reference','native']:shutil.copytree(source/name,self.output/name)
  shutil.copyfile(source/'provenance.json',self.output/'provenance.json');self.app=self.output/'RAID Admin.app'
 def self_consistent_manifest(self):
  path=self.output/'provenance.json';record=json.loads(path.read_text());record['files']=tree(self.app);record['file_modes']=modes(self.app);record['bundle_tree_sha256']=digest({'files':record['files'],'file_modes':record['file_modes']});path.write_text(json.dumps(record))
 def test_correct_candidate_is_verified(self):check_secure_artifact(self.output)
 def test_modified_launcher_is_rejected_even_with_self_consistent_manifest(self):
  with (self.app/'Contents/MacOS/RAIDAdmin').open('ab') as out:out.write(b'\n# unauthorized change\n')
  self.self_consistent_manifest()
  with self.assertRaisesRegex(ValueError,'non-JAR artifact delta'):check_secure_artifact(self.output)
 def test_added_file_is_rejected_even_with_self_consistent_manifest(self):
  (self.app/'Contents/Resources/unapproved').write_bytes(b'fixture');self.self_consistent_manifest()
  with self.assertRaisesRegex(ValueError,'non-JAR artifact delta'):check_secure_artifact(self.output)
 def test_unapproved_plist_field_is_rejected(self):
  path=self.app/'Contents/Info.plist';record=plistlib.loads(path.read_bytes());record['UnapprovedFixture']='fixture';path.write_bytes(plistlib.dumps(record));self.self_consistent_manifest()
  with self.assertRaisesRegex(ValueError,'two version fields'):check_secure_artifact(self.output)
 def test_original_baseline_cannot_be_redefined_by_its_manifest(self):
  reference=self.output/'audit27-reference/RAID Admin.app/Contents/MacOS/RAIDAdmin';reference.write_bytes(b'fixture');path=self.output/'audit27-reference/provenance.json';record=json.loads(path.read_text());record['files']=tree(self.output/'audit27-reference/RAID Admin.app');record['file_modes']=modes(self.output/'audit27-reference/RAID Admin.app');path.write_text(json.dumps(record))
  with self.assertRaisesRegex(ValueError,'independently frozen identity'):check_secure_artifact(self.output)
 def test_altered_native_bytes_are_rejected(self):
  record=json.loads((self.output/'provenance.json').read_text());path=self.output/record['native_helpers']['aarch64']['path'];path.write_bytes(b'fixture')
  with self.assertRaisesRegex(ValueError,'Secure native changed'):check_secure_artifact(self.output)
