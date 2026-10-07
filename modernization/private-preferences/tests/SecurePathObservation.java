package securefixture;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
import java.security.Permission;

/** Actual product helper, disposable cwd and bounded synthetic identifiers only. */
public final class SecurePathObservation {
    static void check(boolean v,String code){if(!v)throw new AssertionError("secure-path:"+code);}
    static Throwable invoke(Method m,String p)throws Exception{try{m.invoke(null,p,new LinkedHashMap<>());return null;}catch(InvocationTargetException e){return e.getCause();}}
    static final class Guard extends SecurityManager {
        final Set<String> paths;final String library;int denied;
        Guard(Set<String> p,String l){paths=p;library=l;}
        SecurityException fail(){denied++;return new SecurityException("secure-path-guard");}
        public void checkWrite(String p){if(!paths.contains(p))throw fail();}
        public void checkDelete(String p){if(!paths.contains(p))throw fail();}
        public void checkRead(String p){if(p.contains("/Library/Preferences"))throw fail();}
        public void checkPermission(Permission p){if(p instanceof RuntimePermission&&(p.getName().equals("preferences")||p.getName().equals("setSecurityManager")))throw fail();if(p instanceof FilePermission&&p.getActions().contains("execute"))throw fail();}
        public void checkConnect(String h,int p){throw fail();}public void checkConnect(String h,int p,Object c){throw fail();}public void checkListen(int p){throw fail();}public void checkMulticast(InetAddress a){throw fail();}public void checkExec(String p){throw fail();}public void checkExit(int s){throw fail();}
        public void checkLink(String p){if(!p.equals(library)&&!Arrays.asList("java","zip","net","nio","management","management_ext").contains(p))throw fail();}
    }
    static String suffix(String name){
        if(name.equals("dot"))return "./profile";if(name.equals("dotdot"))return "child/../profile";
        if(name.equals("missingdotdot"))return "missing/../profile";if(name.equals("filedotdot"))return "blocker/../profile";
        if(name.equals("basedot"))return ".";if(name.equals("basedotdot"))return "child/..";
        if(name.equals("slashes"))return "//profile";if(name.equals("trailing"))return "profile/";
        if(name.equals("composed"))return "é";if(name.equals("decomposed"))return "e\u0301";if(name.equals("nonbmp"))return "😃";
        if(name.equals("high"))return "a\ud800b";if(name.equals("low"))return "a\udc00b";if(name.equals("reversed"))return "a\udc00\ud800b";if(name.equals("nul"))return "a\0b";
        if(name.equals("long255"))return String.join("",Collections.nCopies(255,"x"));if(name.equals("long256"))return String.join("",Collections.nCopies(256,"x"));if(name.equals("multi255"))return String.join("",Collections.nCopies(85,"日"));if(name.equals("multi258"))return String.join("",Collections.nCopies(86,"日"));return "profile";
    }
    public static void main(String[] args)throws Exception{
        Path root=Paths.get(System.getProperty("fixture.directory")).toRealPath();check(Paths.get(".").toRealPath().equals(root),"cwd");
        String[] names={"absolute","relative","dot","dotdot","missingdotdot","filedotdot","basedot","basedotdot","slashes","composed","decomposed","nonbmp","high","low","reversed","nul","empty","trailing","long255","multi255","multi258","long256"};
        Map<String,String[]> inputs=new LinkedHashMap<>();Set<String> allowed=new HashSet<>();
        for(String n:names){String[] pair=new String[2];for(int i=0;i<2;i++){Path folder=root.resolve((i==0?"old-":"new-")+n);Files.createDirectory(folder);Files.setPosixFilePermissions(folder,PosixFilePermissions.fromString("rwx------"));if(n.equals("dotdot")||n.equals("basedotdot"))Files.createDirectory(folder.resolve("child"));if(n.equals("filedotdot"))Files.write(folder.resolve("blocker"),new byte[]{9,8,7});String path=folder+"/"+suffix(n);if(n.equals("empty"))path="";if(n.equals("relative"))path=root.relativize(folder)+"/profile";pair[i]=path;allowed.add(path);allowed.add(new File(path).getPath());}inputs.put(n,pair);}
        // Existing aliases stay in separate private fixture folders.
        String[][] aliases={{"Foo","foo"},{"é","e\u0301"},{"e\u0301","é"}};
        for(int i=0;i<aliases.length;i++){Path d=root.resolve("alias-"+i);Files.createDirectory(d);File f=new File(d.toFile(),aliases[i][0]);try(FileOutputStream out=new FileOutputStream(f)){out.write(new byte[]{9,8,7});}allowed.add(f.toString());allowed.add(new File(d.toFile(),aliases[i][1]).getPath());}
        for(int i=0;i<2;i++){Path d=root.resolve("hard-"+i);Files.createDirectory(d);Path target=d.resolve("hard-target");Files.write(target,new byte[]{9,8,7});Path other=i==0?d:d.resolve("other");if(i!=0)Files.createDirectory(other);Files.createLink(other.resolve("hard-backup"),target);allowed.add(target.toString());}
        // Keep the real parent below PATH_MAX; vary only the final component.
        Path parent=root.resolve("length");Files.createDirectory(parent);while(parent.toString().length()<900){int count=Math.min(80,899-parent.toString().length());if(count<1)break;parent=parent.resolve(String.join("",Collections.nCopies(count,"x")));Files.createDirectory(parent);}
        Map<Integer,String> limits=new LinkedHashMap<>();for(int size:new int[]{1023,1024,1100}){String path=parent+"/"+String.join("",Collections.nCopies(size-parent.toString().length()-1,"x"));check(path.length()==size,"length-bound");limits.put(size,path);allowed.add(path);}
        String library=System.getProperty("fixture.allowed.library");Guard guard=new Guard(allowed,library);System.setSecurityManager(guard);
        URL oldURL=new File(System.getProperty("fixture.reference")).toURI().toURL(),newURL=new File(System.getProperty("fixture.candidate")).toURI().toURL();
        try(URLClassLoader old=new URLClassLoader(new URL[]{oldURL},null);URLClassLoader modern=new URLClassLoader(new URL[]{newURL},null)){
            Class<?> a=Class.forName("compat.PreferenceIO",true,old),b=Class.forName("compat.PreferenceIO",true,modern);check(a.getProtectionDomain().getCodeSource().getLocation().equals(oldURL)&&b.getProtectionDomain().getCodeSource().getLocation().equals(newURL),"origin");Method before=a.getMethod("write",String.class,Object.class),after=b.getMethod("write",String.class,Object.class);
            Set<String> fail=new HashSet<>(Arrays.asList("missingdotdot","filedotdot","basedot","basedotdot","nul","empty","long256"));Set<String> strict=new HashSet<>(Arrays.asList("high","low","reversed"));
            for(Map.Entry<String,String[]> entry:inputs.entrySet()){
                String n=entry.getKey();Throwable x=invoke(before,entry.getValue()[0]),y=invoke(after,entry.getValue()[1]);check((x==null)==!fail.contains(n),"original-outcome");check((y==null)==!(fail.contains(n)||strict.contains(n)),"candidate-outcome");
                if(strict.contains(n))check(y instanceof IOException&&"atomic-path-encoding".equals(y.getMessage()),"strict-code");
                if(x==null&&!strict.contains(n)){Path p=new File(entry.getValue()[0]).toPath(),q=new File(entry.getValue()[1]).toPath();check(Arrays.equals(Files.readAllBytes(p),Files.readAllBytes(q)),"bytes");check(Files.getPosixFilePermissions(q).equals(PosixFilePermissions.fromString("rw-------")),"private");}
            }
            for(int i=0;i<aliases.length;i++){Path d=root.resolve("alias-"+i),f=d.resolve(aliases[i][0]);Object inode=Files.getAttribute(f,"unix:ino");check(invoke(after,new File(d.toFile(),aliases[i][1]).getPath())==null,"alias-save");check(!inode.equals(Files.getAttribute(f,"unix:ino")),"alias-replacement");String[] list=d.toFile().list();check(list.length==1,"alias-one-name");}
            for(int i=0;i<2;i++){
                Path d=root.resolve("hard-"+i),target=d.resolve("hard-target"),backup=(i==0?d:d.resolve("other")).resolve("hard-backup");Object inode=Files.getAttribute(target,"unix:ino");
                check(inode.equals(Files.getAttribute(backup,"unix:ino")),"hard-linked"); // Look up other link last.
                check(invoke(after,target.toString())==null,"hard-save");check(!inode.equals(Files.getAttribute(target,"unix:ino")),"hard-target-replaced");
                check(inode.equals(Files.getAttribute(backup,"unix:ino"))&&Arrays.equals(Files.readAllBytes(backup),new byte[]{9,8,7}),"hard-backup-retained");
                check(!Arrays.equals(Files.readAllBytes(target),new byte[]{9,8,7}),"hard-target-bytes");
            }
            for(Map.Entry<Integer,String> entry:limits.entrySet()){Throwable x=invoke(before,entry.getValue());if(x==null)Files.delete(new File(entry.getValue()).toPath());Throwable y=invoke(after,entry.getValue());check((x==null)==(entry.getKey()<1024)&&((y==null)==(x==null)),"path-max-parity");}
        }
        check(guard.denied==0,"guard");System.out.println("PASS secure paths; original_cases=22; aliases=3; hardlinks=2; path_limits=3; strict_encoding_fail_closed=true");
    }
}
