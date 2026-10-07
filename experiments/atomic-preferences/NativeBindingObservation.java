package atomicfixture;
import java.io.*;
import java.lang.management.*;
import java.nio.file.*;
import java.security.Permission;
import java.util.*;
public final class NativeBindingObservation {
    static void check(boolean value, String code) { if (!value) throw new AssertionError("atomic-binding:" + code); }
    public static void main(String[] arguments) throws Exception {
        String scenario = System.getProperty("fixture.scenario", "normal");
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        Path target = root.resolve("target"); byte[] sentinel = {9,8,7}; Files.write(target, sentinel);
        if (scenario.startsWith("deny-")) System.setSecurityManager(new SecurityManager() {
            public void checkPermission(Permission permission) { }
            public void checkWrite(String name) { if (scenario.equals("deny-path")) throw new SecurityException("fixture-path-denied"); }
            public void checkWrite(FileDescriptor descriptor) { if (scenario.equals("deny-fd")) throw new SecurityException("fixture-descriptor-denied"); }
        });
        com.sun.management.UnixOperatingSystemMXBean os = (com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
        Throwable failure = null;
        try { AtomicPreferenceFile.write(target.toString(), new LinkedHashMap()); } catch (Throwable caught) { failure = caught; }
        if (scenario.equals("normal")) {
            check(failure == null && !Arrays.equals(Files.readAllBytes(target), sentinel), "normal-write");
        } else {
            String message = scenario.equals("deny-path") ? "fixture-path-denied" : scenario.equals("deny-fd") ? "fixture-descriptor-denied" : "atomic-library-unavailable";
            check(failure != null && failure.getClass() == (scenario.startsWith("deny-") ? SecurityException.class : IOException.class) && message.equals(failure.getMessage()), "denial-type");
            check(Arrays.equals(Files.readAllBytes(target), sentinel), "denial-target-unchanged");
            for (int i=0;i<4;i++) try { AtomicPreferenceFile.write(root.resolve("absent").toString(), new LinkedHashMap()); } catch (Throwable caught) { }
            long before = os.getOpenFileDescriptorCount(); check(before >= 3, "supported-fd-counter");
            for (int i=0;i<32;i++) {
                Throwable caught = null;
                try { AtomicPreferenceFile.write(root.resolve("absent").toString(), new LinkedHashMap()); } catch (Throwable value) { caught = value; }
                check(caught != null && message.equals(caught.getMessage()), "repeated-denial");
            }
            check(os.getOpenFileDescriptorCount() == before, "denial-fd-lifetime");
            check(!Files.exists(root.resolve("absent")), "denial-no-create");
        }
        try (java.util.stream.Stream<Path> paths = Files.walk(root)) {
            check(paths.noneMatch(path -> path.getFileName().toString().startsWith(".xra-")), "no-temporary");
        }
        System.out.println("PASS atomic binding " + scenario);
    }
}
