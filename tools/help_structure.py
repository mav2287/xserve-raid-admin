"""Independent disassembly check; intentionally does not import the transformer."""
import re
EXPECTED={
 'com/apple/xsr/RaidAdmin$HelpListener.class':(5,4,36),
 'com/apple/xsr/SystemMonitorController$UnsupportedOperationDialog.class':(14,68,283),
}
def check_operand(entry,before,after):
    pc,old,new=EXPECTED[entry]
    ops=lambda text:[(int(p),' '.join(o.split())) for p,o in re.findall(r'^\s+(\d+):\s+(.*)$',text,re.M)]
    a,b=ops(before),ops(after)
    differences=[(x,y) for x,y in zip(a,b) if x!=y]
    expected=((pc,'invokestatic #'+str(old)+' // Method edu/stanford/ejalbert/BrowserLauncher.openURL:(Ljava/lang/String;)V'),(pc,'invokestatic #'+str(new)+' // Method compat/HelpLauncher.openURL:(Ljava/lang/String;)V'))
    if not a or len(a)!=len(b) or differences!=[expected]:raise ValueError('Independent Help instructions differ')
    # Existing handlers and stack/local frames must survive unchanged.
    metadata=lambda text:re.findall(r'^\s+(?:stack=.+|from\s+to\s+target\s+type|\d+\s+\d+\s+\d+\s+Class .+)$',text,re.M)
    if metadata(before)!=metadata(after):raise ValueError('Help frames/handlers differ')
