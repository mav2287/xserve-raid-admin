"""Independent full-class javap preservation check; no transformer imports."""
import re

POOL = [
 '#82 = Utf8 compat/PreferenceIO',
 '#83 = Class #82 // compat/PreferenceIO',
 '#84 = Utf8 write',
 '#85 = Utf8 (Ljava/lang/String;Ljava/lang/Object;)V',
 '#86 = NameAndType #84:#85 // write:(Ljava/lang/String;Ljava/lang/Object;)V',
 '#87 = Methodref #83.#86 // compat/PreferenceIO.write:(Ljava/lang/String;Ljava/lang/Object;)V',
]
OLD = '''7: new #21 // class java/io/OutputStreamWriter
10: dup
11: new #22 // class java/io/FileOutputStream
14: dup
15: new #6 // class java/io/File
18: dup
19: aload_0
20: getfield #4 // Field identifier:Ljava/lang/String;
23: invokespecial #7 // Method java/io/File."<init>":(Ljava/lang/String;)V
26: invokespecial #23 // Method java/io/FileOutputStream."<init>":(Ljava/io/File;)V
29: ldc #12 // String UTF-8
31: invokespecial #24 // Method java/io/OutputStreamWriter."<init>":(Ljava/io/OutputStream;Ljava/lang/String;)V
34: astore_2
35: aload_0
36: getfield #16 // Field dictionary:Ljava/util/Map;
39: aload_2
40: invokestatic #25 // Method com/apple/util/plist/PropertyListUtilities.writeXML:(Ljava/lang/Object;Ljava/io/Writer;)V
43: aload_2
44: invokevirtual #26 // Method java/io/OutputStreamWriter.flush:()V'''.splitlines()
NEW = '''7: aload_0
8: getfield #4 // Field identifier:Ljava/lang/String;
11: aload_0
12: getfield #16 // Field dictionary:Ljava/util/Map;
15: invokestatic #87 // Method compat/PreferenceIO.write:(Ljava/lang/String;Ljava/lang/Object;)V'''.splitlines()+[str(pc)+': nop' for pc in range(18,47)]

def check_disassembly(before,after):
    def lines(text):
        return [' '.join(line.split()) for line in text.splitlines()
                if not re.match(r'^(Classfile |  Last modified |  MD5 checksum |  SHA-256 checksum )',line)]
    old,new=lines(before),lines(after)
    if old.count('major version: 47')!=1 or new.count('major version: 47')!=1 or any('StackMapTable:' in line for line in old+new):raise ValueError('Preference legacy verification shape differs')
    for line in POOL:
        if new.count(line)!=1:raise ValueError('Preference helper pool differs')
        new.remove(line)
    marker='public void store();'
    if old.count(marker)!=1 or new.count(marker)!=1:raise ValueError('Preference store method differs')
    start=new.index(marker)
    for text in (old[old.index(marker):],new[start:]):
        if text.count('stack=7, locals=4, args_size=1')!=1:raise ValueError('Preference stack/local shape differs')
        for line in text:
            match=re.match(r'\d+: (?:if\w+|goto(?:_w)?|jsr(?:_w)?) (\d+)$',line)
            if match and 8<=int(match[1])<47:raise ValueError('Preference branch enters replaced window')
            if re.match(r'\d+: (?:tableswitch|lookupswitch)\b',line):raise ValueError('Unexpected preference switch control flow')
            if re.match(r'(?:4[7-9]|[5-9]\d|\d{3,}): (?:aload_2|aload 2)\b',line):raise ValueError('Preference writer local used after window')
        table=['7 47 50 Class java/lang/Exception','7 53 56 any','56 59 56 any']
        if any(text.count(row)!=1 for row in table):raise ValueError('Preference exception coverage differs')
    locations=[i for i in range(start,len(new)) if new[i:i+len(NEW)]==NEW]
    if len(locations)!=1:raise ValueError('Preference store instruction window differs')
    at=locations[0];new[at:at+len(NEW)]=OLD
    if old!=new:raise ValueError('Preference full-class preservation differs')
