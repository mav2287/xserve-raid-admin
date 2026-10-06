#!/usr/bin/env python3
"""Opt-in offline verification of the known-package gate and reviewed metadata."""
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import zipfile
import zlib
from unittest.mock import patch
from audit_support import ROOT, sha, verify_python, isolated_env
from check_firmware_archives import official_fixture, OFFICIAL_SHA256, OFFICIAL_ARCHIVE_SHA256
from firmware_preflight import (FixedArgumentParser, PACKAGE_SHA256, PACKAGE_SIZE,
    MANIFEST_SHA256, MEMBERS, IMAGES, ACQUISITION_MARKER_SHA256,
    CONTAINER_SHA256, CONTAINER_SIZE, CONTAINER_MEMBER, read_snapshot, validate_snapshot, PreflightError)


def main():
    parser=FixedArgumentParser(description=__doc__)
    parser.add_argument('--official-firmware',type=Path)
    args=parser.parse_args();verify_python()
    anchor=subprocess.check_output(['/usr/bin/git','rev-parse','HEAD'],cwd=ROOT,env=isolated_env(),text=True).strip()
    dirty=bool(subprocess.check_output(['/usr/bin/git','status','--porcelain'],cwd=ROOT,env=isolated_env()))
    paths=[ROOT/name for name in ('tools/firmware_preflight.py','tools/check_firmware_preflight.py',
           'tools/check_firmware_archives.py','tools/audit_support.py','audit/official-firmware-fixtures.json',
           'audit/apple-distribution-acquisition.json','tests/java/OfficialFirmwareProbe.java',
           'tests/test_firmware_preflight.py','audit/python-lock.json')]
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    reference=json.loads((ROOT/'audit/official-firmware-fixtures.json').read_text())['official_package']
    reference_acquisition=json.loads((ROOT/'audit/apple-distribution-acquisition.json').read_text())
    table={name:{'size':size,'sha256':digest,'compression':method} for name,size,method,digest in MEMBERS}
    if (reference['sha256']!=PACKAGE_SHA256 or reference['container_sha256']!=CONTAINER_SHA256 or
        reference['acquisition_marker_sha256']!=ACQUISITION_MARKER_SHA256 or reference['entries']!=table or
        PACKAGE_SHA256!=OFFICIAL_SHA256 or CONTAINER_SHA256!=OFFICIAL_ARCHIVE_SHA256 or
        CONTAINER_MEMBER!='RAID Admin 1.5.1/firmware-1.5.1-1.51.xfb' or
        reference_acquisition['archive_sha256']!=CONTAINER_SHA256 or
        reference_acquisition['archive_size']!=CONTAINER_SIZE or
        reference_acquisition['selected'][CONTAINER_MEMBER]['sha256']!=PACKAGE_SHA256 or
        reference_acquisition['selected'][CONTAINER_MEMBER]['size']!=PACKAGE_SIZE or
        [m[0] for m in MEMBERS]!=['META-INF/MANIFEST.MF','coprocessor/','raid-controller/',
            'coprocessor/updateROM.bin','raid-controller/updateROM.bin']):
        raise ValueError('Frozen reference metadata differs from reviewed evidence')
    observations={'frozen_metadata_matches_reviewed_record':True,'official_package':'not-run: opt-in public cache not provided'}
    if args.official_firmware is not None:
        path=args.official_firmware
        rows=official_fixture(path)  # Checks the completed public acquisition chain.
        snapshot=read_snapshot(path)
        with patch.object(socket,'socket',side_effect=AssertionError('Sockets prohibited')), \
             patch.object(socket,'create_connection',side_effect=AssertionError('Connect prohibited')), \
             patch.object(zipfile,'ZipFile',side_effect=AssertionError('Runtime parsing prohibited')), \
             patch.object(zlib,'decompress',side_effect=AssertionError('Runtime inflate prohibited')), \
             patch.object(zlib,'decompressobj',side_effect=AssertionError('Runtime inflate prohibited')):
            accepted=validate_snapshot(snapshot)
            if accepted['result']!='KNOWN_PACKAGE' or accepted['snapshot_sha256']!=PACKAGE_SHA256:
                raise ValueError('Known-package gate differs')
            for position in (0,218,342,657677,len(snapshot)-22):
                changed=bytearray(snapshot);changed[position]^=1
                try:validate_snapshot(bytes(changed))
                except PreflightError as rejected:
                    if rejected.code!='UNRECOGNIZED_PACKAGE':raise ValueError('Mutation gate differs')
                else:raise ValueError('Changed package accepted')
            for changed in (snapshot[:-1],b'x'+snapshot,snapshot+b'x'):
                try:validate_snapshot(changed)
                except PreflightError as rejected:
                    if rejected.code not in ('UNRECOGNIZED_PACKAGE','SIZE_REJECTED'):raise ValueError('Layout mutation gate differs')
                else:raise ValueError('Changed package accepted')
        marker=(path.parent/'acquisition.json').read_bytes()
        acquisition=json.loads(marker)
        if (len(snapshot)!=PACKAGE_SIZE or hashlib.sha256(marker).hexdigest()!=ACQUISITION_MARKER_SHA256 or
            acquisition['archive_sha256']!=CONTAINER_SHA256 or acquisition['archive_size']!=CONTAINER_SIZE or
            acquisition['selected'][CONTAINER_MEMBER]['sha256']!=PACKAGE_SHA256 or
            acquisition['selected'][CONTAINER_MEMBER]['size']!=PACKAGE_SIZE or
            (path.parent/'archive.tar.gz').stat().st_size!=CONTAINER_SIZE):
            raise ValueError('Acquisition fixture differs from reviewed metadata table')
        with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
            if archive.namelist()!=[m[0] for m in MEMBERS]:raise ValueError('Known member order differs')
            for name,size,method,digest in MEMBERS:
                entry=archive.getinfo(name);data=archive.read(entry)
                if (len(data),entry.file_size,entry.compress_type,hashlib.sha256(data).hexdigest())!=(size,size,method,digest):
                    raise ValueError('Known table differs from immutable member data')
                if rows[name] != {'size':size,'sha256':digest,'compression':method}:
                    raise ValueError('Known table differs from acquisition fixture')
            manifest=archive.read('META-INF/MANIFEST.MF')
            if hashlib.sha256(manifest).hexdigest()!=MANIFEST_SHA256:raise ValueError('Manifest pin differs')
            for image in IMAGES:
                block=('Name: '+image.path+'\r\nfirmware-version: '+image.version+'\r\nfirmware-date: 12/08/2006\r\n\r\n').encode('ascii')
                key=('xserveraid-'+image.role+'-update-image: '+image.path+'\r\n').encode('ascii')
                if block not in manifest or key not in manifest:raise ValueError('Known manifest metadata differs')
            if b'xserveraid-coprocessor-full-image' in manifest:raise ValueError('Optional image observation differs')
        expected={'result':'KNOWN_PACKAGE','snapshot_sha256':acquisition['selected'][CONTAINER_MEMBER]['sha256'],
            'snapshot_size':acquisition['selected'][CONTAINER_MEMBER]['size'],
            'reference_acquisition':{'container_sha256':acquisition['archive_sha256'],
                'container_size':acquisition['archive_size'],'member':CONTAINER_MEMBER,
                'marker_sha256':hashlib.sha256(marker).hexdigest()},
            'images':[{'role':role,'path':name,'size':rows[name]['size'],'sha256':rows[name]['sha256'],
                'version':version,'firmware_date':'12/08/2006'} for role,name,version in
                [('coprocessor','coprocessor/updateROM.bin','1.5.1'),('raid-controller','raid-controller/updateROM.bin','1.51c')]],
            'optional_full_image':'absent','hardware_compatibility':'unconfirmed','signature_verification':'unconfirmed',
            'transmission':'not performed',
            'scope':'Byte-identical to the acquired Apple reference; provenance describes that reference, not the input source. Offline foundation only.'}
        if accepted!=expected:raise ValueError('Known output differs from verified reference metadata')
        if read_snapshot(path)!=snapshot:raise ValueError('Known cache changed during check')
        observations={'frozen_metadata_matches_reviewed_record':True,'official_package':accepted,
                      'mutation_gates':8,'mutation_scope':'Five arbitrary byte positions and prepend/append/truncate gates, not structural ZIP validation.',
                      'runtime_zip_inflate_socket_calls':0,
                      'independent_snapshot_members_match_frozen_table':True}
    if sources!={str(p.relative_to(ROOT)):sha(p) for p in paths}:raise ValueError('Checker sources changed')
    print(json.dumps({'fixture_commit':anchor,'fixture_dirty':dirty,'sources':sources,'observations':observations,
        'limits':'Offline strict known-package foundation only. Unknown snapshots never parse/decompress. Member inspection is a separate fixture over the validated public snapshot, not generic ZIP validation. No updater, transmission, controller compatibility, signature, UI or send-time snapshot binding qualification. Socket mocks guard reviewed Python calls, not a hostile-code or filesystem sandbox.'},indent=2))


if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps({'result':'REJECTED','code':'INSPECTION_FAILED'}))
        raise SystemExit(1)
