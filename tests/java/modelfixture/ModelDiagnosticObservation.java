package modelfixture;

import fixture.FixtureIdentity;
import fixture.OfflineGuard;
import java.io.*;
import java.net.*;
import java.lang.reflect.*;
import java.security.MessageDigest;
import java.util.*;

/** Actual diagnostic/getter/flag methods; constructors, agents and profiles are never used. */
public final class ModelDiagnosticObservation {
    static final String TOKEN = "<redacted>";
    static void check(boolean ok, String label) { if (!ok) throw new AssertionError(label); }
    static String hash(InputStream source) throws Exception {
        check(source != null, "model resource missing");
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = source) { byte[] buffer = new byte[8192]; int n; while ((n = in.read(buffer)) != -1) digest.update(buffer, 0, n); }
        StringBuilder result = new StringBuilder(); for (byte b : digest.digest()) result.append(String.format("%02x", b & 255)); return result.toString();
    }
    static final class Loader extends URLClassLoader {
        Loader(File jar) throws Exception { super(new URL[]{jar.toURI().toURL()}, ModelDiagnosticObservation.class.getClassLoader()); }
        protected synchronized Class<?> loadClass(String n, boolean resolve) throws ClassNotFoundException {
            if (n.startsWith("com.apple.xsr.som.")) { Class<?> c = findLoadedClass(n); if (c == null) c = findClass(n); if (resolve) resolveClass(c); return c; }
            return super.loadClass(n, resolve);
        }
        void verify(Class<?> type, File jar, String modelHash) throws Exception {
            check(type.getClassLoader() == this && type.getSuperclass().getClassLoader() == this, "model child loader identity");
            check(new File(type.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile().equals(jar.getCanonicalFile()), "model child origin");
            // findResource bypasses the parent-first resource lookup used by getResource.
            for (String[] entry : new String[][]{{"RaidSystem", modelHash}, {"AbstractSystemElement", System.getProperty("fixture.abstractHash")}}) {
                URL resource = findResource("com/apple/xsr/som/" + entry[0] + ".class");
                check(resource != null && "jar".equals(resource.getProtocol()), "model child resource protocol");
                JarURLConnection connection = (JarURLConnection) resource.openConnection(); connection.setUseCaches(false);
                check(new File(connection.getJarFileURL().toURI()).getCanonicalFile().equals(jar.getCanonicalFile()), "model child resource origin");
                check(hash(connection.getInputStream()).equals(entry[1]), "model child resource bytes");
            }
        }
    }
    static final class Child { private final int id; Child(int id) { this.id = id; } public String toString() { return "fixture-child-" + id; } }
    static final class Counter implements Observer { int updates; public void update(Observable model, Object arg) { updates++; } }
    static Object shell(Class<?> type, sun.misc.Unsafe unsafe, String monitor, String management, boolean saved, boolean children) throws Exception {
        Object model = unsafe.allocateInstance(type);
        Field observers = Observable.class.getDeclaredField("obs"); observers.setAccessible(true); observers.set(model, new Vector<Observer>());
        Counter counter = new Counter(); ((Observable)model).addObserver(counter);
        for (String name : new String[]{"systemControllers", "raidControllers", "powerSupplies", "batteries", "fans"}) {
            Field field = type.getDeclaredField(name); field.setAccessible(true); SortedMap<Integer,Object> map = new TreeMap<Integer,Object>();
            if (children) { map.put(1, new Child(1)); if (name.equals("fans")) map.put(2, new Child(2)); }
            field.set(model, Collections.synchronizedSortedMap(map));
        }
        for (String name : new String[]{"name", "primaryHostAddress", "secondaryHostAddress", "currentAddress", "contact", "description", "location"}) {
            Field field = type.getDeclaredField(name); field.setAccessible(true); field.set(model, "fixture-public-" + name);
        }
        Field field = type.getDeclaredField("monitoringPassword"); field.setAccessible(true); field.set(model, monitor);
        type.getMethod("setManagementPassword", String.class).invoke(model, management);
        type.getMethod("setManagementPasswordSaved", boolean.class).invoke(model, saved);
        check(counter.updates == 1, "model saved observer count"); return model;
    }
    static int modelCases(Class<?> type, Class<?> reference, sun.misc.Unsafe unsafe) throws Exception {
        int cases = 0;
        for (String[] passwords : new String[][]{{null, null}, {"", ""}, {"fixture-monitor-sentinel", "fixture-management-sentinel"}, {"fixture,=[]<redacted>-monitor", "fixture,=[]<redacted>-management"}, {"fixture-監視-sentinel", "fixture-管理-sentinel"}})
            for (boolean saved : new boolean[]{false, true}) for (boolean children : new boolean[]{false, true}) {
                Object model = shell(type, unsafe, passwords[0], passwords[1], saved, children);
                Object basis = shell(reference, unsafe, TOKEN, TOKEN, saved, children);
                String diagnostic = (String)type.getMethod("paramString").invoke(model), text = (String)type.getMethod("toString").invoke(model);
                check(diagnostic.equals(reference.getMethod("paramString").invoke(basis)) && text.equals(reference.getMethod("toString").invoke(basis)), "model differential");
                check(diagnostic.contains("monitoringPassword=<redacted>,") && diagnostic.contains("managementPassword=<redacted>,"), "model diagnostic token");
                for (String password : passwords) if (password != null && !password.isEmpty()) check(!diagnostic.contains(password) && !text.contains(password), "model credential leak");
                check(type.getMethod("getMonitoringPassword").invoke(model) == passwords[0], "model monitoring getter");
                check(type.getMethod("getManagementPassword").invoke(model) == passwords[1], "model management getter");
                check(type.getMethod("getManagementPasswordSaved").invoke(model).equals(saved), "model saved flag"); cases++;
            }
        return cases;
    }
    public static void main(String[] args) throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")), "model headless flag");
        check("true".equals(System.getProperty("log4j.defaultInitOverride")), "model logging flag");
        check(TOKEN.equals(System.getProperty("fixture.token")), "model token binding");
        FixtureIdentity.verify(); OfflineGuard.install();
        File candidate = new File(System.getProperty("fixture.candidate")), original = new File(System.getProperty("fixture.reference"));
        Field field = sun.misc.Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true); sun.misc.Unsafe unsafe = (sun.misc.Unsafe)field.get(null); int cases;
        try (Loader now = new Loader(candidate); Loader old = new Loader(original)) {
            Class<?> type = now.loadClass("com.apple.xsr.som.RaidSystem"), reference = old.loadClass("com.apple.xsr.som.RaidSystem");
            now.verify(type, candidate, System.getProperty("fixture.modelHash")); old.verify(reference, original, System.getProperty("fixture.originalHash"));
            String phase = System.getProperty("fixture.phase", "both");
            check(phase.equals("both") || phase.equals("product"), "model phase binding");
            cases = phase.equals("product") ? 0 : modelCases(type, reference, unsafe);
            Class<?> product = Class.forName("com.apple.xsr.som.RaidSystem");
            check(product.getClassLoader() == ModelDiagnosticObservation.class.getClassLoader(), "model product loader");
            check(new File(product.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile().equals(candidate.getCanonicalFile()), "model product origin");
            cases += modelCases(product, reference, unsafe);
        }
        OfflineGuard.assertUntouched(); check(cases == 40, "model case count");
        System.out.println("PASS model diagnostic redaction; cases=40; original_differential=true; product_loader=true; getters_flags_observers_preserved=true; forbidden_operations=0");
    }
}
