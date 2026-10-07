import fixture.FixtureIdentity;
import com.apple.util.prefs.FileBasedPreferences;
import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.security.Permission;
import java.lang.management.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Original backend only, explicit disposable identifier, never the Mac factory. */
public final class PreferenceLifetimeObservation {
    static void check(boolean ok,String code){if(!ok)throw new AssertionError(code);}
    static final class Guard extends SecurityManager {
        final Path root; final AtomicInteger denied=new AtomicInteger();
        Guard(Path root){this.root=root;}
        SecurityException fail(){denied.incrementAndGet();return new SecurityException("Preference fixture guard");}
        void writable(String name){if(!Paths.get(name).toAbsolutePath().normalize().startsWith(root))throw fail();}
        public void checkPermission(Permission p){
            if(p instanceof RuntimePermission && (p.getName().equals("preferences") || p.getName().equals("setSecurityManager")))throw fail();
            if(p instanceof FilePermission && p.getActions().contains("execute"))throw fail();
        }
        public void checkRead(String name){String n=Paths.get(name).toAbsolutePath().normalize().toString();if(n.contains("/Library/Preferences/") || n.endsWith("/Library/Preferences"))throw fail();}
        public void checkWrite(String name){writable(name);}
        public void checkDelete(String name){writable(name);}
        public void checkExec(String name){throw fail();}
        public void checkExit(int status){throw fail();}
        public void checkConnect(String host,int port){throw fail();}
        public void checkConnect(String host,int port,Object context){throw fail();}
        public void checkListen(int port){throw fail();}
        public void checkMulticast(java.net.InetAddress address){throw fail();}
    }
    static final class Backend extends FileBasedPreferences {
        Backend(String identifier){super(identifier);dictionary=new LinkedHashMap();dictionary.put("fixture-public-label","fixture-value");changeCount=3;}
        void checkState(){check("fixture-value".equals(dictionary.get("fixture-public-label")),"preference fixture state");}
    }
    static long gc(){long n=0;for(GarbageCollectorMXBean bean:ManagementFactory.getGarbageCollectorMXBeans()){check(bean.getCollectionCount()>=0,"GC observation unavailable");n+=bean.getCollectionCount();}return n;}
    static int mode(Path path)throws Exception{Set<PosixFilePermission> p=Files.getPosixFilePermissions(path);int result=0;PosixFilePermission[] values=PosixFilePermission.values();for(int i=0;i<values.length;i++)if(p.contains(values[i]))result|=1<<(8-i);return result;}
    public static void main(String[] args)throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")),"preference headless flag");FixtureIdentity.verify();
        Path root=Paths.get(System.getProperty("fixture.directory")).toRealPath();Guard guard=new Guard(root);System.setSecurityManager(guard);
        check(ManagementFactory.getOperatingSystemMXBean() instanceof com.sun.management.UnixOperatingSystemMXBean,"descriptor observation unavailable");
        com.sun.management.UnixOperatingSystemMXBean os=(com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
        Backend backend=new Backend(root.resolve("synthetic-profile.plist").toString());
        // Warm parser/serializer/management paths before measuring; any later GC invalidates the run.
        for(int i=0;i<4;i++){backend.store();backend.load();backend.checkState();os.getOpenFileDescriptorCount();gc();}
        long g=gc(),before=os.getOpenFileDescriptorCount();for(int i=0;i<32;i++)backend.store();long afterStore=os.getOpenFileDescriptorCount();
        for(int i=0;i<32;i++){backend.load();backend.checkState();}long afterLoad=os.getOpenFileDescriptorCount();
        check(gc()==g,"GC occurred; development run invalid");check(guard.denied.get()==0,"forbidden operation attempted");
        System.out.println("OBSERVE original preference IO; store_fd_delta="+(afterStore-before)+"; load_fd_delta="+(afterLoad-afterStore)+"; new_file_mode="+Integer.toOctalString(mode(root.resolve("synthetic-profile.plist")))+"; gc_during_measurement=0; real_profile_access=none");
    }
}
