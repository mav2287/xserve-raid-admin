#!/usr/bin/env python3
"""Reproduce the immutable JAR's typed NumberFormatException handler inventory."""
import json
from pathlib import Path
import struct
import zipfile
from audit_support import ROOT, sha, verify_python
from baseline import verify_original
from class_patch import ClassFile, u2, u4


def main():
    verify_python()
    original = ROOT/'original/RAID_Admin_original.jar'
    verify_original(original)
    rows=[];methods=0
    with zipfile.ZipFile(original) as archive:
        names=sorted(name for name in archive.namelist() if name.endswith('.class'))
        for name in names:
            data=archive.read(name);cls=ClassFile(data)
            for method in cls.methods:
                for attribute,begin,end in method['attributes']:
                    if attribute!='Code':continue
                    methods+=1;at=begin+14+u4(data,begin+10)
                    for i in range(u2(data,at)):
                        start,stop,target,kind=struct.unpack_from('>HHHH',data,at+2+i*8)
                        if not kind:continue
                        tag,value=cls.pool[kind]
                        if tag!=7:raise ValueError('Exception handler catch type must be Class')
                        if cls.text(u2(value,0))=='java/lang/NumberFormatException':
                            rows.append({'class':name,'method':method['name'],'descriptor':method['descriptor'],
                                         'range':[start,stop],'handler':target})
    verify_original(original)
    print(json.dumps({'original_jar_sha256':sha(original),'class_count':len(names),'code_method_count':methods,
        'filter':'Typed java/lang/NumberFormatException entries only; all class Code handler tables scanned',
        'generator_sha256':sha(Path(__file__)),
        'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/class_patch.py',ROOT/'tools/baseline.py',ROOT/'tools/audit_support.py']},
        'handlers':rows,'limits':'Static inventory only; does not trace reflective/dynamic invocation or establish CLI lifecycle behavior.'},indent=2))


if __name__=='__main__':main()
