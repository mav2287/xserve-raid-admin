#!/usr/bin/env python3
"""Offline known-package check only; never invokes the application or transmitter."""
import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass


@dataclass(frozen=True)
class Image:
    role: str
    path: str
    size: int
    sha256: str
    version: str


PACKAGE_SHA256 = '32c077ea0ec50a944a996b72978f6d7b9585d17603da847fd4317ebc364dd9a7'
PACKAGE_SIZE = 929851
CONTAINER_SHA256 = '21cf7a8c4e82b925bf9df3d6ea982569bfd24148773ad8dad47f6ddc698ae2c7'
CONTAINER_SIZE = 8052021
ACQUISITION_MARKER_SHA256 = '27b6679d1ada1d9cef3d242977524832fb9b4ede7d285c7e953cf0dc11ac2859'
CONTAINER_MEMBER = 'RAID Admin 1.5.1/firmware-1.5.1-1.51.xfb'
MANIFEST_SHA256 = '76486a0b542258a2ec7c7dd8f02de1ec30152dd211c8d39c7cce69ede1f7136c'
IMAGES = (
    Image('coprocessor', 'coprocessor/updateROM.bin', 1572900,
          'f0c16dbd926a333d0c94fcb0c10c560e7e783c664c33bdc062536ef29fbadff6', '1.5.1'),
    Image('raid-controller', 'raid-controller/updateROM.bin', 910360,
          '1ad6561433cacad5ee1f30aed35b4300d102a883cec3da03047d75e5bccf8851', '1.51c'),
)
MEMBERS = (
    ('META-INF/MANIFEST.MF', 362, 8, MANIFEST_SHA256),
    ('coprocessor/', 0, 8, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
    ('raid-controller/', 0, 8, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
) + tuple((image.path, image.size, 8, image.sha256) for image in IMAGES)
CODES = frozenset(('TYPE_REJECTED', 'NOT_REGULAR_FILE', 'SIZE_REJECTED',
                   'READ_FAILED', 'UNRECOGNIZED_PACKAGE', 'ARGUMENT_REJECTED'))


class PreflightError(ValueError):
    def __init__(self, code):
        if code not in CODES:
            raise ValueError('Invalid preflight code')
        self.code = code
        super().__init__(code)


def read_snapshot(path):
    """Bound a local regular-file read; no containment or hostile-filesystem claim."""
    try:
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode):
            raise PreflightError('NOT_REGULAR_FILE')
        if before.st_size > PACKAGE_SIZE:
            raise PreflightError('SIZE_REJECTED')
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise PreflightError('NOT_REGULAR_FILE')
            if opened.st_size > PACKAGE_SIZE:
                raise PreflightError('SIZE_REJECTED')
            data = bytearray()
            while len(data) <= PACKAGE_SIZE:
                part = os.read(descriptor, min(65536, PACKAGE_SIZE + 1 - len(data)))
                if not part:
                    break
                data.extend(part)
            if len(data) > PACKAGE_SIZE:
                raise PreflightError('SIZE_REJECTED')
            if len(data) != opened.st_size:
                raise PreflightError('READ_FAILED')
            return bytes(data)
        finally:
            os.close(descriptor)
    except PreflightError:
        raise
    except (OSError, ValueError, TypeError):
        raise PreflightError('READ_FAILED') from None


def validate_snapshot(snapshot):
    """Hash before any interpretation. Unknown ZIPs are never parsed or inflated."""
    if type(snapshot) is not bytes:
        raise PreflightError('TYPE_REJECTED')
    if len(snapshot) > PACKAGE_SIZE:
        raise PreflightError('SIZE_REJECTED')
    if len(snapshot) != PACKAGE_SIZE or hashlib.sha256(snapshot).hexdigest() != PACKAGE_SHA256:
        raise PreflightError('UNRECOGNIZED_PACKAGE')
    return {
        'result': 'KNOWN_PACKAGE',
        'snapshot_sha256': PACKAGE_SHA256,
        'snapshot_size': PACKAGE_SIZE,
        'reference_acquisition': {'container_sha256': CONTAINER_SHA256, 'container_size': CONTAINER_SIZE,
                        'member': CONTAINER_MEMBER, 'marker_sha256': ACQUISITION_MARKER_SHA256},
        'images': [dict(role=image.role, path=image.path, size=image.size,
                        sha256=image.sha256, version=image.version,
                        firmware_date='12/08/2006') for image in IMAGES],
        'optional_full_image': 'absent',
        'hardware_compatibility': 'unconfirmed',
        'signature_verification': 'unconfirmed',
        'transmission': 'not performed',
        'scope': 'Byte-identical to the acquired Apple reference; provenance describes that reference, not the input source. Offline foundation only.',
    }


class FixedArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({'result': 'REJECTED', 'code': 'ARGUMENT_REJECTED'}))
        raise SystemExit(2)


def main():
    parser = FixedArgumentParser(description=__doc__)
    parser.add_argument('package', help='Local firmware file; only the pinned Apple package is recognized')
    args = parser.parse_args()
    try:
        result = validate_snapshot(read_snapshot(args.package))
    except PreflightError as failure:
        print(json.dumps({'result': 'REJECTED', 'code': failure.code}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
