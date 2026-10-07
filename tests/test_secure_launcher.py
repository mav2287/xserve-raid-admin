import os
import json
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SecureLauncherTests(unittest.TestCase):
    def test_embedded_runtime_arguments_and_ambient_injection(self):
        with tempfile.TemporaryDirectory(prefix='raid launcher ') as tmp:
            app = Path(tmp).resolve() / 'RAID Admin.app/Contents'
            macos = app / 'MacOS'; macos.mkdir(parents=True)
            resource = app / 'Resources'; resource.mkdir()
            (resource / 'RAID_Admin.jar').write_bytes(b'fixture')
            launch = macos / 'RAIDAdmin'
            launch.write_bytes((ROOT / 'modernization/private-preferences/RAIDAdmin').read_bytes()); launch.chmod(0o755)
            java = app / 'PlugIns/Runtime.jdk/Contents/Home/bin/java'; java.parent.mkdir(parents=True)
            java.write_text('''#!/bin/sh
for arg do
    if [ "$arg" = "-version" ]; then exit 0; fi
done
[ -z "$JAVA_TOOL_OPTIONS$_JAVA_OPTIONS$JDK_JAVA_OPTIONS$CLASSPATH$JAVA_HOME$BASH_ENV$ENV$CDPATH$JAVA_LIBRARY_PATH$_JAVA_SPLASH_FILE$_JAVA_SPLASH_JAR$_JAVA_VERSION_SET$_JAVA_LAUNCHER_DEBUG$DYLD_INSERT_LIBRARIES" ] || exit 90
printf '%s\\n' "$@"
'''); java.chmod(0o755)
            injection = Path(tmp) / 'injection'
            injection.write_text('touch "' + str(Path(tmp) / 'executed') + '"\n')
            env = {'PATH':'/unavailable','BASH_ENV':str(injection),'ENV':str(injection),'CDPATH':'/unavailable',
                   'JAVA_TOOL_OPTIONS':'synthetic','_JAVA_OPTIONS':'synthetic','JDK_JAVA_OPTIONS':'synthetic',
                   'CLASSPATH':'synthetic','JAVA_HOME':'/unavailable','JAVA_LIBRARY_PATH':'synthetic','_JAVA_SPLASH_FILE':'synthetic','_JAVA_SPLASH_JAR':'synthetic','_JAVA_VERSION_SET':'synthetic','_JAVA_LAUNCHER_DEBUG':'synthetic'}
            result = subprocess.run([str(launch),'input with spaces','-fixture'],env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0)
            args = result.stdout.splitlines()
            self.assertEqual(args[-2:],['input with spaces','-fixture'])
            self.assertIn('-Djava.ext.dirs=' + str(java.parent.parent / 'jre/lib/ext'),args)
            self.assertIn('-Djava.library.path=' + str(java.parent.parent / 'jre/lib'),args)
            self.assertIn('-Djava.endorsed.dirs=',args)
            self.assertIn('-Draid.admin.gui=false',args)
            self.assertIn('-Xdock:icon=' + str(resource / 'AppIcon.png'),args)
            self.assertIn(str(resource / 'RAID_Admin.jar'),args)
            self.assertFalse((Path(tmp) / 'executed').exists())
            self.assertNotIn('/tmp/RAIDAdmin_icon.png',result.stdout)

    def observe_application_arguments(self, arguments):
        with tempfile.TemporaryDirectory(prefix='raid argv ') as temporary:
            contents=Path(temporary).resolve()/'RAID Admin.app/Contents'
            launch=contents/'MacOS/RAIDAdmin';launch.parent.mkdir(parents=True)
            launch.write_bytes((ROOT/'modernization/private-preferences/RAIDAdmin').read_bytes());launch.chmod(0o755)
            jar=contents/'Resources/RAID_Admin.jar';jar.parent.mkdir();jar.write_bytes(b'fixture')
            java=contents/'PlugIns/Runtime.jdk/Contents/Home/bin/java';java.parent.mkdir(parents=True)
            java.write_text('#!'+sys.executable+' -I\nimport json,sys\nif "-version" in sys.argv and "-jar" not in sys.argv:sys.exit(0)\nprint(json.dumps(sys.argv[1:]))\n');java.chmod(0o755)
            result=subprocess.run([str(launch)]+arguments,env={'PATH':'/unavailable'},capture_output=True,text=True,timeout=10)
            self.assertEqual((result.returncode,result.stderr),(0,''))
            argv=json.loads(result.stdout);index=argv.index('-jar');self.assertEqual(argv[index+1],str(jar))
            remaining=argv[index+2:]
            self.assertIn('-Draid.admin.gui='+('false' if remaining else 'true'),argv)
            self.assertEqual(sum(v.startswith('-Draid.admin.gui=') for v in argv),1)
            return remaining

    def test_launchservices_metadata_does_not_enter_cli(self):
        self.assertEqual(self.observe_application_arguments(['-psn_0_123456']),[])
        self.assertEqual(self.observe_application_arguments([]),[])

    def test_remaining_arguments_preserve_exact_bytes_and_order(self):
        arguments=['path with spaces','', 'é', 'line\nbreak', '-psn_2_3']
        self.assertEqual(self.observe_application_arguments(['-psn_1_2']+arguments),arguments)

    def test_cli_and_noncanonical_metadata_are_preserved(self):
        for arguments in [['-psn_custom'],['-psn_1'],['-psn_1_2extra'],['-psn_-1_2'],['command','-psn_1_2'],['-psn_1_2\n']]:
            with self.subTest(arguments=arguments):self.assertEqual(self.observe_application_arguments(arguments),arguments)
