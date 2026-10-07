package privatefixture;

import java.io.*;
import java.lang.management.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;

/** Disposable-file observations, not application/GUI or controller qualification. */
public final class PrivatePreferenceObservation {
    static void check(boolean value, String code) {
        if (!value) throw new AssertionError("private-descriptor:" + code);
    }
    static long gc() {
        long value = 0;
        for (GarbageCollectorMXBean b : ManagementFactory.getGarbageCollectorMXBeans()) {
            check(b.getCollectionCount() >= 0, "gc-supported"); value += b.getCollectionCount();
        }
        return value;
    }
    static Map good(int kind) {
        Map value = new LinkedHashMap();
        if (kind == 1) value.put("label", "日本語 é 😃 &<>\" '\n");
        if (kind == 2) value.put("nested", new ArrayList(Arrays.asList(Long.valueOf(12), Boolean.TRUE, new byte[]{0, 1, 2}, new Date(123456789L))));
        if (kind == 3) value.put("large", String.join("", Collections.nCopies(40000, "ü<&")));
        if (kind == 4) value.put("surrogates", "a\ud800b\udc00c\u0001");
        if (kind >= 5) { if (kind == 6) value.put("prefix", String.join("", Collections.nCopies(40000, "x"))); value.put(Integer.valueOf(5), "bad-key"); }
        return value;
    }
    static Throwable save(Method original, Object target, Path path, Object value) throws Exception {
        try {
            if (original == null) PrivatePreferenceFile.write(path.toString(), value);
            else original.invoke(target, path.toString(), value);
            return null;
        } catch (InvocationTargetException e) { return e.getCause(); }
        catch (Throwable e) { return e; }
    }
    static void compare(Method original, Path a, Path b, Object value, boolean interrupt, Class<?> expectedFailure, boolean expectedFlag) throws Exception {
        if (interrupt) Thread.currentThread().interrupt();
        Throwable old = save(original, null, a, value);
        boolean oldFlag = Thread.interrupted();
        if (interrupt) Thread.currentThread().interrupt();
        Throwable now = save(null, null, b, value);
        boolean nowFlag = Thread.interrupted();
        check((old == null && now == null) || (old != null && now != null && old.getClass() == now.getClass()), "failure-type");
        check(expectedFailure == null ? old == null && now == null : old != null && now != null && old.getClass() == expectedFailure && now.getClass() == expectedFailure, "expected-failure-type");
        if (expectedFailure == AssertionError.class) check("synthetic-error".equals(old.getMessage()) && "synthetic-error".equals(now.getMessage()), "expected-error");
        check(oldFlag == nowFlag && (!interrupt || nowFlag), "interrupt");
        check(oldFlag == expectedFlag && nowFlag == expectedFlag, "expected-interrupt");
        check(Arrays.equals(Files.readAllBytes(a), Files.readAllBytes(b)), "bytes");
        check(Files.getPosixFilePermissions(b).equals(PosixFilePermissions.fromString("rw-------")), "private-mode");
    }
    static int number(FileDescriptor descriptor) throws Exception {
        Field field = FileDescriptor.class.getDeclaredField("fd"); field.setAccessible(true); return field.getInt(descriptor);
    }
    static void rejected(Path path, String expected) throws Exception {
        try { PrivatePreferenceFile.write(path.toString(), good(0)); check(false, "policy-not-rejected"); }
        catch (IOException e) { check(e.getSuppressed().length == 0, "suppressed-close"); check(expected.equals(e.getMessage()), "policy-code"); }
    }
    public static void main(String[] arguments) throws Exception {
        check(GraphicsEnvironmentHeadless(), "headless");
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        check(Files.getFileStore(root).type().equals("apfs"), "filesystem-apfs");
        // Initialize only this fixture's explicitly supplied dylib; no app startup.
        Class.forName("privatefixture.PrivatePreferenceFile");
        if (arguments.length == 1 && (arguments[0].equals("deny-descriptor") || arguments[0].equals("deny-path") || arguments[0].equals("missing-library") || arguments[0].equals("unset-library"))) {
            final String operation = arguments[0];
            Path path = root.resolve("permission-sentinel"); byte[] bytes = {1, 2, 3, 4}; Files.write(path, bytes);
            Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rw-r--r--"));
            final com.sun.management.UnixOperatingSystemMXBean os = (com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
            os.getOpenFileDescriptorCount(); long before = os.getOpenFileDescriptorCount();
            check(before >= 3, "fd-count-supported");
            System.setSecurityManager(new SecurityManager() {
                public void checkPermission(java.security.Permission permission) {}
                public void checkWrite(FileDescriptor descriptor) { if (operation.equals("deny-descriptor")) throw new SecurityException("fixture-descriptor-denied"); }
                public void checkWrite(String path) { if (operation.equals("deny-path")) throw new SecurityException("fixture-path-denied"); }
                public void checkConnect(String host, int port) { throw new SecurityException("fixture-network-denied"); }
            });
            for (Path attempt : Arrays.asList(path, root.resolve("not-created"))) {
                try { PrivatePreferenceFile.write(attempt.toString(), good(0)); check(false, "descriptor-permission"); }
                catch (SecurityException expected) { check((operation.equals("deny-descriptor") ? "fixture-descriptor-denied" : "fixture-path-denied").equals(expected.getMessage()), "descriptor-permission-code"); }
                catch (IOException expected) { check((operation.equals("missing-library") || operation.equals("unset-library")) && "private-library-unavailable".equals(expected.getMessage()), "library-failure-code"); }
            }
            check(!Files.exists(root.resolve("not-created")), "denial-no-create");
            check(Arrays.equals(Files.readAllBytes(path), bytes), "descriptor-denial-bytes");
            check(Files.getPosixFilePermissions(path).equals(PosixFilePermissions.fromString("rw-r--r--")), "descriptor-denial-mode");
            check(os.getOpenFileDescriptorCount() == before, "descriptor-denial-close");
            System.out.println("PASS private descriptor " + operation + "; bytes_modes_unchanged=true; fd_delta=0"); return;
        }
        URL jar = new File(System.getProperty("fixture.reference")).toURI().toURL();
        try (URLClassLoader loader = new URLClassLoader(new URL[]{jar}, null)) {
            Class<?> type = Class.forName("compat.PreferenceIO", true, loader);
            check(type.getProtectionDomain().getCodeSource().getLocation().equals(jar), "reference-origin");
            Method original = type.getMethod("write", String.class, Object.class); int cases = 0;
            for (int kind = 0; kind < 7; kind++) {
                compare(original, root.resolve("old-" + kind), root.resolve("new-" + kind), good(kind), false, kind >= 5 ? ClassCastException.class : null, false);
                if (kind == 6) check(Files.size(root.resolve("old-6")) > 8192, "large-failure-partial-bytes"); cases++;
            }
            for (boolean existing : new boolean[]{false, true}) {
                Path a = root.resolve("old-interrupted-" + existing), b = root.resolve("new-interrupted-" + existing);
                if (existing) { Files.write(a, new byte[500000]); Files.write(b, new byte[500000]); Files.setPosixFilePermissions(a, PosixFilePermissions.fromString("rw-r--r--")); Files.setPosixFilePermissions(b, PosixFilePermissions.fromString("rw-r--r--")); }
                compare(original, a, b, good(1), true, null, true); cases++;
            }
            Map interrupted = new LinkedHashMap() { public int size() { Thread.currentThread().interrupt(); return super.size(); } };
            compare(original, root.resolve("old-midinterrupt"), root.resolve("new-midinterrupt"), interrupted, false, null, true); cases++;
            Map error = new LinkedHashMap() { public int size() { throw new AssertionError("synthetic-error"); } };
            compare(original, root.resolve("old-error"), root.resolve("new-error"), error, false, AssertionError.class, false); cases++;
            Path oldFailure = root.resolve("old-existing-failure"), newFailure = root.resolve("new-existing-failure");
            Files.write(oldFailure, new byte[500000]); Files.write(newFailure, new byte[500000]);
            Files.setPosixFilePermissions(oldFailure, PosixFilePermissions.fromString("rw-r--r--")); Files.setPosixFilePermissions(newFailure, PosixFilePermissions.fromString("rw-r--r--"));
            compare(original, oldFailure, newFailure, good(6), false, ClassCastException.class, false); cases++;
            Path target = root.resolve("target"), link = root.resolve("link"), hard = root.resolve("hard");
            byte[] sentinel = {9, 8, 7}; Files.write(target, sentinel); Files.setPosixFilePermissions(target, PosixFilePermissions.fromString("rw-r--r--"));
            Files.createSymbolicLink(link, target); rejected(link, "private-open");
            check(Arrays.equals(Files.readAllBytes(target), sentinel), "link-target-bytes");
            check(Files.getPosixFilePermissions(target).equals(PosixFilePermissions.fromString("rw-r--r--")), "link-target-mode"); cases++;
            Path absent = root.resolve("absent"); Path dangling = root.resolve("dangling"); Files.createSymbolicLink(dangling, absent); rejected(dangling, "private-open"); check(!Files.exists(absent), "dangling-no-target"); cases++;
            Files.createLink(hard, target); rejected(hard, "private-file-policy"); check(Arrays.equals(Files.readAllBytes(target), sentinel), "hardlink-bytes"); cases++;
            rejected(root.resolve("directory"), "private-open"); cases++;
            rejected(root.resolve("fifo"), "private-open"); cases++;
            rejected(root.resolve("acl-file"), "private-file-policy");
            check(Arrays.equals(Files.readAllBytes(root.resolve("acl-file")), sentinel), "acl-bytes"); cases++;
            rejected(root.resolve("acl-parent/new-file"), "private-parent-policy");
            check(!Files.exists(root.resolve("acl-parent/new-file")), "inherited-acl-no-file-created"); cases++;
            rejected(root.resolve("missing-parent/file"), "private-open"); check(!Files.exists(root.resolve("missing-parent")), "missing-parent"); cases++;
            // Swap the path AFTER open: writes must stay on the protected descriptor.
            Path opened = root.resolve("opened"), moved = root.resolve("moved"), replacement = root.resolve("replacement");
            Files.write(replacement, sentinel);
            try (FileOutputStream output = PrivatePreferenceFile.open(opened.toString())) {
                check(PrivatePreferenceFile.flags0(output.getFD()) == 1, "descriptor-flags");
                Files.move(opened, moved); Files.createSymbolicLink(opened, replacement); output.write(new byte[]{4, 5});
            }
            check(Arrays.equals(Files.readAllBytes(moved), new byte[]{4, 5}), "descriptor-inode");
            check(Arrays.equals(Files.readAllBytes(replacement), sentinel), "replacement-not-written"); cases++;
            try (FileOutputStream output = PrivatePreferenceFile.open(root.resolve("descriptor-reuse").toString())) {
                FileDescriptor descriptor = output.getFD(); int old = number(descriptor); output.close(); check(number(descriptor) == -1, "descriptor-invalidated");
                ArrayList<FileOutputStream> held = new ArrayList<>(); boolean reused = false;
                try {
                    for (int i = 0; i < 16; i++) {
                        Path sentinelPath = root.resolve("reuse-sentinel-" + i);
                        FileOutputStream next = new FileOutputStream(sentinelPath.toFile()); held.add(next);
                        if (number(next.getFD()) == old) {
                            reused = true; output.close(); next.write(17); next.flush();
                            check(Arrays.equals(Files.readAllBytes(sentinelPath), new byte[]{17}), "reuse-sentinel"); break;
                        }
                    }
                    check(reused, "descriptor-reused");
                } finally { for (FileOutputStream next : held) next.close(); }
            }
            cases++;
            com.sun.management.UnixOperatingSystemMXBean os = (com.sun.management.UnixOperatingSystemMXBean)ManagementFactory.getOperatingSystemMXBean();
            Path fd = root.resolve("lifetime");
            for (Object dictionary : Arrays.asList(good(0), good(5), error)) {
                for (int i = 0; i < 4; i++) save(null, null, fd, dictionary);
                os.getOpenFileDescriptorCount(); long before = os.getOpenFileDescriptorCount(), collections = gc();
                check(before >= 3, "fd-count-supported");
                for (int i = 0; i < 32; i++) save(null, null, fd, dictionary);
                check(os.getOpenFileDescriptorCount() == before, "lifetime-close"); check(gc() == collections, "lifetime-gc"); cases++;
            }
            for (int i = 0; i < 4; i++) rejected(hard, "private-file-policy");
            long before = os.getOpenFileDescriptorCount(), collections = gc();
            check(before >= 3, "fd-count-supported");
            for (int i = 0; i < 32; i++) rejected(hard, "private-file-policy");
            check(os.getOpenFileDescriptorCount() == before, "rejection-close"); check(gc() == collections, "rejection-gc"); cases++;
            Path originalNames = root.resolve("original-names"), candidateNames = root.resolve("candidate-names"); Files.createDirectory(originalNames); Files.createDirectory(candidateNames);
            Files.setPosixFilePermissions(originalNames, PosixFilePermissions.fromString("rwx------")); Files.setPosixFilePermissions(candidateNames, PosixFilePermissions.fromString("rwx------"));
            int filenameCase = 0;
            for (String name : new String[]{"ascii", "日本語", "é", "e\u0301", "😃"}) {
                Path oldDirectory = Files.createDirectory(originalNames.resolve("case-" + filenameCase)), newDirectory = Files.createDirectory(candidateNames.resolve("case-" + filenameCase)); filenameCase++;
                Files.setPosixFilePermissions(oldDirectory, PosixFilePermissions.fromString("rwx------")); Files.setPosixFilePermissions(newDirectory, PosixFilePermissions.fromString("rwx------"));
                String oldPath = oldDirectory.toString() + "/" + name, newPath = newDirectory.toString() + "/" + name;
                original.invoke(null, oldPath, good(1)); byte[] expected = Files.readAllBytes(new File(oldPath).toPath());
                PrivatePreferenceFile.write(newPath, good(1));
                try (InputStream input = new FileInputStream(new File(newPath))) {
                    ByteArrayOutputStream bytes = new ByteArrayOutputStream(); byte[] buffer = new byte[1024]; int n;
                    while ((n = input.read(buffer)) != -1) bytes.write(buffer, 0, n);
                    check(Arrays.equals(expected, bytes.toByteArray()), "path-encoding-parity");
                }
                cases++;
            }
            for (String name : new String[]{"invalid\0suffix", "invalid\ud800suffix", "invalid\udc00suffix"}) {
                TreeSet<String> listing = new TreeSet<>();
                try (DirectoryStream<Path> entries = Files.newDirectoryStream(root)) { for (Path entry : entries) listing.add(entry.getFileName().toString()); }
                try { PrivatePreferenceFile.write(root.toString() + "/" + name, good(0)); check(false, "invalid-path"); }
                catch (IOException expected) {
                    check(name.indexOf('\0') >= 0 ? expected.getClass() == IOException.class && "private-fixture-path".equals(expected.getMessage()) : expected.getClass() == java.nio.charset.MalformedInputException.class, "invalid-path-outcome");
                }
                TreeSet<String> after = new TreeSet<>();
                try (DirectoryStream<Path> entries = Files.newDirectoryStream(root)) { for (Path entry : entries) after.add(entry.getFileName().toString()); }
                check(listing.equals(after), "invalid-path-no-create");
                check(!Files.exists(root.resolve("invalid?suffix")), "invalid-path-no-substitution"); cases++;
            }
            check(cases == 34, "case-count");
            System.out.println("PASS private descriptor experiment; cases=34; bytes_interrupts_preserved=true; private_modes=true; link_acl_rejections=true; fd_delta=0");
        }
    }
    static boolean GraphicsEnvironmentHeadless() { return java.awt.GraphicsEnvironment.isHeadless(); }
}
