import sys,tempfile,unittest,zipfile,stat,os,json
from unittest import mock
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from release_archive import write_archive,extract_archive,snapshot
class ReleaseArchiveTests(unittest.TestCase):
    def test_repeatable_bytes_and_exact_extraction(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);app=p/'RAID Admin.app';(app/'Contents/bin').mkdir(parents=True)
            f=app/'Contents/bin/launch';f.write_bytes(b'fixture');f.chmod(0o755)
            r=app/'Contents/readonly';r.write_bytes(b'read-only');r.chmod(0o444)
            before=write_archive(app,p/'a.zip');self.assertEqual(write_archive(app,p/'b.zip'),before)
            self.assertEqual((p/'a.zip').read_bytes(),(p/'b.zip').read_bytes())
            extracted=extract_archive(p/'a.zip',p/'out',app.name);self.assertEqual(snapshot(extracted),before)
    def test_symlink_source_and_existing_outputs_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);app=p/'A.app';app.mkdir();(app/'link').symlink_to('/does/not/exist')
            with self.assertRaises(ValueError):write_archive(app,p/'a.zip')
            (app/'link').unlink();(p/'a.zip').write_bytes(b'fixture')
            with self.assertRaises(ValueError):write_archive(app,p/'a.zip')
    def test_unsafe_archive_entries_refused_before_extraction(self):
        for name,kind,mode in [('A.app/../../escape',stat.S_IFREG,0o644),('/A.app/file',stat.S_IFREG,0o644),('A.app/link',stat.S_IFLNK,0o777),('A.app/file',stat.S_IFREG,0o666)]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as t:
                p=Path(t);info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(kind|mode)<<16
                with zipfile.ZipFile(p/'bad.zip','w') as z:z.writestr(info,b'fixture')
                with self.assertRaises(ValueError):extract_archive(p/'bad.zip',p/'out','A.app')
                self.assertFalse((p/'out').exists())
    def test_source_mutation_never_publishes_partial_archive(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);app=p/'A.app';app.mkdir();f=app/'file';f.write_bytes(b'original');before=snapshot(app)
            changed=dict(before);changed['file_modes']=dict(before['file_modes']);changed['file_modes']['file']=0o444
            with mock.patch('release_archive.snapshot',side_effect=[before,changed]),self.assertRaisesRegex(ValueError,'Source changed'):
                write_archive(app,p/'out.zip')
            self.assertFalse((p/'out.zip').exists())
    def test_headers_ignore_input_mtimes_and_creation_order(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            for root,order in [('one',('b','a')),('two',('a','b'))]:
                app=p/root/'A.app';(app/'empty').mkdir(parents=True);(app/'readonly').mkdir();(app/'readonly').chmod(0o555)
                for name in order:
                    f=app/name;f.write_bytes(name.encode());f.chmod(0o444);os.utime(f,(123 if root=='one' else 456,)*2)
                write_archive(app,p/(root+'.zip'))
            self.assertEqual((p/'one.zip').read_bytes(),(p/'two.zip').read_bytes())
            with zipfile.ZipFile(p/'one.zip') as z:
                for item in z.infolist():
                    self.assertEqual(item.date_time,(1980,1,1,0,0,0));self.assertEqual(item.compress_type,zipfile.ZIP_STORED);self.assertEqual(item.create_system,3);self.assertEqual(item.flag_bits,0);self.assertEqual(item.extra,b'');self.assertEqual(item.comment,b'')
            self.assertEqual(snapshot(extract_archive(p/'one.zip',p/'out','A.app')),snapshot(p/'one/A.app'))
    def test_aliases_implicit_parents_and_file_parents_refused(self):
        scenarios=[['A.app/file','A.app/FILE'],['A.app/é/','A.app/é/'],['A.app/missing/file'],['A.app/file','A.app/file/child'],['A.app//file'],['A.app/./file'],['A.app\\file']]
        for names in scenarios:
            with self.subTest(names=names),tempfile.TemporaryDirectory() as t:
                p=Path(t)
                with zipfile.ZipFile(p/'bad.zip','w') as z:
                    for name in ['A.app/']+names:
                        item=zipfile.ZipInfo(name);item.create_system=3;item.external_attr=((stat.S_IFDIR|0o755) if name.endswith('/') else (stat.S_IFREG|0o644))<<16;z.writestr(item,b'' if name.endswith('/') else b'x')
                with self.assertRaises(ValueError):extract_archive(p/'bad.zip',p/'out','A.app')
                self.assertFalse((p/'out').exists())
    def test_corrupt_payload_leaves_no_partial_extraction(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);app=p/'A.app';app.mkdir();(app/'file').write_bytes(b'payload');write_archive(app,p/'a.zip')
            with zipfile.ZipFile(p/'a.zip') as z:item=z.getinfo('A.app/file');offset=item.header_offset+30+len(item.filename.encode())+len(item.extra)
            data=bytearray((p/'a.zip').read_bytes());data[offset]^=1;(p/'a.zip').write_bytes(data)
            with self.assertRaises(zipfile.BadZipFile):extract_archive(p/'a.zip',p/'out','A.app')
            self.assertFalse((p/'out').exists())
    def test_release_publication_refuses_overlaps_and_cleans_verification_failure(self):
        from release_archive import main
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);source=p/'source';bundle=p/'bundle';source.mkdir();bundle.mkdir();app=bundle/'RAID Admin.app';app.mkdir();(app/'fixture').write_bytes(b'fixture')
            for directory in (source,bundle):(directory/'provenance.json').write_text(json.dumps({'bundled_runtime':{'architecture':'aarch64'},'source_dirty':False}))
            common=['release_archive','--source',str(source),'--bundle',str(bundle)]
            for output,record in [(p/'same',p/'same'),(bundle/'out',p/'record'),(p/'out',source/'record')]:
                with mock.patch.object(sys,'argv',common+['--output',str(output),'--record',str(record)]),self.assertRaisesRegex(ValueError,'overlap'):main()
            with mock.patch.object(sys,'argv',common+['--output',str(p/'out.zip'),'--record',str(p/'record.json')]),mock.patch('release_archive.clean_state',return_value={'commit':'fixture','dirty':False}),mock.patch('release_archive.check_bundle',return_value=snapshot(app)),mock.patch('release_archive.verify_runtime',side_effect=ValueError('signature rejected')),self.assertRaisesRegex(ValueError,'signature rejected'):main()
            self.assertFalse((p/'out.zip').exists());self.assertFalse((p/'record.json').exists())
    def test_record_link_failure_rolls_back_archive(self):
        from release_archive import main
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);source=p/'source';bundle=p/'bundle';source.mkdir();bundle.mkdir();app=bundle/'RAID Admin.app';app.mkdir();(app/'fixture').write_bytes(b'fixture')
            for directory in (source,bundle):(directory/'provenance.json').write_text(json.dumps({'bundled_runtime':{'architecture':'aarch64'},'source_dirty':False}))
            argv=['release_archive','--source',str(source),'--bundle',str(bundle),'--output',str(p/'out.zip'),'--record',str(p/'record.json')]
            original=os.link
            def link(a,b):
                if Path(b)==(p/'record.json').resolve():raise FileExistsError('fixture refusal')
                return original(a,b)
            with mock.patch.object(sys,'argv',argv),mock.patch('release_archive.clean_state',return_value={'commit':'fixture','dirty':False}),mock.patch('release_archive.check_bundle',return_value=snapshot(app)),mock.patch('release_archive.verify_runtime'),mock.patch('release_archive.os.link',side_effect=link),self.assertRaises(FileExistsError):main()
            self.assertFalse((p/'out.zip').exists());self.assertFalse((p/'record.json').exists())
