import ast
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import firmware_preflight as preflight
from audit_support import ROOT, isolated_env


class FirmwarePreflightTests(unittest.TestCase):
    def code(self, function, value, expected):
        with self.assertRaises(preflight.PreflightError) as caught:
            function(value)
        self.assertEqual(caught.exception.code, expected)
        self.assertEqual(str(caught.exception), expected)

    def test_unknown_archives_never_reach_any_zip_or_network_parser(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('../DO_NOT_RENDER', b'x'*(2*1024*1024))
        snapshots=[b'',b'not a zip',stream.getvalue()]
        with patch.object(zipfile,'ZipFile',side_effect=AssertionError('Parser reached')), \
             patch.object(zlib,'decompressobj',side_effect=AssertionError('Inflater reached')), \
             patch.object(zlib,'decompress',side_effect=AssertionError('Inflater reached')), \
             patch.object(socket,'socket',side_effect=AssertionError('Socket reached')), \
             patch.object(socket,'create_connection',side_effect=AssertionError('Connect reached')):
            for snapshot in snapshots:
                self.code(preflight.validate_snapshot,snapshot,'UNRECOGNIZED_PACKAGE')

    def test_immutable_type_and_size_bound(self):
        class BytesSubclass(bytes):pass
        for value in (bytearray(),memoryview(b''),BytesSubclass(),None):
            self.code(preflight.validate_snapshot,value,'TYPE_REJECTED')
        self.code(preflight.validate_snapshot,b'x'*(preflight.PACKAGE_SIZE+1),'SIZE_REJECTED')

    def test_regular_file_snapshot_is_independent_and_short_reads_accumulate(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'input.xfb';path.write_bytes(b'synthetic fixture')
            actual_read=os.read
            with patch.object(os,'read',side_effect=lambda descriptor,count:actual_read(descriptor,min(count,3))):
                snapshot=preflight.read_snapshot(path)
            self.assertIs(type(snapshot),bytes)
            path.write_bytes(b'changed')
            self.assertEqual(snapshot,b'synthetic fixture')
            self.code(preflight.validate_snapshot,snapshot,'UNRECOGNIZED_PACKAGE')

    def test_type_size_and_failed_read_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'input.xfb';path.write_bytes(b'x')
            link=root/'link';link.symlink_to(path)
            fifo=root/'fifo';os.mkfifo(fifo)
            for value in (root,link,fifo):self.code(preflight.read_snapshot,value,'NOT_REGULAR_FILE')
            self.code(preflight.read_snapshot,root/'missing_DO_NOT_RENDER','READ_FAILED')
            self.code(preflight.read_snapshot,'DO_NOT_RENDER\0','READ_FAILED')
            with patch.object(os,'read',return_value=b''):
                self.code(preflight.read_snapshot,path,'READ_FAILED')
            path.write_bytes(b'x'*(preflight.PACKAGE_SIZE+1))
            self.code(preflight.read_snapshot,path,'SIZE_REJECTED')

    def test_growth_identity_and_request_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'input.xfb';path.write_bytes(b'x')
            with patch.object(os,'read',side_effect=[b'xy',b'']):
                self.code(preflight.read_snapshot,path,'READ_FAILED')
            requested=[]
            def growing(descriptor,count):
                requested.append(count);return b'x'*count
            with patch.object(os,'read',side_effect=growing):
                self.code(preflight.read_snapshot,path,'SIZE_REJECTED')
            self.assertLessEqual(max(requested),65536)
            self.assertEqual(sum(requested),preflight.PACKAGE_SIZE+1)
            metadata=list(path.stat());metadata[1]+=1
            with patch.object(os,'fstat',return_value=os.stat_result(metadata)),patch.object(os,'read',side_effect=AssertionError('Read prohibited')):
                self.code(preflight.read_snapshot,path,'NOT_REGULAR_FILE')
            with patch.object(os,'open',side_effect=AssertionError('Device open prohibited')):
                self.code(preflight.read_snapshot,'/dev/null','NOT_REGULAR_FILE')

    def test_cli_errors_never_echo_argument_or_filesystem_text(self):
        for args in (['--DO_NOT_RENDER'],['/__missing_DO_NOT_RENDER']):
            result=subprocess.run([sys.executable,str(ROOT/'tools/firmware_preflight.py')]+args,
                                  env=isolated_env(),capture_output=True,text=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(result.stderr,'')
            self.assertNotIn('DO_NOT_RENDER',result.stdout)
            self.assertEqual(json.loads(result.stdout)['result'],'REJECTED')

    def test_runtime_imports_allow_only_local_stdlib_read_hash_output(self):
        source=ast.parse((ROOT/'tools/firmware_preflight.py').read_text())
        imports=set()
        for node in ast.walk(source):
            if isinstance(node,ast.Import):
                imports.update(n.name for n in node.names)
                self.assertTrue(all(n.asname is None for n in node.names))
            if isinstance(node,ast.ImportFrom):
                imports.add(node.module)
                self.assertEqual((node.module,[(n.name,n.asname) for n in node.names]),('dataclasses',[('dataclass',None)]))
            if isinstance(node,ast.Name):
                self.assertNotIn(node.id,('eval','exec','__import__','getattr','open','compile','globals','vars','breakpoint'))
            if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name) and node.value.id=='os':
                self.assertIn(node.attr,{'lstat','open','fstat','read','close','O_RDONLY','O_NOFOLLOW','O_NONBLOCK','O_CLOEXEC'})
        self.assertEqual(imports,{'argparse','hashlib','json','os','stat','dataclasses'})
