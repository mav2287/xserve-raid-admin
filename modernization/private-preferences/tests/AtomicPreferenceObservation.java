package securefixture;

import java.io.*;
import java.lang.management.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;

public final class AtomicPreferenceObservation {
    static void check(boolean value, String code) { if (!value) throw new AssertionError("atomic-preference:" + code); }
    static Set<PosixFilePermission> mode(String value) { return PosixFilePermissions.fromString(value); }
    static long gc() {
        long count = 0;
        for (GarbageCollectorMXBean bean : ManagementFactory.getGarbageCollectorMXBeans()) {
            check(bean.getCollectionCount() >= 0, "gc-supported"); count += bean.getCollectionCount();
        }
        return count;
    }
    static Set<String> listing(Path directory) throws IOException {
        Set<String> result = new TreeSet<>();
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(directory)) { for (Path file : stream) result.add(file.getFileName().toString()); }
        return result;
    }
    static Set<String> tree(Path directory) throws IOException {
        Set<String> result = new TreeSet<>();
        try (java.util.stream.Stream<Path> paths = Files.walk(directory)) {
            paths.forEach(path -> result.add(directory.relativize(path).toString()));
        }
        return result;
    }
    static Map dictionary(int kind) {
        Map value = new LinkedHashMap();
        if (kind == 1) value.put("label", "日本語 é 😃 &<>\" '\n");
        if (kind == 2) value.put("nested", new ArrayList(Arrays.asList(Long.valueOf(12), Boolean.TRUE, new byte[]{0, 1, 2}, new Date(123456789L))));
        if (kind == 3) value.put("large", String.join("", Collections.nCopies(40000, "ü<&")));
        if (kind == 4) value.put("surrogates", "a\ud800b\udc00c\u0001");
        return value;
    }
    static Map failure(boolean large) {
        Map value = new LinkedHashMap(); if (large) value.put("prefix", String.join("", Collections.nCopies(40000, "x")));
        value.put(Integer.valueOf(5), "bad-key"); return value;
    }
    static Throwable save(Path path, Object dictionary) {
        try { TransactionProbe.write(path.toString(), dictionary); return null; }
        catch (Throwable failure) { return failure; }
    }
    static Map<String,Object> identity(Path path) throws IOException { return Files.readAttributes(path, "unix:ino,dev,mode,size,lastModifiedTime,ctime", LinkOption.NOFOLLOW_LINKS); }
    static void rejected(Path path, String code, Path root) throws Exception {
        Set<String> before = tree(root);
        Throwable failure = save(path, dictionary(0));
        check(failure instanceof IOException && code.equals(failure.getMessage()), "rejection-code");
        check(failure.getSuppressed().length == 0, "rejection-cleanup"); check(tree(root).equals(before), "rejection-listing");
    }
    public static void main(String[] arguments) throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")), "headless");
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        check(Files.getFileStore(root).type().equals("apfs"), "apfs");
        byte[] sentinel = {9, 8, 7}; int cases = 0;
        URL reference = new File(System.getProperty("fixture.reference")).toURI().toURL();
        try (URLClassLoader old = new URLClassLoader(new URL[]{reference}, null)) {
            Class<?> helper = Class.forName("compat.PreferenceIO", true, old);
            check(helper.getProtectionDomain().getCodeSource().getLocation().equals(reference), "reference-origin");
            Method write = helper.getMethod("write", String.class, Object.class);
            for (int kind = 0; kind < 5; kind++) {
                Path original = root.resolve("old-" + kind), candidate = root.resolve("new-" + kind);
                write.invoke(null, original.toString(), dictionary(kind));
                TransactionProbe.write(candidate.toString(), dictionary(kind));
                check(Arrays.equals(Files.readAllBytes(original), Files.readAllBytes(candidate)), "success-bytes");
                check(Files.getPosixFilePermissions(candidate).equals(mode("rw-------")), "private-mode"); cases++;
            }
            for (boolean pre : new boolean[]{true, false}) {
                Map value = pre ? dictionary(1) : new LinkedHashMap() { public int size() { Thread.currentThread().interrupt(); return super.size(); } };
                Path original = root.resolve("old-interrupt-" + pre), candidate = root.resolve("new-interrupt-" + pre);
                if (pre) Thread.currentThread().interrupt(); write.invoke(null, original.toString(), value); check(Thread.interrupted(), "reference-interrupt");
                if (pre) Thread.currentThread().interrupt(); TransactionProbe.write(candidate.toString(), value); check(Thread.interrupted(), "candidate-interrupt");
                check(Arrays.equals(Files.readAllBytes(original), Files.readAllBytes(candidate)), "interrupt-bytes"); cases++;
            }
            Path existing = root.resolve("existing"); Files.write(existing, sentinel); Files.setPosixFilePermissions(existing, mode("rw-r--r--"));
            Object inode = identity(existing).get("ino");
            try (InputStream reader = new FileInputStream(existing.toFile())) {
                TransactionProbe.write(existing.toString(), dictionary(1));
                ByteArrayOutputStream retained = new ByteArrayOutputStream(); int c;
                while ((c = reader.read()) != -1) retained.write(c);
                check(Arrays.equals(retained.toByteArray(), sentinel), "old-reader-isolated");
            }
            check(!identity(existing).get("ino").equals(inode), "inode-replaced");
            check(Files.getPosixFilePermissions(existing).equals(mode("rw-------")), "existing-private-mode"); cases++;
            Map error = new LinkedHashMap() { public int size() { throw new AssertionError("synthetic-error"); } };
            for (Object value : Arrays.asList(failure(false), failure(true), error)) {
                Path target = root.resolve("failed-" + cases); Files.write(target, sentinel); Files.setPosixFilePermissions(target, mode("rw-r--r--"));
                Map<String,Object> before = identity(target); Set<String> names = listing(root);
                Throwable result = save(target, value);
                check(result != null && (value == error ? result.getClass() == AssertionError.class && "synthetic-error".equals(result.getMessage()) : result.getClass() == ClassCastException.class), "failure-type");
                check(result.getSuppressed().length == 0, "failure-cleanup");
                check(Files.exists(target), "failure-original-present");
                check(before.equals(identity(target)) && Arrays.equals(Files.readAllBytes(target), sentinel), "failure-original-unchanged");
                check(names.equals(listing(root)), "failure-no-temporary"); cases++;
            }
            Path linked = root.resolve("linked"); Files.createSymbolicLink(linked, existing); rejected(linked, "atomic-target-policy", root); cases++;
            Path dangling = root.resolve("dangling"); Files.createSymbolicLink(dangling, root.resolve("absent")); rejected(dangling, "atomic-target-policy", root); check(!Files.exists(root.resolve("absent")), "dangling-no-create"); cases++;
            rejected(root.resolve("directory"), "atomic-target-policy", root); cases++;
            rejected(root.resolve("fifo"), "atomic-target-policy", root); cases++;
            rejected(root.resolve("missing-parent/file"), "atomic-parent-open", root); cases++;
            rejected(root.resolve("acl-parent/profile"), "atomic-parent-policy", root); check(!Files.exists(root.resolve("acl-parent/profile")), "acl-parent-no-create"); cases++;
            rejected(root.resolve("public-parent/profile"), "atomic-parent-policy", root); cases++;
            rejected(root.resolve("group-parent/profile"), "atomic-parent-policy", root); cases++;
            rejected(root.resolve("allow-parent/profile"), "atomic-parent-policy", root); cases++;
            rejected(root.resolve("inherit-deny-parent/profile"), "atomic-parent-policy", root); cases++;
            TransactionProbe.write(root.resolve("deny-parent/profile").toString(), dictionary(1));
            check(Files.getPosixFilePermissions(root.resolve("deny-parent/profile")).equals(mode("rw-------")), "deny-parent-accepted"); cases++;
            for (String permission : new String[]{"r--------", "r--r--r--"}) {
                Path target = root.resolve("readonly-" + permission); Files.write(target, sentinel); Files.setPosixFilePermissions(target, mode(permission));
                Map<String,Object> before = identity(target);
                Throwable original = null;
                try { write.invoke(null, target.toString(), dictionary(1)); }
                catch (InvocationTargetException failure) { original = failure.getCause(); }
                check(original instanceof FileNotFoundException, "reference-readonly-rejected");
                rejected(target, "atomic-target-unwritable", root);
                check(before.equals(identity(target)) && Arrays.equals(Files.readAllBytes(target), sentinel), "readonly-unchanged"); cases++;
            }
            Path denyWrite = root.resolve("deny-write-file"); Map<String,Object> denyBefore = identity(denyWrite);
            Throwable denyOriginal = null;
            try { write.invoke(null, denyWrite.toString(), dictionary(1)); }
            catch (InvocationTargetException failure) { denyOriginal = failure.getCause(); }
            check(denyOriginal instanceof FileNotFoundException, "reference-deny-write-rejected");
            rejected(denyWrite, "atomic-target-unwritable", root);
            check(denyBefore.equals(identity(denyWrite)) && Arrays.equals(Files.readAllBytes(denyWrite), sentinel), "deny-write-unchanged"); cases++;
            Path freeze = root.resolve("freeze-at-commit"); Files.write(freeze, sentinel); Files.setPosixFilePermissions(freeze, mode("rw-------"));
            final boolean[] freezeHook = {false};
            Throwable freezeFailure = null;
            try { TransactionProbe.writeWithHook(freeze.toString(), dictionary(1), () -> {
                try { freezeHook[0] = true; Files.setPosixFilePermissions(freeze, mode("r--------")); }
                catch (IOException failure) { throw new RuntimeException(failure); }
            }); } catch (Throwable failure) { freezeFailure = failure; }
            check(freezeHook[0], "commit-readonly-hook");
            check(freezeFailure instanceof IOException && "atomic-target-unwritable-at-commit".equals(freezeFailure.getMessage()), "commit-readonly-rejected");
            check(Arrays.equals(Files.readAllBytes(freeze), sentinel) && Files.getPosixFilePermissions(freeze).equals(mode("r--------")), "commit-readonly-unchanged"); cases++;
            Path hardTarget = root.resolve("hard-target"), hard = root.resolve("hard-alias"); Files.write(hardTarget, sentinel); Files.setPosixFilePermissions(hardTarget, mode("rw-------")); Files.createLink(hard, hardTarget);
            TransactionProbe.write(hardTarget.toString(), dictionary(1)); check(Arrays.equals(Files.readAllBytes(hard), sentinel), "hardlink-old-content");
            check(Arrays.equals(Files.readAllBytes(hardTarget), Files.readAllBytes(root.resolve("old-1"))), "hardlink-new-content"); cases++;
            Path acl = root.resolve("acl-file"); TransactionProbe.write(acl.toString(), dictionary(1));
            check(Files.getPosixFilePermissions(acl).equals(mode("rw-------")), "acl-target-private"); cases++;
            for (boolean present : new boolean[]{true, false}) {
                Path target = root.resolve("race-" + present); if (present) { Files.write(target, sentinel); Files.setPosixFilePermissions(target, mode("rw-------")); }
                final Path replacement = root.resolve("replacement-" + present); Files.write(replacement, new byte[]{4, 5, 6});
                Throwable caught = null;
                try { TransactionProbe.writeWithHook(target.toString(), dictionary(1), () -> {
                    try { Files.move(replacement, target, StandardCopyOption.REPLACE_EXISTING); }
                    catch (IOException failure) { throw new RuntimeException(failure); }
                }); } catch (Throwable failure) { caught = failure; }
                check(caught instanceof IOException && "atomic-target-changed".equals(caught.getMessage()), "concurrent-target-rejected");
                check(Arrays.equals(Files.readAllBytes(target), new byte[]{4, 5, 6}), "concurrent-target-unchanged"); cases++;
            }
            Path swapTarget = root.resolve("swap-target"), retainedTemp = root.resolve("retained-temporary"); Files.write(swapTarget, sentinel); Files.setPosixFilePermissions(swapTarget, mode("rw-------"));
            final Path[] foreign = new Path[1]; Throwable swapFailure = null;
            try { TransactionProbe.writeWithHook(swapTarget.toString(), dictionary(1), () -> {
                try {
                    for (String name : listing(root)) if (name.startsWith(".xra-")) { check(foreign[0] == null, "one-private-temporary"); foreign[0] = root.resolve(name); }
                    check(foreign[0] != null, "private-temporary-found");
                    Files.move(foreign[0], retainedTemp); Files.write(foreign[0], new byte[]{4, 5, 6});
                } catch (IOException failure) { throw new RuntimeException(failure); }
            }); } catch (Throwable failure) { swapFailure = failure; }
            check(swapFailure instanceof IOException && swapFailure.getMessage().startsWith("atomic-temporary-changed"), "temporary-swap-rejected");
            check(Files.exists(foreign[0]), "foreign-temporary-not-deleted");
            check("atomic-temporary-changed+leftover".equals(swapFailure.getMessage()), "temporary-swap-cleanup-reported");
            check(Arrays.equals(Files.readAllBytes(foreign[0]), new byte[]{4, 5, 6}), "foreign-temporary-unchanged");
            check(Arrays.equals(Files.readAllBytes(swapTarget), sentinel), "swap-target-unchanged");
            // Delete only the two known fixture files created/moved by this test hook.
            Files.delete(foreign[0]); Files.delete(retainedTemp); cases++;
            com.sun.management.UnixOperatingSystemMXBean os = (com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
            Path lifetime = root.resolve("lifetime");
            for (Object value : Arrays.asList(dictionary(0), failure(false), error)) {
                for (int i = 0; i < 4; i++) save(lifetime, value);
                os.getOpenFileDescriptorCount(); long before = os.getOpenFileDescriptorCount(), collections = gc(); check(before >= 3, "fd-counter");
                for (int i = 0; i < 32; i++) save(lifetime, value);
                check(os.getOpenFileDescriptorCount() == before, "fd-lifetime"); check(gc() == collections, "gc-lifetime"); cases++;
            }
            for (String scenario : new String[]{"parent", "target", "unwritable"}) {
                Path rejection = scenario.equals("parent") ? root.resolve("allow-parent/rejected") : scenario.equals("target") ? root.resolve("linked") : denyWrite;
                String expected = scenario.equals("parent") ? "atomic-parent-policy" : scenario.equals("target") ? "atomic-target-policy" : "atomic-target-unwritable";
                for (int i=0;i<4;i++) rejected(rejection, expected, root);
                long before = os.getOpenFileDescriptorCount(), collections = gc(); check(before >= 3, "rejection-fd-counter");
                for (int i=0;i<32;i++) rejected(rejection, expected, root);
                check(os.getOpenFileDescriptorCount() == before, "rejection-fd-lifetime"); check(gc() == collections, "rejection-gc-lifetime"); cases++;
            }
            for (String name : tree(root)) check(!Paths.get(name).getFileName().toString().startsWith(".xra-"), "no-temporary-leftovers");
            check(cases == 37, "case-count");
            System.out.println("PASS atomic preference experiment; cases=37; old_readers_isolated=true; serialization_failures_preserve_original=true; fd_delta=0");
        }
    }
}
