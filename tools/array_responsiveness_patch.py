"""Exact reversible information-only simulated-click substitutions over audit29."""
import hashlib
from class_patch import ClassFile, word
from sync_ownership_patch import compose, method_code, pool_boundary, utf

HELPERS = {'compat/InfoSelectionClick.class'}
SPECS = {
 'com/apple/xsr/SystemInfoPane$4.class': ('44e1bfedbc79a2164f17f7291f1ab2d974844c7cd7a49abec3ef29699373848e',51,'propertyChange','(Ljava/beans/PropertyChangeEvent;)V',[(23,7),(41,7)],'viewMode'),
 'com/apple/xsr/ArraySelectionPanel$4.class': ('20e1158ae48790cacc2b9c8b1460c951549493218770523e5bd948b4a5b81d3f',38,'mouseReleased','(Ljava/awt/event/MouseEvent;)V',[(17,4)],'arrayRow'),
}


def extra(count, name):
    return (utf('compat/InfoSelectionClick')+b'\x07'+word(count)+utf(name)
            +utf('(Ljavax/swing/AbstractButton;)V')+b'\x0c'+word(count+2)+word(count+3)
            +b'\x0a'+word(count+1)+word(count+4))


def edits(data, cls, spec, forward):
    pin,count,method,descriptor,calls,name=spec
    start,_=method_code(cls,method,descriptor)
    result=[]
    for pc, index in calls:
        old=b'\xb6'+word(index);new=b'\xb8'+word(count+5)
        at=start+14+pc
        if data[at:at+3] != (old if forward else new): raise ValueError('Exact call site differs')
        result.append((at,at+3,new if forward else old))
    return result


def plan(entry, data):
    spec=SPECS[entry];pin,count,*_=spec;cls=ClassFile(data)
    if hashlib.sha256(data).hexdigest()!=pin or cls.pool_count!=count: raise ValueError('Exact audit29 class required')
    return compose(data,cls,edits(data,cls,spec,True),count+6,extra(count,spec[-1]))


def normalize(entry, data):
    spec=SPECS[entry];pin,count,*_=spec;cls=ClassFile(data);cut=pool_boundary(cls,count)
    if cls.pool_count!=count+6 or data[cut:cls.pool_end]!=extra(count,spec[-1]): raise ValueError('Exact helper pool required')
    original=compose(data,cls,edits(data,cls,spec,False),count,keep_end=cut)
    if hashlib.sha256(original).hexdigest()!=pin or plan(entry,original)!=data: raise ValueError('Unexpected class delta')
    return original


def verify_delta(before, after, helpers):
    if set(helpers)!=HELPERS or set(after)-set(before)!=HELPERS or set(before)-set(after) or {n for n in before if before[n]!=after[n]}!=set(SPECS): raise ValueError('Unexpected JAR inventory delta')
    for entry in SPECS:
        if normalize(entry,after[entry])!=before[entry]: raise ValueError('JAR inverse differs')
    for entry in HELPERS:
        if after[entry]!=helpers[entry] or helpers[entry][6:8]!=b'\x00\x34': raise ValueError('Unexpected helper')
