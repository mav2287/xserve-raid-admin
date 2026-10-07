import hashlib,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from spdx import generate
from audit_support import tree
class SpdxTests(unittest.TestCase):
    def fixture(self,root):
        app=root/'A.app';(app/'Contents/Resources').mkdir(parents=True);(app/'Contents/PlugIns/Runtime.jdk').mkdir(parents=True)
        (app/'Contents/PlugIns/Runtime.jdk/LICENSE').write_bytes(b'fixture notice')
        with zipfile.ZipFile(app/'Contents/Resources/RAID_Admin.jar','w') as z:z.writestr('Original.class',b'original fixture');z.writestr('compat/Added.class',b'compat fixture')
        manifest={'files':tree(app),'compatibility_version':'fixture','original_jar_sha256':'0'*64,'bundled_runtime':{'vendor':'fixture runtime','version':'fixture','architecture':'fixture'}}
        return app,manifest,[{'name':'Original component','files':{'Original.class':'historical-reference'}}]
    def test_deterministic_complete_inventory_and_independent_verification_codes(self):
        with tempfile.TemporaryDirectory() as t:
            app,manifest,components=self.fixture(Path(t));a=generate(app,manifest,'2026-10-06T00:00:00Z',components);b=generate(app,manifest,'2026-10-06T00:00:00Z',components);self.assertEqual(a,b)
            self.assertEqual(len(a['files']),4);self.assertEqual(a['spdxVersion'],'SPDX-2.3')
            byname={f['fileName']:f for f in a['files']}
            self.assertEqual(byname['./A.app/Contents/Resources/RAID_Admin.jar!/Original.class']['checksums'][0]['checksumValue'],hashlib.sha256(b'original fixture').hexdigest())
            jar=next(p for p in a['packages'] if p['SPDXID']=='SPDXRef-jar');hashes=sorted(hashlib.sha1(data).hexdigest() for data in [b'original fixture',b'compat fixture']);self.assertEqual(jar['packageVerificationCode']['packageVerificationCodeValue'],hashlib.sha1(''.join(hashes).encode()).hexdigest())
            self.assertTrue(all(p['licenseDeclared']=='NOASSERTION' for p in a['packages']))
    def test_overlapping_components_and_invalid_dates_refused(self):
        with tempfile.TemporaryDirectory() as t:
            app,manifest,components=self.fixture(Path(t))
            with self.assertRaises(ValueError):generate(app,manifest,'invalid',components)
            with self.assertRaises(ValueError):generate(app,manifest,'2026-10-06T00:00:00Z',components+components)
    def test_semantic_tampering_and_missing_checksums_refused(self):
        import copy
        from spdx import validate_semantics
        with tempfile.TemporaryDirectory() as t:
            app,manifest,components=self.fixture(Path(t));doc=generate(app,manifest,'2026-10-06T00:00:00Z',components);validate_semantics(doc)
            for operation in range(6):
                bad=copy.deepcopy(doc)
                if operation==0:bad['files'][0]['checksums']=bad['files'][0]['checksums'][:1]
                elif operation==1:bad['files'][0]['checksums'][0]['checksumValue']='A'*64
                elif operation==2:bad['files'][0]['SPDXID']+='\n'
                elif operation==3:bad['relationships'].append(dict(bad['relationships'][0]))
                elif operation==4:bad['documentNamespace']='https://example.invalid/tampered'
                else:bad['packages'][0]['packageVerificationCode']['packageVerificationCodeValue']='0'*40
                with self.subTest(operation=operation),self.assertRaises(ValueError):validate_semantics(bad)
    def test_modified_original_members_are_explicit_and_bounded(self):
        with tempfile.TemporaryDirectory() as t:
            app,manifest,components=self.fixture(Path(t));components[0]['files']['Original.class']=hashlib.sha256(b'old-original fixture').hexdigest()
            doc=generate(app,manifest,'2026-10-06T00:00:00Z',components,{'Original.class'},{'compat/Added.class'})
            original=next(f for f in doc['files'] if f['fileName'].endswith('!/Original.class'));self.assertIn('Compatibility override',original['comment'])
            package=next(p for p in doc['packages'] if p['SPDXID']=='SPDXRef-component-0');self.assertIn('compatibility',package['versionInfo'])
            with self.assertRaises(ValueError):generate(app,manifest,'2026-10-06T00:00:00Z',components,set(),{'compat/Added.class'})
    def test_unsafe_members_dates_empty_components_and_file_changes_refused(self):
        for name in ('../escape','/absolute','a\\b','a!/b','a//b'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as t:
                app,manifest,components=self.fixture(Path(t))
                with zipfile.ZipFile(app/'Contents/Resources/RAID_Admin.jar','a') as z:z.writestr(name,b'fixture')
                manifest['files']=tree(app)
                with self.assertRaises(ValueError):generate(app,manifest,'2026-10-06T00:00:00Z',components)
        with tempfile.TemporaryDirectory() as t:
            app,manifest,components=self.fixture(Path(t))
            for date in ('2026-1-06T00:00:00Z','2026-10-06T00:00:00Z\n','2026-10-06T23:59:60Z'):
                with self.assertRaises(ValueError):generate(app,manifest,date,components)
            with self.assertRaises(ValueError):generate(app,manifest,'2026-10-06T00:00:00Z',components+[{'name':'empty','files':{}}])
            (app/'Contents/PlugIns/Runtime.jdk/LICENSE').write_bytes(b'changed fixture')
            with self.assertRaises(ValueError):generate(app,manifest,'2026-10-06T00:00:00Z',components)
