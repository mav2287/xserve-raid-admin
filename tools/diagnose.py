#!/usr/bin/env python3
"""Allowlisted local diagnostics. Never launches Java or reads app preferences."""
import argparse
import json
import platform
import socket
from pathlib import Path
from baseline import tree
from audit_support import modes, digest


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
    file_modes = modes(output / 'RAID Admin.app')
    expected_jdk = json.loads((Path(__file__).resolve().parents[1] / 'audit/jdk-lock.json').read_text())
    jdk_matches = provenance.get('jdk', {}) == {k: v for k, v in expected_jdk.items() if k != 'files'}
    matches = files == provenance['files'] and file_modes == provenance.get('file_modes')
    # Do not relay arbitrary strings from manifests, environment, or preference stores.
    return {
        'apple_version': '1.5.1', 'compatibility_version': provenance['compatibility_version'] if provenance.get('compatibility_version') in ('1.5.1-modern.audit.1', '1.5.1-modern.audit.2') else 'unrecognized',
        'source_commit': provenance['source_commit'] if len(provenance.get('source_commit', '')) == 40 and all(c in '0123456789abcdef' for c in provenance['source_commit']) else 'unknown',
        'architecture': platform.machine(), 'macos': platform.mac_ver()[0],
        'bundle_tree_sha256': digest({'files': files, 'file_modes': file_modes}), 'matches_build_manifest': matches,
        'bundled_jre': 'absent', 'runtime_selected': 'not evaluated; application not launched',
        'build_jdk': {k: expected_jdk[k] for k in ('vendor', 'version', 'architecture', 'tree_sha256')} if jdk_matches else 'unrecognized build JDK',
        'interfaces': [name for _, name in socket.if_nameindex()],
        'controller_discovery': 'not run; no controller traffic generated', 'discovered_controllers': [],
        'event': safe_event({'operation': 'diagnose', 'result': 'pass' if matches and jdk_matches else 'fail'}),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    print(json.dumps(diagnose(parser.parse_args().build_directory), indent=2))
