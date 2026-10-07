package atomiccaller;

import java.io.*;
import java.net.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;

/** Synthetic model-to-plist boundary only: no registry constructor, factory, GUI or controller. */
public final class CredentialPersistenceObservation {
    static void check(boolean value, String code) { if (!value) throw new AssertionError("credential-fixture:" + code); }
    static void field(Object value, String name, Object data) throws Exception {
        Field f = value.getClass().getDeclaredField(name); f.setAccessible(true); f.set(value, data);
    }
    static Object model(ClassLoader loader, sun.misc.Unsafe unsafe, String monitor, String management, boolean saved, boolean secondary) throws Exception {
        Class<?> type = Class.forName("com.apple.xsr.som.RaidSystem", true, loader);
        Object value = unsafe.allocateInstance(type);
        Field observers = Observable.class.getDeclaredField("obs"); observers.setAccessible(true); observers.set(value, new Vector<Observer>());
        field(value, "name", "fixture-public-name"); field(value, "primaryHostAddress", "192.0.2.1");
        field(value, "secondaryHostAddress", secondary ? "192.0.2.2" : null);
        field(value, "monitoringPassword", monitor);
        Class<?> agentType = Class.forName("com.apple.xsr.som.RaidSystemAgent", true, loader);
        Object agent = unsafe.allocateInstance(agentType); field(agent, "pollDelay", Long.valueOf(7000)); field(value, "agent", agent);
        type.getMethod("setManagementPassword", String.class).invoke(value, management);
        type.getMethod("setManagementPasswordSaved", boolean.class).invoke(value, saved);
        return value;
    }
    static Map container(ClassLoader loader, Object model) throws Exception {
        Class<?> localizer = Class.forName("com.apple.xsr.SOMLocalizer", true, loader);
        Method method = localizer.getDeclaredMethod("toPrefsContainer", model.getClass()); method.setAccessible(true);
        return (Map)method.invoke(null, model);
    }
    static void validate(Map map, String monitor, boolean secondary, boolean restored) {
        Set<String> keys = new HashSet<String>(Arrays.asList("Name", "Rate", "IPAddress")); if (monitor != null) keys.add("Attributes");
        check(Objects.equals(map.get("Attributes"), monitor), "monitor-source"); check(map.keySet().equals(keys), "keys");
        Object rate = restored ? (Object)Long.valueOf(7) : (Object)Integer.valueOf(7);
        check(map.get("Rate").equals(rate), "rate"); check(map.get("Name").equals("fixture-public-name"), "name");
        check(map.get("IPAddress").equals(secondary ? Arrays.asList("192.0.2.1", "192.0.2.2") : Arrays.asList("192.0.2.1")), "addresses");
    }
    public static void main(String[] args) {
        try { run(); } catch (Throwable failure) {
            String code = failure instanceof AssertionError && "credential-fixture:monitor-source".equals(failure.getMessage()) ? "monitor-source" : "assertion_or_execution";
            System.out.println("FAIL credential fixture; fixed_code=" + code); throw new AssertionError("credential-fixture-failed");
        }
    }
    static void run() throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")) && "true".equals(System.getProperty("log4j.defaultInitOverride")), "flags");
        check(System.getProperty("os.arch").equals(System.getProperty("fixture.expectedArch")), "jvm-architecture");
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        AtomicCallerObservation.Guard guard = new AtomicCallerObservation.Guard(root, System.getProperty("fixture.allowed.library"));
        System.setSecurityManager(guard);
        Field unsafeField = sun.misc.Unsafe.class.getDeclaredField("theUnsafe"); unsafeField.setAccessible(true); sun.misc.Unsafe unsafe = (sun.misc.Unsafe)unsafeField.get(null);
        URL before = new File(System.getProperty("fixture.apple.original")).toURI().toURL(), after = new File(System.getProperty("fixture.caller.candidate")).toURI().toURL();
        int cases = 0;
        try (URLClassLoader old = new URLClassLoader(new URL[]{before}, null); URLClassLoader now = new URLClassLoader(new URL[]{after}, null)) {
            ClassLoader[] loaders = {old, now}; URL[] origins = {before, after};
            for (int writer = 0; writer < 2; writer++) {
                for (String name : new String[]{"com.apple.xsr.som.RaidSystem", "com.apple.xsr.som.RaidSystemAgent", "com.apple.xsr.SOMLocalizer", "com.apple.util.prefs.FileBasedPreferences"})
                    AtomicCallerObservation.origin(loaders[writer], name, origins[writer]);
                for (String[] secrets : new String[][]{{null, "synthetic-management"}, {"", "synthetic-management"}, {"synthetic-monitor", "synthetic-management"}, {"synthetic-監視-é", "synthetic-管理-é"}, {"synthetic-monitor<&'\"", "synthetic-management<&'\""}})
                    for (boolean saved : new boolean[]{false, true}) for (boolean secondary : new boolean[]{false, true}) {
                        Object value = model(loaders[writer], unsafe, secrets[0], secrets[1], saved, secondary);
                        Map first = container(loaders[writer], value); validate(first, secrets[0], secondary, false);
                        // The actual setter used by Forget changes the flag, retaining the original management value.
                        value.getClass().getMethod("setManagementPasswordSaved", boolean.class).invoke(value, false);
                        check(value.getClass().getMethod("getManagementPassword").invoke(value) == secrets[1], "forget-retains-memory");
                        check(Boolean.FALSE.equals(value.getClass().getMethod("getManagementPasswordSaved").invoke(value)), "forget-flag");
                        check(container(loaders[writer], value).equals(first), "forget-persistence-unchanged");
                        value.getClass().getMethod("setManagementPassword", String.class).invoke(value, "synthetic-management-updated");
                        check(container(loaders[writer], value).equals(first), "management-persistence-unchanged");
                        ArrayList systems = new ArrayList(); systems.add(first);
                        Path path = root.resolve("profile-" + writer + "-" + cases);
                        AtomicCallerObservation.Backend backend = new AtomicCallerObservation.Backend(loaders[writer], path, origins[writer]);
                        backend.value.getClass().getMethod("load").invoke(backend.value);
                        backend.value.getClass().getMethod("setArray", String.class, ArrayList.class).invoke(backend.value, "Systems", systems);
                        check(backend.sync() == null && Files.isRegularFile(path), "store");
                        byte[] written = Files.readAllBytes(path); check(backend.sync() == null && Arrays.equals(written, Files.readAllBytes(path)), "repeated-sync");
                        if (writer == 1) check(Files.getPosixFilePermissions(path).equals(PosixFilePermissions.fromString("rw-------")), "private-mode");
                        for (int reader = 0; reader < 2; reader++) {
                            AtomicCallerObservation.Backend restored = new AtomicCallerObservation.Backend(loaders[reader], path, origins[reader]);
                            restored.value.getClass().getMethod("load").invoke(restored.value);
                            ArrayList actual = (ArrayList)restored.value.getClass().getMethod("getArray", String.class, ArrayList.class).invoke(restored.value, "Systems", null);
                            Map expectedMap = new HashMap(first); expectedMap.put("Rate", Long.valueOf(7));
                            check(actual != null && actual.size() == 1, "read-count"); validate((Map)actual.get(0), secrets[0], secondary, true); check(actual.get(0).equals(expectedMap), "roundtrip"); cases++;
                        }
                        Files.delete(path);
                    }
            }
        }
        check(guard.denied.get() == 0, "forbidden-operation"); check(cases == 80, "cases");
        System.out.println("PASS credential persistence; roundtrips=80; management_absent=true; monitoring_preserved=true; forget_flag_only=true; private_current_mode=true; forbidden_operations=0");
    }
}
