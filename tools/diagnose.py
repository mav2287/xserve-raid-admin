#!/usr/bin/env python3
"""Allowlisted local diagnostics. Never launches Java or reads app preferences."""
import argparse
import json
import platform
import socket
from pathlib import Path
from baseline import sha, tree, tree_hash


def safe_event(event):
    """Emit enumerated metadata only; discard arbitrary messages, headers and bodies."""
    allowed = {
        'operation': {'build', 'diagnose', 'fixture'},
        'result': {'pass', 'fail', 'not-run'},
        'error_code': {'INPUT_HASH', 'TOOLCHAIN_HASH', 'ARTIFACT_CHANGED', 'NONE'},
    }
    return {key: value for key, value in event.items()
            if key in allowed and isinstance(value, str) and value in allowed[key]}


def diagnose(output):
    provenance = json.loads((output / 'provenance.json').read_text())
    files = tree(output / 'RAID Admin.app')
    # Do not relay arbitrary strings from manifests, environment, or preference stores.
    return {
        'apple_version': '1.5.1', 'compatibility_version': '1.5.1-modern.audit.1',
        'source_commit': provenance['source_commit'] if len(provenance.get('source_commit', '')) == 40 and all(c in '0123456789abcdef' for c in provenance['source_commit']) else 'unknown',
        'architecture': platform.machine(), 'macos': platform.mac_ver()[0],
        'bundle_tree_sha256': tree_hash(files), 'matches_build_manifest': files == provenance['files'],
        'bundled_jre': 'absent', 'runtime_selected': 'not evaluated; application not launched',
        'build_jdk': {'vendor': 'Amazon Corretto', 'version': '1.8.0_362', 'architecture': 'arm64'},
        'interfaces': [name for _, name in socket.if_nameindex()],
        'controller_discovery': 'not run; no controller traffic generated', 'discovered_controllers': [],
        'event': safe_event({'operation': 'diagnose', 'result': 'pass' if files == provenance['files'] else 'fail'}),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    print(json.dumps(diagnose(parser.parse_args().build_directory), indent=2))
