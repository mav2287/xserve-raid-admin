"""One exact information-view invocation substitution; full original reversal."""
import hashlib
from class_patch import ClassFile, word
from sync_ownership_patch import compose, method_code, pool_boundary, utf

ENTRY = 'com/apple/xsr/SystemInfoPane$5.class'
HELPER = 'compat/ArrayInfoSelection.class'
PIN = '1ec5002833994756edfe1b7d04f74bf7d39c4c02398fad2af584f28188f2ddce'
COUNT = 85
METHOD = ('propertyChange', '(Ljava/beans/PropertyChangeEvent;)V')


def extra():
    return (utf('compat/ArrayInfoSelection') + b'\x07' + word(COUNT)
            + utf('setArrayIndex') + utf('(Lcom/apple/xsr/DriveSelectionPanel;I)V')
            + b'\x0c' + word(COUNT + 2) + word(COUNT + 3)
            + b'\x0a' + word(COUNT + 1) + word(COUNT + 4))


def plan(data):
    if hashlib.sha256(data).hexdigest() != PIN:
        raise ValueError('Exact original information listener required')
    cls = ClassFile(data); start, end = method_code(cls, *METHOD); at = start + 14 + 30
    if cls.pool_count != COUNT or data[at:at+3] != b'\xb6\x00\x08':
        raise ValueError('Original information invocation differs')
    return compose(data, cls, [(at, at+3, b'\xb8' + word(COUNT + 5))], COUNT + 6, extra())


def normalize(data):
    cls = ClassFile(data); start, end = method_code(cls, *METHOD); at = start + 14 + 30
    cut = pool_boundary(cls, COUNT)
    if (cls.pool_count != COUNT + 6 or data[cut:cls.pool_end] != extra()
            or data[at:at+3] != b'\xb8' + word(COUNT + 5)):
        raise ValueError('Exact information helper invocation differs')
    original = compose(data, cls, [(at, at+3, b'\xb6\x00\x08')], COUNT, keep_end=cut)
    if hashlib.sha256(original).hexdigest() != PIN or plan(original) != data:
        raise ValueError('Information listener differs outside the single invocation')
    return original


def verify_delta(before, after, helper):
    if (set(after) - set(before) != {HELPER} or set(before) - set(after)
            or {n for n in before if before[n] != after[n]} != {ENTRY}
            or after[HELPER] != helper or helper[6:8] != b'\x00\x34'
            or normalize(after[ENTRY]) != before[ENTRY]):
        raise ValueError('Unexpected application delta')
