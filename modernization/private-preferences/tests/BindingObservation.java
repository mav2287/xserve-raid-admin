package atomiccaller;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.lang.management.*;
import java.util.*;

public final class BindingObservation {
    static void check(boolean v,String c){if(!v)throw new AssertionError("secure-binding:"+c);}
    static Throwable save(Method m,Path p,Object v)throws Exception{try{m.invoke(null,p.toString(),v);return null;}catch(InvocationTargetException e){return e.getCause();}}
    public static void main(String[] args)throws Exception{
        Path root=Paths.get(System.getProperty("fixture.directory")).toRealPath(),target=root.resolve("profile");byte[] sentinel={9,8,7};Files.write(target,sentinel);Object inode=Files.getAttribute(target,"unix:ino");
        AtomicCallerObservation.Guard guard=new AtomicCallerObservation.Guard(root,System.getProperty("fixture.allowed.library"));System.setSecurityManager(guard);
        URL url=new File(System.getProperty("fixture.candidate")).toURI().toURL();String scenario=System.getProperty("fixture.scenario");
        try(URLClassLoader loader=new URLClassLoader(new URL[]{url},null){
            protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
                if (scenario.equals("reporter-unavailable") && name.equals("compat.PreferenceSaveFailure")) throw new NoClassDefFoundError("fixture-reporting-unavailable");
                return super.loadClass(name,resolve);
            }
        }){
            Class<?> helper=Class.forName("compat.PreferenceIO",true,loader);check(helper.getProtectionDomain().getCodeSource().getLocation().equals(url),"origin");Method write=helper.getMethod("write",String.class,Object.class);
            if(scenario.equals("reporter-unavailable")) {
                final RuntimeException primary=new RuntimeException("fixture-private-message");Map fail=new LinkedHashMap(){public int size(){throw primary;}};
                for(int i=0;i<32;i++)check(save(write,target,fail)==primary,"reporter-linkage-primary");
                check(Arrays.equals(Files.readAllBytes(target),sentinel)&&inode.equals(Files.getAttribute(target,"unix:ino")),"failure-original");
            } else if(scenario.equals("reporter")){
                final AssertionError error=new AssertionError("fixture-error");Map bad=new LinkedHashMap(){public int size(){throw error;}};
                check(save(write,target,bad)==error,"error-identity");check(error.getSuppressed().length==0&&error.getCause()==null,"error-unmodified");
                final RuntimeException primary=new RuntimeException("fixture-private-message");Map fail=new LinkedHashMap(){public int size(){throw primary;}};
                for(int i=0;i<32;i++)check(save(write,target,fail)==primary,"exception-identity");
                Class<?> reporting=Class.forName("compat.PreferenceSaveFailure",true,loader);Method report=reporting.getDeclaredMethod("report",Throwable.class);report.setAccessible(true);
                for(int i=0;i<32;i++)report.invoke(null,new IOException("atomic-committed:close"));
                // A throwing diagnostic must leave the same original primary object.
                Field reporter=reporting.getDeclaredField("reporter");reporter.setAccessible(true);Class<?> api=Class.forName("compat.PreferenceSaveFailure$Reporter",true,loader);
                reporter.set(null,java.lang.reflect.Proxy.newProxyInstance(loader,new Class[]{api},(p,m,a)->{throw new AssertionError("fixture-reporter-error");}));
                Field flags=reporting.getDeclaredField("failedReported");flags.setAccessible(true);((java.util.concurrent.atomic.AtomicBoolean)flags.get(null)).set(false);
                check(save(write,target,fail)==primary,"reporter-primary-preserved");
                check(Arrays.equals(Files.readAllBytes(target),sentinel)&&inode.equals(Files.getAttribute(target,"unix:ino")),"failure-original");
            }else{
                for(int i=0;i<4;i++){Throwable e=save(write,target,new LinkedHashMap());check(e instanceof IOException&&"atomic-library-unavailable".equals(e.getMessage()),"unavailable-code");}
                com.sun.management.UnixOperatingSystemMXBean os=(com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();long before=os.getOpenFileDescriptorCount();check(before>=3,"fd-supported");long gc=0;for(GarbageCollectorMXBean b:ManagementFactory.getGarbageCollectorMXBeans()){check(b.getCollectionCount()>=0,"gc-supported");gc+=b.getCollectionCount();}
                for(int i=0;i<32;i++){Throwable e=save(write,target,new LinkedHashMap());check(e instanceof IOException&&"atomic-library-unavailable".equals(e.getMessage()),"permanent-unavailable");check(Arrays.equals(Files.readAllBytes(target),sentinel)&&inode.equals(Files.getAttribute(target,"unix:ino")),"no-fallback");}
                check(before==os.getOpenFileDescriptorCount(),"fd-lifetime");for(GarbageCollectorMXBean b:ManagementFactory.getGarbageCollectorMXBeans())gc-=b.getCollectionCount();check(gc==0,"gc-lifetime");
            }
        }
        for(Thread t:Thread.getAllStackTraces().keySet())check(!t.getName().startsWith("AWT-"),"cli-no-awt");
        check(guard.denied.get()==0,"guard");check(root.toFile().list().length==1,"exact-listing");System.out.println("PASS secure binding "+scenario+"; fallback=false; primary_preserved=true");
    }
}
