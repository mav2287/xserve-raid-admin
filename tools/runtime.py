#!/usr/bin/env python3
"""Fetch or verify exact vendor runtimes in a local cache; never install them."""
import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

from audit_support import ROOT, digest, modes, sha, tree, isolated_env


def extract_archive(archive, destination, expected_root):
    """Only ordinary files/directories under one reviewed root; no archive links."""
    with tarfile.open(archive) as tar:
        seen = set()
        for member in tar.getmembers():
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts or
                    path.parts[0] != expected_root or str(path).casefold() in seen or
                    not (member.isfile() or member.isdir()) or member.mode & 0o7022):
                raise ValueError('Unsafe runtime archive entry')
            seen.add(str(path).casefold())
        tar.extractall(destination, filter='data')
        # Python's data filter adds owner-write permission to read-only files.
        # Restore the reviewed vendor's exact ordinary permission bits.
        for member in tar.getmembers():
            if member.isfile() or member.isdir():
                (Path(destination) / member.name).chmod(member.mode)


def runtime_manifest():
    return json.loads((ROOT / 'audit/runtime-lock.json').read_text())


def verify_runtime(root, record):
    if tree(root) != record['files'] or modes(root) != record['file_modes']:
        raise ValueError('Runtime differs from reviewed vendor contents or modes')
    if digest({'files': record['files'], 'file_modes': record['file_modes']}) != record['tree_sha256']:
        raise ValueError('Invalid runtime lock digest')
    if 'directory_modes' in record and directory_modes(root) != record['directory_modes']:
        raise ValueError('Runtime directory modes differ from vendor archive')
    if record.get('signature_team'):
        requirement = '=anchor apple generic and certificate leaf[subject.OU] = "' + record['signature_team'] + '"'
        result = subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', '-R', requirement, str(root)],
                                env=isolated_env(), capture_output=True, timeout=30)
        detail = subprocess.run(['/usr/bin/codesign', '-dv', '--verbose=4', str(root)],
                                env=isolated_env(), capture_output=True, timeout=30)
        lines = detail.stderr.decode('utf-8').splitlines()
        if (result.returncode or detail.returncode or
                'TeamIdentifier=' + record['signature_team'] not in lines or
                'Identifier=' + record['signature_identifier'] not in lines):
            raise ValueError('Vendor runtime signature or identity does not verify')


def directory_modes(root):
    root = Path(root)
    return {str(p.relative_to(root)): p.stat().st_mode & 0o7777
            for p in [root] + sorted(root.rglob('*')) if p.is_dir() and not p.is_symlink()}


def obtain_runtime(cache, architecture, *, fetch=False):
    record = runtime_manifest()['architectures'][architecture]
    cache = Path(cache).absolute()
    cache.mkdir(parents=True, exist_ok=True)
    if cache.is_symlink():
        raise ValueError('Runtime cache must not be a symlink')
    archive = cache / record['archive_name']
    if archive.is_symlink():
        raise ValueError('Runtime archive must not be a symlink')
    if not archive.exists():
        if not fetch:
            raise ValueError('Pinned archive missing; explicitly use --fetch to download it')
        if not record['archive_url'].startswith('https://corretto.aws/downloads/resources/'):
            raise ValueError('Unexpected runtime download origin')
        with tempfile.NamedTemporaryFile(dir=cache, prefix='download-', delete=False) as out:
            temporary = Path(out.name)
            try:
                with urllib.request.urlopen(record['archive_url'], timeout=60) as response:
                    if not response.url.startswith('https://corretto.aws/'):
                        raise ValueError('Unexpected runtime redirect origin')
                    shutil.copyfileobj(response, out)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            if sha(temporary) != record['archive_sha256']:
                raise ValueError('Runtime archive checksum mismatch')
            temporary.rename(archive)
        finally:
            temporary.unlink(missing_ok=True)
    if sha(archive) != record['archive_sha256']:
        raise ValueError('Runtime archive checksum mismatch')
    destination = cache / architecture
    root = destination / record['archive_root']
    if destination.is_symlink():
        raise ValueError('Runtime destination must not be a symlink')
    if destination.exists():
        verify_runtime(root, record)
        return root
    with tempfile.TemporaryDirectory(dir=cache, prefix='extract-') as tmp:
        extract_archive(archive, tmp, record['archive_root'])
        verify_runtime(Path(tmp) / record['archive_root'], record)
        Path(tmp).rename(destination)
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--architecture', required=True, choices=['aarch64', 'x64'])
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    obtain_runtime(args.cache, args.architecture, fetch=args.fetch)
    print('PASS pinned vendor runtime archive, files and modes verified; no installation or execution')
