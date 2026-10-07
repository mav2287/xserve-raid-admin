package atomiccaller;
import java.io.*;
import java.lang.reflect.*;
import java.lang.management.*;
import java.net.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
import java.security.Permission;
import java.util.concurrent.atomic.AtomicInteger;

/** Planned nonshipping caller probe. Explicit disposable identifiers; no factory/Main. */
public final class AtomicCallerObservation {
    static void check(boolean value, String code) { if (!value) throw new AssertionError("atomic-caller:" + code); }
    static final class Guard extends SecurityManager {
        final Path root; final String library; final AtomicInteger denied=new AtomicInteger();
        Guard(Path root,String library){this.root=root;this.library=library;}
        SecurityException fail(){denied.incrementAndGet();return new SecurityException("atomic-caller-guard");}
        void writable(String name){if(!Paths.get(name).toAbsolutePath().normalize().startsWith(root))throw fail();}
        public void checkPermission(Permission permission){
            if(permission instanceof RuntimePermission && (permission.getName().equals("preferences") || permission.getName().equals("setSecurityManager")))throw fail();
            if(permission instanceof FilePermission && permission.getActions().contains("execute"))throw fail();
        }
        public void checkRead(String name){String path=Paths.get(name).toAbsolutePath().normalize().toString();if(path.contains("/Library/Preferences/") || path.endsWith("/Library/Preferences"))throw fail();}
        public void checkWrite(String name){writable(name);} public void checkDelete(String name){writable(name);}
        public void checkExec(String name){throw fail();} public void checkExit(int status){throw fail();}
        public void checkConnect(String host,int port){throw fail();} public void checkConnect(String host,int port,Object context){throw fail();}
        public void checkListen(int port){throw fail();} public void checkMulticast(java.net.InetAddress address){throw fail();}
        public void checkLink(String name){if(!name.equals(library) && !Arrays.asList("management","management_ext","java","zip","net","nio").contains(name))throw fail();}
    }
    static final class Observed extends LinkedHashMap {
        Object expectedLock; boolean candidate; int callbacks; String firstFailure;
        void observed(boolean value,String code){if(!value && firstFailure==null)firstFailure=code;}
        public int size(){
            callbacks++;observed(Thread.holdsLock(expectedLock),"store-lock-held");
            Set<String> chain=new HashSet<>();for(StackTraceElement frame:Thread.currentThread().getStackTrace())chain.add(frame.getClassName()+"."+frame.getMethodName());
            observed(chain.contains("com.apple.util.prefs.FileBasedPreferences.store") && chain.contains("com.apple.util.prefs.Preferences.synchronize") && chain.contains("com.apple.util.plist.PropertyListUtilities.writeXML"),"actual-caller-chain");
            if(candidate)observed(chain.contains("compat.PreferenceIO.write") && chain.contains("compat.PrivatePreferenceFile.write"),"actual-helper-chain");
            return super.size();
        }
    }
    static void origin(ClassLoader loader,String name,URL expected)throws Exception{check(Class.forName(name,false,loader).getProtectionDomain().getCodeSource().getLocation().equals(expected),"class-origin");}
    static void absent(ClassLoader loader,String name)throws Exception{boolean missing=false;try{Class.forName(name,false,loader);}catch(ClassNotFoundException expected){missing=true;}check(missing,"original-no-shadows");}
    static final class Backend {
        final Object value, lock; final Method synchronize; final Field dictionary, count;
        Backend(ClassLoader loader, Path path, URL expected) throws Exception {
            Class<?> type = Class.forName("com.apple.util.prefs.FileBasedPreferences", true, loader);
            check(type.getProtectionDomain().getCodeSource().getLocation().equals(expected), "backend-origin");
            value = type.getConstructor(String.class).newInstance(path.toString());
            Class<?> parent = type.getSuperclass(); dictionary = parent.getDeclaredField("dictionary"); dictionary.setAccessible(true);
            count = parent.getDeclaredField("changeCount"); count.setAccessible(true);
            lock = parent.getField("lock").get(value); synchronize = type.getMethod("synchronize");
        }
        void state(Map data, int changes) throws Exception { dictionary.set(value, data); count.setInt(value, changes); }
        Throwable sync() throws Exception {
            try { synchronize.invoke(value); return null; } catch (InvocationTargetException failed) { return failed.getCause(); }
        }
        void preserved() throws Exception { check(count.getInt(value) == 7, "count-preserved"); check(!Thread.holdsLock(lock), "monitor-released"); }
    }
    static Map good(int kind) {
        Map data = new LinkedHashMap();
        if (kind == 1) data.put("label", "日本語 é 😃 &<>\" '\n");
        if (kind == 2) data.put("nested", new ArrayList(Arrays.asList(Long.valueOf(12), Boolean.TRUE, new byte[]{0,1,2}, new Date(123456789L))));
        if (kind == 4) data.put("surrogates", "a\ud800b\udc00c\u0001");
        if (kind == 3) data.put("large", String.join("", Collections.nCopies(40000, "ü<&")));
        return data;
    }
    static Map<String,Object> identity(Path path) throws IOException { return Files.readAttributes(path,"unix:ino,dev,mode,size,lastModifiedTime,ctime",LinkOption.NOFOLLOW_LINKS); }
    static long gc() { long total=0;for(GarbageCollectorMXBean bean:ManagementFactory.getGarbageCollectorMXBeans()){check(bean.getCollectionCount()>=0,"gc-supported");total+=bean.getCollectionCount();}return total; }
    public static void main(String[] arguments) throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")),"headless");
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        URL reference = new File(System.getProperty("fixture.apple.original")).toURI().toURL();
        URL candidate = new File(System.getProperty("fixture.caller.candidate")).toURI().toURL();
        Guard guard=new Guard(root,System.getProperty("fixture.allowed.library"));System.setSecurityManager(guard);
        byte[] sentinel = {9,8,7}; int cases = 0;
        try (URLClassLoader old = new URLClassLoader(new URL[]{reference}, null); URLClassLoader modern = new URLClassLoader(new URL[]{candidate}, null)) {
            check(old.getParent()==null && modern.getParent()==null,"loader-isolated");
            origin(old,"com.apple.util.plist.PropertyListUtilities",reference);
            for(String name:new String[]{"compat.PreferenceIO","compat.PrivatePreferenceFile","com.apple.util.plist.PropertyListUtilities"})origin(modern,name,candidate);
            absent(old,"compat.PreferenceIO");absent(old,"compat.PrivatePreferenceFile");
            Class<?> holder=Class.forName("compat.PrivatePreferenceFile$Library",true,modern);
            Method available=holder.getDeclaredMethod("available");available.setAccessible(true);check((Boolean)available.invoke(null),"native-library-ready");
            Backend observedOld=new Backend(old,root.resolve("observed-old"),reference),observedNew=new Backend(modern,root.resolve("observed-new"),candidate);
            Observed beforeMap=new Observed(),afterMap=new Observed();beforeMap.expectedLock=observedOld.lock;afterMap.expectedLock=observedNew.lock;afterMap.candidate=true;
            beforeMap.put("label","fixture");afterMap.put("label","fixture");observedOld.state(beforeMap,7);observedNew.state(afterMap,7);
            check(observedOld.sync()==null && observedNew.sync()==null && beforeMap.callbacks>0 && afterMap.callbacks>0,"caller-callbacks-observed");
            check(beforeMap.firstFailure==null,beforeMap.firstFailure);check(afterMap.firstFailure==null,afterMap.firstFailure);
            for (int kind=0;kind<5;kind++) {
                Path a=root.resolve("original-"+kind), b=root.resolve("candidate-"+kind);
                Backend before=new Backend(old,a,reference), after=new Backend(modern,b,candidate);
                before.state(good(kind),7);after.state(good(kind),7);
                check(before.sync()==null && after.sync()==null,"success"); before.preserved();after.preserved();
                check(Arrays.equals(Files.readAllBytes(a),Files.readAllBytes(b)),"bytes");
                check(Files.getPosixFilePermissions(b).equals(PosixFilePermissions.fromString("rw-------")),"private-mode");cases++;
            }
            Path existing = root.resolve("existing"), priorExisting = root.resolve("existing-original");
            Files.write(existing, new byte[500000]); Files.setPosixFilePermissions(existing, PosixFilePermissions.fromString("rw-r--r--"));
            Files.write(priorExisting, new byte[500000]);
            Object existingInode=identity(existing).get("ino");
            Backend beforeExisting = new Backend(old, priorExisting, reference), afterExisting = new Backend(modern, existing, candidate);
            beforeExisting.state(good(1), 7); afterExisting.state(good(1), 7);
            check(beforeExisting.sync()==null && afterExisting.sync()==null, "existing-save");
            check(Arrays.equals(Files.readAllBytes(existing),Files.readAllBytes(priorExisting)),"existing-bytes");
            check(!identity(existing).get("ino").equals(existingInode),"existing-inode-replaced");
            check(Files.getPosixFilePermissions(existing).equals(PosixFilePermissions.fromString("rw-------")),"existing-private");
            afterExisting.preserved();beforeExisting.preserved();cases++;
            for (boolean dangling : new boolean[]{false,true}) {
                Path target=root.resolve("linked-target-"+dangling), link=root.resolve("linked-"+dangling);
                Path oldTarget=root.resolve("old-linked-target-"+dangling), oldLink=root.resolve("old-linked-"+dangling);
                if(!dangling){Files.write(target,sentinel);Files.write(oldTarget,sentinel);}
                Files.createSymbolicLink(link,target);Files.createSymbolicLink(oldLink,oldTarget);
                Backend prior=new Backend(old,oldLink,reference), now=new Backend(modern,link,candidate);prior.state(good(1),7);now.state(good(1),7);
                check(prior.sync()==null && now.sync()==null,"link-catch");prior.preserved();now.preserved();
                check(Files.isSymbolicLink(link) && (dangling ? !Files.exists(target) : Arrays.equals(Files.readAllBytes(target),sentinel)),"link-target-protected");
                check(Files.exists(oldTarget) && Arrays.equals(Files.readAllBytes(oldTarget),Files.readAllBytes(root.resolve("original-1"))),"original-link-characterized");cases++;
            }
            for(Path path : Arrays.asList(root,root.resolve("missing-parent/profile"))) {
                Backend prior=new Backend(old,path,reference),now=new Backend(modern,path,candidate);prior.state(good(0),7);now.state(good(0),7);
                check(prior.sync()==null && now.sync()==null,"path-catch");prior.preserved();now.preserved();
                check(path.equals(root) || !Files.exists(path.getParent()),"missing-parent-no-create");cases++;
            }
            final AssertionError primary=new AssertionError("fixture-primary");
            Map error=new LinkedHashMap(){public int size(){throw primary;}};
            for (Object kind : new Object[]{Boolean.FALSE,Boolean.TRUE,primary}) {
                Map data;
                if(kind==primary)data=error;
                else {data=new LinkedHashMap();if(kind==Boolean.TRUE)data.put("prefix",String.join("",Collections.nCopies(40000,"x")));data.put(Integer.valueOf(4),"bad-key");}
                Path a=root.resolve("failed-original-"+cases),b=root.resolve("failed-candidate-"+cases);
                Files.write(a,sentinel);Files.write(b,sentinel);Files.setPosixFilePermissions(a,PosixFilePermissions.fromString("rw-------"));Files.setPosixFilePermissions(b,PosixFilePermissions.fromString("rw-------"));
                Map<String,Object> retained=identity(b);
                Backend before=new Backend(old,a,reference),after=new Backend(modern,b,candidate);before.state(data,7);after.state(data,7);
                Throwable original=before.sync(), changed=after.sync();
                check(kind==primary ? original==primary && changed==primary : original==null && changed==null,"catch-error-identity");
                before.preserved();after.preserved();
                check(retained.equals(identity(b)) && Arrays.equals(Files.readAllBytes(b),sentinel),"failure-original-retained");
                check(!Arrays.equals(Files.readAllBytes(a),sentinel),"original-failure-characterized");cases++;
            }
            for (boolean pre : new boolean[]{true,false}) {
                Map interrupted=pre ? good(1) : new LinkedHashMap(){public int size(){Thread.currentThread().interrupt();return super.size();}};
                Backend prior=new Backend(old,root.resolve("interrupt-old-"+pre),reference),now=new Backend(modern,root.resolve("interrupt-new-"+pre),candidate);
                prior.state(interrupted,7);now.state(interrupted,7);
                if(pre)Thread.currentThread().interrupt();check(prior.sync()==null,"interrupt-old-save");check(Thread.interrupted(),"interrupt-old-flag");
                if(pre)Thread.currentThread().interrupt();check(now.sync()==null,"interrupt-new-save");check(Thread.interrupted(),"interrupt-new-flag");
                check(Arrays.equals(Files.readAllBytes(root.resolve("interrupt-old-"+pre)),Files.readAllBytes(root.resolve("interrupt-new-"+pre))),"interrupt-bytes");prior.preserved();now.preserved();cases++;
            }
            Map invalid=new LinkedHashMap();invalid.put(Integer.valueOf(4),"bad-key");
            Backend measured=new Backend(modern,root.resolve("measured"),candidate);
            com.sun.management.UnixOperatingSystemMXBean os=(com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
            for(Map data : Arrays.asList(good(0),invalid,error)) {
                measured.state(data,7);
                for(int i=0;i<4;i++)check(data==error ? measured.sync()==primary : measured.sync()==null,"lifetime-warm");
                long before=os.getOpenFileDescriptorCount(), collections=gc();check(before>=3,"fd-supported");
                for(int i=0;i<32;i++)check(data==error ? measured.sync()==primary : measured.sync()==null,"lifetime-result");
                check(os.getOpenFileDescriptorCount()==before,"caller-fd-lifetime");check(gc()==collections,"caller-gc-lifetime");measured.preserved();cases++;
            }
            Path zero=root.resolve("zero-count"), oldZero=root.resolve("zero-count-old");Backend unchanged=new Backend(modern,zero,candidate),oldUnchanged=new Backend(old,oldZero,reference);unchanged.state(good(0),0);oldUnchanged.state(good(0),0);
            check(unchanged.sync()==null && oldUnchanged.sync()==null && !Files.exists(zero) && !Files.exists(oldZero),"zero-count-no-store");cases++;
            check(primary.getSuppressed().length==0 && primary.getCause()==null,"error-unmodified");
            check(guard.denied.get()==0,"forbidden-operation-attempted");
            check(cases==19,"case-count");System.out.println("PASS atomic caller; cases=19; actual_synchronize=true; failure_retains_original=true");
        }
    }
}
