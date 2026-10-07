"""Independent complete javap comparison; imports no bytecode transformer."""
import re

def check_disassembly(before, after):
    def headers(text):
        return '\n'.join(line for line in text.splitlines() if not re.match(r'^(Classfile |  Last modified |  MD5 checksum |  SHA-256 checksum )', line))
    old, new = headers(before), headers(after)
    pool = [r'^\s+#1184 = Utf8\s+<redacted>$', r'^\s+#1185 = String\s+#1184\s+// <redacted>$']
    for pattern in pool:
        new, count = re.subn(pattern + r'\n', '', new, flags=re.M)
        if count != 1: raise ValueError('Independent model pool differs')
    for pc, index, name in ((156, 74, 'monitoringPassword'), (190, 75, 'managementPassword')):
        pattern = r'^(\s+)' + str(pc) + r': ldc_w\s+#1185\s+// String <redacted>\n\s+' + str(pc+3) + r': nop$'
        replacement = r'\g<1>' + str(pc) + ': aload_0\n' + ' ' * 7 + str(pc+1) + ': getfield      #' + str(index) + '                 // Field ' + name + ':Ljava/lang/String;'
        # Compare instructions canonically below, so alignment is immaterial.
        new, count = re.subn(pattern, replacement, new, flags=re.M)
        if count != 1: raise ValueError('Independent model instruction window differs')
    canonical = lambda text: [' '.join(line.split()) for line in text.splitlines()]
    if canonical(old) != canonical(new):
        raise ValueError('Independent full-class model disassembly differs')
    for index in (74, 75):
        count = lambda text: len(re.findall(r'^\s+\d+: getfield\s+#'+str(index)+r'\s', text, re.M))
        if count(before) != count(after)+1: raise ValueError('Diagnostic field-read count differs')
    count_saved = lambda text: len(re.findall(r'^\s+\d+: (?:getfield|putfield)\s+#76\s', text, re.M))
    if count_saved(before) != count_saved(after): raise ValueError('Saved flag instructions differ')
