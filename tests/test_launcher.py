import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_embedded_runtime_arguments_and_ambient_injection(self):
        with tempfile.TemporaryDirectory(prefix='raid launcher ') as tmp:
            app = Path(tmp).resolve() / 'RAID Admin.app/Contents'
            macos = app / 'MacOS'; macos.mkdir(parents=True)
            resource = app / 'Resources'; resource.mkdir()
            (resource / 'RAID_Admin.jar').write_bytes(b'fixture')
            launch = macos / 'RAIDAdmin'
            launch.write_bytes((ROOT / 'packaging/RAIDAdmin').read_bytes()); launch.chmod(0o755)
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
            self.assertIn('-Xdock:icon=' + str(resource / 'AppIcon.png'),args)
            self.assertIn(str(resource / 'RAID_Admin.jar'),args)
            self.assertFalse((Path(tmp) / 'executed').exists())
            self.assertNotIn('/tmp/RAIDAdmin_icon.png',result.stdout)
