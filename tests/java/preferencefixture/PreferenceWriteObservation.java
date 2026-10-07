import fixture.FixtureIdentity;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
import java.lang.management.*;

public final class PreferenceWriteObservation {
    static void check(boolean ok){check(ok,"general");}
    static void check(boolean ok,String code){if(!ok)throw new AssertionError("preference write differential: "+code);}
    static class Backend {
        final Object value; final Class<?> base; final Method store,load;
        Backend(ClassLoader loader,Path path)throws Exception {
            Class<?> type=Class.forName("com.apple.util.prefs.FileBasedPreferences",true,loader);
            base=type.getSuperclass();value=type.getConstructor(String.class).newInstance(path.toString());store=type.getMethod("store");load=type.getMethod("load");
        }
        void state(Map dictionary,int changes)throws Exception {Field f=base.getDeclaredField("dictionary");f.setAccessible(true);f.set(value,dictionary);f=base.getDeclaredField("changeCount");f.setAccessible(true);f.setInt(value,changes);}
        int count()throws Exception{Field f=base.getDeclaredField("changeCount");f.setAccessible(true);return f.getInt(value);}
        void save()throws Exception{store.invoke(value);}
    }
    static long gc(){long n=0;for(GarbageCollectorMXBean b:ManagementFactory.getGarbageCollectorMXBeans()){check(b.getCollectionCount()>=0);n+=b.getCollectionCount();}return n;}
    static Set<PosixFilePermission> perms(String p){return PosixFilePermissions.fromString(p);}
    static Map good(int kind){Map m=new LinkedHashMap();
        if(kind==1)m.put("unicode","日本語 é 😃 &<>\" '\n");
        if(kind==2){ArrayList a=new ArrayList();a.add(Long.valueOf(-1234567890123L));a.add(Integer.valueOf(42));a.add(Boolean.TRUE);a.add(new byte[]{0,1,2});a.add(new Date(123456789L));a.add(new LinkedHashMap());m.put("nested",a);}
        if(kind==3)m.put("large",String.join("",Collections.nCopies(40000,"ü<&")));
        if(kind==4)m.put("surrogates","a\ud800b\udc00c\u0001");
        return m;
    }
    static Map bad(boolean large){Map m=new LinkedHashMap();if(large)m.put("prefix",String.join("",Collections.nCopies(40000,"x")));m.put(Integer.valueOf(5),"bad-key");return m;}
    static Map error(){return new LinkedHashMap(){public int size(){throw new AssertionError("synthetic serialization error");}};}
    static Map interrupted(){return new LinkedHashMap(){public int size(){Thread.currentThread().interrupt();return super.size();}};}
    public static void main(String[]args)throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")));FixtureIdentity.verify();
        Path root=Paths.get(System.getProperty("fixture.directory")).toRealPath();
        URL reference=new File(System.getProperty("fixture.reference")).toURI().toURL();
        try(URLClassLoader original=new URLClassLoader(new URL[]{reference},null)){
            // Reference loader contains only the immutable audit26 JAR, no shadows.
            Class<?> r=Class.forName("com.apple.util.prefs.FileBasedPreferences",false,original);
            check(new File(r.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile().equals(new File(reference.toURI()).getCanonicalFile()));
            PreferenceLifetimeObservation.Guard guard=new PreferenceLifetimeObservation.Guard(root);System.setSecurityManager(guard);
            ClassLoader candidate=PreferenceWriteObservation.class.getClassLoader();int cases=0;
            for(int kind=0;kind<7;kind++){
                Map m=kind<5?good(kind):bad(kind==6);Path a=root.resolve("original-"+kind),b=root.resolve("candidate-"+kind);
                Backend old=new Backend(original,a),now=new Backend(candidate,b);old.state(m,7);now.state(m,7);old.save();now.save();
                check(Arrays.equals(Files.readAllBytes(a),Files.readAllBytes(b)),"bytes-kind-"+kind);check(old.count()==7 && now.count()==7,"count-kind-"+kind);
                check(Files.getPosixFilePermissions(b).equals(Files.getPosixFilePermissions(a)),"mode-kind-"+kind);cases++;
            }
            Path existing=root.resolve("existing");Files.write(existing,new byte[500000]);Files.setPosixFilePermissions(existing,perms("rw-r--r--"));
            Path referenceExisting=root.resolve("reference-existing");Files.write(referenceExisting,new byte[500000]);Files.setPosixFilePermissions(referenceExisting,perms("rw-r--r--"));Backend oldExisting=new Backend(original,referenceExisting);oldExisting.state(good(1),3);oldExisting.save();check(Arrays.equals(Files.readAllBytes(referenceExisting),Files.readAllBytes(root.resolve("original-1"))),"original-truncation");
            Backend now=new Backend(candidate,existing);now.state(good(1),3);now.save();check(Files.getPosixFilePermissions(existing).equals(perms("rw-r--r--")),"existing-mode");check(now.count()==3,"existing-count");check(Arrays.equals(Files.readAllBytes(existing),Files.readAllBytes(root.resolve("original-1"))),"existing-truncation");cases++;
            Path target=root.resolve("target"),link=root.resolve("linked");byte[] sentinel={1,2,3};Files.write(target,sentinel);Files.createSymbolicLink(link,target);
            Path oldTarget=root.resolve("reference-target"),oldLink=root.resolve("reference-link");Files.write(oldTarget,sentinel);Files.createSymbolicLink(oldLink,oldTarget);Backend oldLinked=new Backend(original,oldLink);oldLinked.state(good(1),3);oldLinked.save();check(Files.isSymbolicLink(oldLink)&&Arrays.equals(Files.readAllBytes(oldTarget),Files.readAllBytes(root.resolve("original-1"))),"original-link");
            now=new Backend(candidate,link);now.state(good(1),3);now.save();check(Files.isSymbolicLink(link)&&Arrays.equals(Files.readAllBytes(root.resolve("original-1")),Files.readAllBytes(target)));check(now.count()==3);cases++;
            Path absent=root.resolve("absent-target"),dangling=root.resolve("dangling");Files.createSymbolicLink(dangling,absent);now=new Backend(candidate,dangling);now.state(good(0),3);now.save();check(Files.isSymbolicLink(dangling)&&Arrays.equals(Files.readAllBytes(root.resolve("original-0")),Files.readAllBytes(absent)));cases++;
            Path oldAbsent=root.resolve("reference-absent"),oldDangling=root.resolve("reference-dangling");Files.createSymbolicLink(oldDangling,oldAbsent);Backend oldDanglingBackend=new Backend(original,oldDangling);oldDanglingBackend.state(good(0),3);oldDanglingBackend.save();check(Files.isSymbolicLink(oldDangling)&&Arrays.equals(Files.readAllBytes(oldAbsent),Files.readAllBytes(absent)),"original-dangling-link");
            for(Path path:Arrays.asList(root,root.resolve("missing-parent/profile"))){Backend oldPath=new Backend(original,path);oldPath.state(good(0),3);oldPath.save();now=new Backend(candidate,path);now.state(good(0),3);now.save();check(now.count()==3&&oldPath.count()==3,"path-failure-count");check(path.equals(root)||!Files.exists(path.getParent()),"path-failure-no-create");cases++;}
            Path fatal=root.resolve("fatal");now=new Backend(candidate,fatal);now.state(error(),3);boolean caught=false;
            try{now.save();}catch(InvocationTargetException e){caught=e.getCause() instanceof AssertionError;}
            check(caught&&now.count()==3&&Files.size(fatal)==0&&Files.getPosixFilePermissions(fatal).equals(Files.getPosixFilePermissions(root.resolve("original-0"))),"error-state");Field lock=now.base.getField("lock");check(!Thread.holdsLock(lock.get(now.value)),"error-lock");
            Backend originalFatal=new Backend(original,root.resolve("original-fatal"));originalFatal.state(error(),3);caught=false;try{originalFatal.save();}catch(InvocationTargetException e){caught=e.getCause() instanceof AssertionError;}check(caught&&originalFatal.count()==3&&Arrays.equals(Files.readAllBytes(fatal),Files.readAllBytes(root.resolve("original-fatal"))),"error-original-differential");cases++;
            Path interruptOld=root.resolve("interrupt-original"),interruptNow=root.resolve("interrupt-candidate");
            for(boolean before:Arrays.asList(Boolean.TRUE,Boolean.FALSE)){
                Backend old=new Backend(original,interruptOld);now=new Backend(candidate,interruptNow);Map value=before?good(1):interrupted();old.state(value,3);now.state(value,3);
                if(before)Thread.currentThread().interrupt();old.save();check(Thread.interrupted(),"interrupt-original-"+before);
                if(before)Thread.currentThread().interrupt();now.save();check(Thread.interrupted(),"interrupt-candidate-"+before);
                check(Arrays.equals(Files.readAllBytes(interruptOld),Files.readAllBytes(interruptNow)),"interrupt-bytes-"+before);check(old.count()==3&&now.count()==3,"interrupt-count-"+before);cases++;
            }
            com.sun.management.UnixOperatingSystemMXBean os=(com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
            now=new Backend(candidate,root.resolve("descriptor"));now.state(good(0),3);
            for(int i=0;i<4;i++){now.save();os.getOpenFileDescriptorCount();gc();}
            long collections=gc(),before=os.getOpenFileDescriptorCount();for(int i=0;i<32;i++)now.save();check(os.getOpenFileDescriptorCount()==before,"success-fd");check(gc()==collections,"success-gc");cases++;
            now.state(bad(false),3);for(int i=0;i<4;i++)now.save();collections=gc();before=os.getOpenFileDescriptorCount();for(int i=0;i<32;i++)now.save();check(os.getOpenFileDescriptorCount()==before,"exception-fd");check(gc()==collections,"exception-gc");cases++;
            now.state(error(),3);for(int i=0;i<4;i++){try{now.save();check(false);}catch(InvocationTargetException e){check(e.getCause() instanceof AssertionError);}}
            collections=gc();before=os.getOpenFileDescriptorCount();for(int i=0;i<32;i++){try{now.save();check(false,"error-missing");}catch(InvocationTargetException e){check(e.getCause() instanceof AssertionError,"error-category");}}check(os.getOpenFileDescriptorCount()==before,"error-fd");check(gc()==collections,"error-gc");check(!Thread.holdsLock(lock.get(now.value)),"error-loop-lock");cases++;
            check(guard.denied.get()==0);check(cases==18);
            System.out.println("PASS preference write; cases=18; success_exception_error_fd_delta=0; interrupts_preserved=true; synthetic_files_only=true");
        }
    }
}
