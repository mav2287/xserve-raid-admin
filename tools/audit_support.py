"""Shared deterministic input checks and isolated Java subprocesses."""
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]
JAVA_FLAGS = ['-Djava.ext.dirs=', '-Djava.endorsed.dirs=', '-Dfile.encoding=UTF-8',
              '-Duser.language=en', '-Duser.country=US', '-Duser.timezone=UTC']


def isolated_env():
    # Never echo, hash or propagate arbitrary ambient JVM options or credentials.
    return {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8', 'TZ': 'UTC'}


def regular_files(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Expected a real directory, not a symlink')
    found = []
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            if p.is_symlink():
                raise ValueError('Symlinks are not permitted in audit inputs or bundles')
        for name in files:
            p = Path(base) / name
            if not stat.S_ISREG(p.stat().st_mode):
                raise ValueError('Non-regular audit input')
            found.append(p)
    return sorted(found)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(root):
    return {str(p.relative_to(root)): sha(p) for p in regular_files(root)}


def modes(root):
    return {str(p.relative_to(root)): stat.S_IMODE(p.stat().st_mode) for p in regular_files(root)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_python():
    expected = json.loads((ROOT / 'audit/python-lock.json').read_text())
    if platform.python_version() != expected['version'] or platform.python_implementation() != expected['implementation']:
        raise ValueError('Python differs from audit/python-lock.json')


def verify_jdk(jdk):
    jdk = Path(jdk).absolute()
    lock = json.loads((ROOT / 'audit/jdk-lock.json').read_text())
    if tree(jdk) != lock['files']:
        raise ValueError('JDK differs from audit/jdk-lock.json')
    return lock


def run_jdk(jdk, tool, arguments, *, timeout=60, require_empty_stderr=False):
    # Callers verify the entire JDK once before invoking this helper.
    options = JAVA_FLAGS if tool == 'java' else ['-J' + flag for flag in JAVA_FLAGS]
    if tool == 'javac':
        options += ['-extdirs', '', '-endorseddirs', '', '-encoding', 'UTF-8']
    result = subprocess.run([str(Path(jdk) / 'bin' / tool)] + options + list(arguments),
                            env=isolated_env(), capture_output=True, timeout=timeout)
    if result.returncode:
        # JVM/compiler messages can contain uncontrolled paths or payloads. Do not relay them.
        raise RuntimeError('Isolated ' + tool + ' failed (output withheld)')
    if require_empty_stderr and result.stderr:
        raise RuntimeError('Isolated ' + tool + ' produced unexpected stderr (output withheld)')
    return result.stdout.decode('utf-8')
