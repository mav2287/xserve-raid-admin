package compat;
import fixture.FixtureIdentity;
import fixture.OfflineGuard;
import java.io.*;
import java.net.*;
import java.lang.reflect.*;
import java.awt.event.ActionEvent;
import java.util.*;
import javax.swing.event.HyperlinkEvent;

/** Actual helper and exact patched actions, with no browser or controller execution. */
public final class HelpObservation {
    private static int cases;
    private static void check(boolean ok) { if(!ok)throw new AssertionError("Help observation differs"); }
    private static final class Recording implements HelpLauncher.Opener, HelpLauncher.Reporter {
        URI uri; String code; int opens,reports; Throwable fault;
        public void open(URI input) throws Exception {
            opens++;uri=input;
            if(fault instanceof Exception)throw (Exception)fault;
            if(fault instanceof LinkageError)throw (LinkageError)fault;
        }
        public void report(String input) { reports++;code=input; }
    }
    private static void failure(String input,String code,Throwable fault,boolean opens) {
        Recording r=new Recording();r.fault=fault;HelpLauncher.openURL(input,r,r);
        check(r.opens==(opens?1:0)&&r.reports==1&&code.equals(r.code));cases++;
    }
    private static final class DenyLegacy extends URLClassLoader {
        int attempted;
        DenyLegacy(URL jar) { super(new URL[]{jar},HelpObservation.class.getClassLoader()); }
        @Override protected synchronized Class<?> loadClass(String name,boolean resolve) throws ClassNotFoundException {
            if(name.equals("edu.stanford.ejalbert.BrowserLauncher")) {attempted++;throw new ClassNotFoundException("Legacy browser prohibited");}
            if(name.equals("com.apple.xsr.RaidAdmin$HelpListener")||name.equals("com.apple.xsr.SystemMonitorController$UnsupportedOperationDialog")) {
                Class<?> c=findLoadedClass(name);if(c==null)c=findClass(name);if(resolve)resolveClass(c);return c;
            }
            return super.loadClass(name,resolve);
        }
    }
    private static void observedStderr(Runnable call,String expected) {
        PrintStream old=System.err;ByteArrayOutputStream out=new ByteArrayOutputStream();
        try {System.setErr(new PrintStream(out));call.run();} finally {System.setErr(old);}
        check(out.toString().equals(expected));cases++;
    }
    private static final class BrowserGuard extends SecurityManager {
        final OfflineGuard delegate=new OfflineGuard();
        int browsers;
        public void checkPermission(java.security.Permission p) {
            if ((p instanceof FilePermission && p.getActions().contains("execute")) || p instanceof java.awt.AWTPermission) {
                browsers++;throw new SecurityException("Browser permission prohibited");
            }
            delegate.checkPermission(p);
        }
        public void checkRead(String p){delegate.checkRead(p);}
        public void checkWrite(String p){delegate.checkWrite(p);}
        public void checkWrite(FileDescriptor p){delegate.checkWrite(p);}
        public void checkDelete(String p){delegate.checkDelete(p);}
        public void checkExit(int n){delegate.checkExit(n);}
        public void checkExec(String p){delegate.checkExec(p);}
        public void checkConnect(String h,int p){delegate.checkConnect(h,p);}
        public void checkConnect(String h,int p,Object c){delegate.checkConnect(h,p,c);}
        public void checkListen(int p){delegate.checkListen(p);}
        public void checkMulticast(java.net.InetAddress a){delegate.checkMulticast(a);}
    }
    public static void main(String[] args) throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")));
        check(java.awt.GraphicsEnvironment.isHeadless());
        FixtureIdentity.verify();BrowserGuard guard=new BrowserGuard();System.setSecurityManager(guard);
        for(java.security.Permission permission:new java.security.Permission[]{new FilePermission("<<ALL FILES>>","execute"),new java.awt.AWTPermission("showWindowWithoutWarningBanner"),new java.awt.AWTPermission("accessClipboard")}) {
            try {guard.checkPermission(permission);throw new AssertionError("Browser guard failed");} catch(SecurityException expected) {}
        }
        check(guard.browsers==3);int browserControls=guard.browsers;
        Set<String> supportUrls=new HashSet<String>();
        String[] locales={"", "da", "de", "en", "en_AU", "en_GB", "es", "fi", "fr", "it", "ja", "ko", "nl", "no", "pt", "sv", "zh", "zh_TW"};
        for(String tag:locales) {
            String[] p=tag.split("_");Locale locale=tag.length()==0?Locale.ROOT:new Locale(p[0],p.length>1?p[1]:"");
            ResourceBundle b=ResourceBundle.getBundle("com.apple.xsr.resources.GlobalResources",locale,ResourceBundle.Control.getNoFallbackControl(ResourceBundle.Control.FORMAT_DEFAULT));
            check(b.getLocale().equals(locale));Locale.setDefault(locale);com.apple.xsr.Resources.load();
            for(String key:new String[]{"helpURL","unsupportedOperationDialog.url"}) {
                String source=com.apple.xsr.Resources.getString(key);if(key.equals("unsupportedOperationDialog.url"))supportUrls.add(source);check(source.equals(b.getString(key)));Recording r=new Recording();HelpLauncher.openURL(source,r,r);
                check(r.opens==1&&r.reports==0&&source.equals(r.uri.toString()));cases++;
            }
        }
        check(supportUrls.equals(new HashSet<String>(Arrays.asList("http://www.apple.com/support/","http://www.apple.com/de/support/","http://www.info.apple.com/frfr/index.html","http://www.apple.com/jp/support/"))));
        Locale.setDefault(Locale.US);com.apple.xsr.Resources.load();
        for(String s:new String[]{"http://example.invalid/a%20b?q=%E6%97%A5#fragment","custom:opaque-value","https://example.invalid/日本語"}) {
            Recording r=new Recording();HelpLauncher.openURL(s,r,r);check(r.opens==1&&r.reports==0&&s.equals(r.uri.toString()));cases++;
        }
        failure(null,"HELP_URL_MISSING",null,false);failure(" \t\n","HELP_URL_MISSING",null,false);
        failure("relative/path","HELP_URL_INVALID",null,false);failure("http://bad host/","HELP_URL_INVALID",null,false);
        for(Throwable t:new Throwable[]{new IOException("synthetic-detail"),new SecurityException("synthetic-detail"),new UnsupportedOperationException("synthetic-detail"),new IllegalArgumentException("synthetic-detail"),new Exception("synthetic-detail"),new UnsatisfiedLinkError("synthetic-detail"),new ExceptionInInitializerError("synthetic-detail")})
            failure("http://example.invalid/","BROWSE_FAILED",t,true);
        observedStderr(new Runnable(){public void run(){HelpLauncher.openURL("http://example.invalid/");}},"BROWSE_UNSUPPORTED\n");
        final File jar=new File(System.getProperty("fixture.candidate"));
        try(final DenyLegacy loader=new DenyLegacy(jar.toURI().toURL())) {
            final Class<?> help=loader.loadClass("com.apple.xsr.RaidAdmin$HelpListener");
            check(help.getClassLoader()==loader);
            check(new File(help.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile().equals(jar.getCanonicalFile()));
            Constructor<?> ctor=help.getDeclaredConstructor();ctor.setAccessible(true);final Object listener=ctor.newInstance();
            final Method action=help.getMethod("actionPerformed",ActionEvent.class);action.setAccessible(true);
            observedStderr(new Runnable(){public void run(){try{action.invoke(listener,new ActionEvent(listener,0,"fixture"));}catch(Exception e){throw new AssertionError("Help action failed");}}},"BROWSE_UNSUPPORTED\n");
            final Class<?> dialog=loader.loadClass("com.apple.xsr.SystemMonitorController$UnsupportedOperationDialog");
            check(dialog.getClassLoader()==loader);
            check(new File(dialog.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile().equals(jar.getCanonicalFile()));
            Field uf=sun.misc.Unsafe.class.getDeclaredField("theUnsafe");uf.setAccessible(true);
            sun.misc.Unsafe unsafe=(sun.misc.Unsafe)uf.get(null);final Object shell=unsafe.allocateInstance(dialog);
            Field url=dialog.getDeclaredField("url");url.setAccessible(true);url.set(shell,"http://example.invalid/");
            final Method hyperlink=dialog.getMethod("hyperlinkUpdate",HyperlinkEvent.class);hyperlink.setAccessible(true);
            for(final HyperlinkEvent.EventType event:new HyperlinkEvent.EventType[]{HyperlinkEvent.EventType.ENTERED,HyperlinkEvent.EventType.EXITED,HyperlinkEvent.EventType.ACTIVATED}) {
                observedStderr(new Runnable(){public void run(){try{hyperlink.invoke(shell,new HyperlinkEvent(shell,event,null));}catch(Exception e){throw new AssertionError("Support action failed");}}},event==HyperlinkEvent.EventType.ACTIVATED?"BROWSE_UNSUPPORTED\n":"");
            }
            url.set(shell,"relative/path");
            observedStderr(new Runnable(){public void run(){try{hyperlink.invoke(shell,new HyperlinkEvent(shell,HyperlinkEvent.EventType.ACTIVATED,null));}catch(Exception e){throw new AssertionError("Support action failed");}}},"HELP_URL_INVALID\n");
            for(String support:new String[]{"http://www.apple.com/support/","http://www.apple.com/de/support/","http://www.info.apple.com/frfr/index.html","http://www.apple.com/jp/support/"}) {
                url.set(shell,support);
                observedStderr(new Runnable(){public void run(){try{hyperlink.invoke(shell,new HyperlinkEvent(shell,HyperlinkEvent.EventType.ACTIVATED,null));}catch(Exception e){throw new AssertionError("Support action failed");}}},"BROWSE_UNSUPPORTED\n");
            }
            url.set(shell,null);
            observedStderr(new Runnable(){public void run(){try{hyperlink.invoke(shell,new HyperlinkEvent(shell,HyperlinkEvent.EventType.ACTIVATED,null));}catch(Exception e){throw new AssertionError("Support action failed");}}},"HELP_URL_MISSING\n");
            check(loader.attempted==0);
        }
        // Reachability control: the same loader must reject the actual old call path.
        File baseline=new File(System.getProperty("fixture.baseline"));
        try(DenyLegacy loader=new DenyLegacy(baseline.toURI().toURL())) {
            Class<?> old=loader.loadClass("com.apple.xsr.RaidAdmin$HelpListener");check(old.getClassLoader()==loader);
            Constructor<?> ctor=old.getDeclaredConstructor();ctor.setAccessible(true);Object listener=ctor.newInstance();
            Method action=old.getMethod("actionPerformed",ActionEvent.class);action.setAccessible(true);
            try {action.invoke(listener,new ActionEvent(listener,0,"fixture"));throw new AssertionError("Old browser call unexpectedly succeeded");}
            catch(InvocationTargetException failure) {check(failure.getCause() instanceof NoClassDefFoundError);}
            check(loader.attempted==1);cases++;
        }
        OfflineGuard.assertUntouched();check(guard.browsers==browserControls);check(cases==62);
        System.out.println("PASS help boundary; cases=62; legacy_browser_load_attempts=0; legacy_control_attempts=1; guard_control_rejections=3; forbidden_operations=0");
    }
}
