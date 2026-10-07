package atomicpaths;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.security.Permission;
import java.util.*;

/** Disposable pathname characterization; no Main, factory or real profiles. */
public final class PathObservation {
    static final class Guard extends SecurityManager {
        final Set<String> allowed; final List<String> writes=new ArrayList<>(); int denied;
        Guard(Set<String> allowed) { this.allowed=allowed; }
        SecurityException fail() { denied++;return new SecurityException("atomic-path-guard"); }
        public void checkWrite(String path) { if(!allowed.contains(path))throw fail(); writes.add(path); }
        public void checkDelete(String path) { throw fail(); }
        public void checkRead(String path) { if(path.contains("/Library/Preferences"))throw fail(); }
        public void checkPermission(Permission p) {
            if(p instanceof RuntimePermission && (p.getName().equals("preferences") || p.getName().equals("setSecurityManager")))throw fail();
            if(p instanceof FilePermission) {
                String actions=p.getActions();
                if(actions.contains("execute") || actions.contains("delete") || (actions.contains("write") && !allowed.contains(p.getName())))throw fail();
            }
        }
        public void checkExec(String p) { throw fail(); } public void checkExit(int s) { throw fail(); }
        public void checkConnect(String h,int p) { throw fail(); } public void checkConnect(String h,int p,Object c) { throw fail(); }
        public void checkListen(int p) { throw fail(); } public void checkMulticast(InetAddress a) { throw fail(); }
        public void checkLink(String p) { if(!Arrays.asList("java","zip","net","nio").contains(p))throw fail(); }
    }
    static String hex(String s) { StringBuilder b=new StringBuilder();for(int i=0;i<s.length();i++)b.append(String.format(Locale.ROOT,"%04x",(int)s.charAt(i)));return b.toString(); }
    public static void main(String[] args)throws Exception {
        File root=new File(System.getProperty("fixture.directory")).getCanonicalFile();
        if(!root.equals(new File(".").getCanonicalFile()))throw new AssertionError("atomic-path:cwd");
        URL jar=new File(System.getProperty("fixture.reference")).toURI().toURL();
        LinkedHashMap<String,String> paths=new LinkedHashMap<>();
        String absolute=root.getPath()+"/";
        paths.put("absolute",absolute+"absolute/profile");paths.put("relative","relative/profile");
        paths.put("dot",absolute+"dot/./profile");paths.put("dotdot",absolute+"dotdot/child/../profile");
        paths.put("missingdotdot",absolute+"missingdotdot/missing/../profile");
        paths.put("filedotdot",absolute+"filedotdot/blocker/../profile");
        paths.put("basedot",absolute+"basedot/.");paths.put("basedotdot",absolute+"basedotdot/child/..");
        paths.put("slashes",absolute+"slashes///profile");
        paths.put("composed",absolute+"composed/\u00e9");paths.put("decomposed",absolute+"decomposed/e\u0301");
        paths.put("nonbmp",absolute+"nonbmp/\ud83d\ude03");
        paths.put("high",absolute+"high/a\ud800b");paths.put("low",absolute+"low/a\udc00b");paths.put("reversed",absolute+"reversed/a\udc00\ud800b");
        paths.put("nul",absolute+"nul/a\0b");paths.put("empty","");
        paths.put("trailing",absolute+"trailing/profile/");
        paths.put("long255",absolute+"long255/"+String.join("",Collections.nCopies(255,"x")));
        paths.put("multi255",absolute+"multi255/"+String.join("",Collections.nCopies(85,"日")));
        paths.put("multi258",absolute+"multi258/"+String.join("",Collections.nCopies(86,"日")));
        paths.put("long256",absolute+"long256/"+String.join("",Collections.nCopies(256,"x")));
        Set<String> allowed=new HashSet<>();for(String path:paths.values()){allowed.add(path);allowed.add(new File(path).getPath());}
        Guard guard=new Guard(allowed);System.setSecurityManager(guard);
        if(!"UTF-8".equals(System.getProperty("sun.jnu.encoding")))throw new AssertionError("atomic-path:native-encoding");
        System.out.println("ENCODING\t"+System.getProperty("sun.jnu.encoding")+"\t"+System.getProperty("file.encoding"));
        try(URLClassLoader loader=new URLClassLoader(new URL[]{jar},null)) {
            Class<?> helper=Class.forName("compat.PreferenceIO",true,loader);
            if(!helper.getProtectionDomain().getCodeSource().getLocation().equals(jar))throw new AssertionError("atomic-path:origin");
            Method write=helper.getMethod("write",String.class,Object.class);
            for(Map.Entry<String,String> item:paths.entrySet()) {
                String result="SUCCESS";int start=guard.writes.size();
                try { write.invoke(null,item.getValue(),new LinkedHashMap<>()); }
                catch(InvocationTargetException failure) { result=failure.getCause().getClass().getName(); }
                if(guard.writes.size()!=start+1 || !guard.writes.get(start).equals(new File(item.getValue()).getPath()))throw new AssertionError("atomic-path:write-check");
                File folder=new File(root,item.getKey());String[] names=folder.list();if(names==null)throw new AssertionError("atomic-path:listing");Arrays.sort(names);
                String nio="SUCCESS";try{new File(item.getValue()).toPath();}catch(java.nio.file.InvalidPathException expected){nio=expected.getClass().getName();}
                String input=item.getValue().startsWith(absolute)?item.getValue().substring(absolute.length()):item.getValue();
                String normalized=new File(item.getValue()).getPath();if(normalized.startsWith(absolute))normalized=normalized.substring(absolute.length());
                System.out.print(item.getKey()+"\t"+result+"\t"+hex(input)+"\t"+hex(normalized)+"\t"+nio+"\t");
                for(int i=0;i<names.length;i++){if(i>0)System.out.print(",");System.out.print(hex(names[i]));}System.out.println();
            }
        }
        if(guard.denied!=0)throw new AssertionError("atomic-path:guard-denied");
    }
}
