package securefixture;
import java.io.*;
import java.lang.management.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;

/** Exercises only separately compiled fault libraries on disposable files. */
public final class AtomicFaultObservation {
    static void check(boolean value, String code) { if (!value) throw new AssertionError("atomic-fault:" + code); }
    static Map<String,Object> identity(Path file) throws IOException {
        return Files.readAttributes(file, "unix:ino,dev,mode,size,lastModifiedTime,ctime", LinkOption.NOFOLLOW_LINKS);
    }
    static List<Path> temporary(Path root) throws IOException {
        List<Path> result = new ArrayList<>();
        try (DirectoryStream<Path> files = Files.newDirectoryStream(root)) {
            for (Path path : files) if (path.getFileName().toString().startsWith(".xra-")) result.add(path);
        }
        return result;
    }
    static void run(Path root, String scenario, byte[] expected) throws Exception {
        Path target = root.resolve("target"); byte[] sentinel = {9,8,7};
        if (Files.exists(target)) Files.delete(target);
        boolean exclusive = scenario.equals("rename-exclusive");
        if (!exclusive) { Files.write(target, sentinel); Files.setPosixFilePermissions(target, PosixFilePermissions.fromString("rw-------")); }
        Map<String,Object> before = exclusive ? null : identity(target);
        Throwable failure = null;
        try { compat.PreferenceIO.write(target.toString(), new LinkedHashMap()); } catch (Throwable caught) { failure = caught; }
        String code = scenario.startsWith("create-interrupted-") ? "atomic-temporary-create-uncertain" : scenario.equals("mode") ? "atomic-temporary-mode" : scenario.equals("dup") ? "atomic-temporary-dup"
            : scenario.equals("stat-leftover") ? "atomic-temporary-stat-leftover" : scenario.equals("close-committed") ? "atomic-committed:close"
            : scenario.startsWith("rename-interrupted-") ? ("atomic-rename-uncertain"+((scenario.contains("-leftover") ? "+leftover" : "")+(scenario.endsWith("-close") ? "+close" : ""))) : scenario.equals("rename-cleanup") ? "atomic-rename+leftover" : scenario.equals("remote-sync") ? "atomic-temporary-sync" : scenario.equals("statfs") ? "atomic-temporary-filesystem"  : "atomic-rename";
        if ((scenario.equals("stat-recovered") || scenario.equals("remote-sync-ok"))) check(failure == null, "recovered-stat-success");
        else check(failure instanceof IOException && code.equals(failure.getMessage()) && failure.getSuppressed().length == 0, "failure-code");
        if ((scenario.equals("stat-recovered") || scenario.equals("remote-sync-ok")) || scenario.equals("close-committed") || scenario.startsWith("rename-interrupted-after")) {
            check(Arrays.equals(Files.readAllBytes(target), expected), "committed-bytes");
            check(!identity(target).get("ino").equals(before.get("ino")), "committed-inode");
        } else if (exclusive) check(Arrays.equals(Files.readAllBytes(target), new byte[]{4,5,6}), "exclusive-target-preserved");
        else check(before.equals(identity(target)) && Arrays.equals(Files.readAllBytes(target), sentinel), "failure-original-unchanged");
        List<Path> left = temporary(root);
        if (scenario.equals("stat-leftover") || scenario.equals("rename-cleanup") || scenario.equals("create-interrupted-after") || scenario.startsWith("rename-interrupted-before-leftover")) {
            check(left.size() == 1, "explicit-leftover-count"); Path file = left.get(0);
            check(Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS) && Files.getPosixFilePermissions(file).equals(PosixFilePermissions.fromString("rw-------")), "explicit-leftover-private");
            check((scenario.equals("stat-leftover") || scenario.equals("create-interrupted-after")) ? Files.size(file) == 0 : Arrays.equals(Files.readAllBytes(file), expected), "explicit-leftover-bytes");
            // Delete only the one inode just inspected in this disposable failure test.
            Files.delete(file);
        } else check(left.isEmpty(), "fault-no-temporary");
    }
    public static void main(String[] arguments) throws Exception {
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        String scenario = System.getProperty("fixture.scenario");
        URL reference = new File(System.getProperty("fixture.reference")).toURI().toURL();
        byte[] expected;
        try (URLClassLoader loader = new URLClassLoader(new URL[]{reference}, null)) {
            Class<?> helper = Class.forName("compat.PreferenceIO", true, loader);
            check(helper.getProtectionDomain().getCodeSource().getLocation().equals(reference), "reference-origin");
            helper.getMethod("write", String.class, Object.class).invoke(null, root.resolve("expected").toString(), new LinkedHashMap());
            expected = Files.readAllBytes(root.resolve("expected"));
        }
        for (int i=0;i<4;i++) run(root, scenario, expected);
        com.sun.management.UnixOperatingSystemMXBean os = (com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
        long before = os.getOpenFileDescriptorCount(); check(before >= 3, "supported-fd-counter");
        long gc = 0; for (GarbageCollectorMXBean bean : ManagementFactory.getGarbageCollectorMXBeans()) { check(bean.getCollectionCount() >= 0, "supported-gc-counter"); gc += bean.getCollectionCount(); }
        for (int i=0;i<32;i++) run(root, scenario, expected);
        check(before == os.getOpenFileDescriptorCount(), "fault-fd-lifetime");
        for (GarbageCollectorMXBean bean : ManagementFactory.getGarbageCollectorMXBeans()) gc -= bean.getCollectionCount();
        check(gc == 0, "fault-gc-lifetime");
        System.out.println("PASS atomic fault " + scenario + "; repetitions=32; fd_delta=0; gc_delta=0");
    }
}
