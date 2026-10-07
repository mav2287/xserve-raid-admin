package atomicfixture;

import com.apple.util.plist.PropertyListUtilities;
import java.io.*;
import java.nio.*;
import java.nio.charset.*;
import java.nio.file.*;

/** Nonshipping atomic-save experiment; explicit disposable identifiers only. */
public final class AtomicPreferenceFile {
    private static final class Library {
        static final boolean AVAILABLE = load();
        static boolean load() {
            try {
                String value = System.getProperty("fixture.atomic.library");
                if (value == null || !new File(value).isAbsolute()) return false;
                System.load(value);
                // Loading a stale library without JNI_OnLoad is insufficient. Bind
                // each method without creating a session, descriptor or file.
                try { abort0(0); return false; } catch (IOException expected) { if (!"atomic-session-consumed".equals(expected.getMessage())) return false; }
                try { commit0(0); return false; } catch (IOException expected) { if (!"atomic-session-consumed".equals(expected.getMessage())) return false; }
                try { begin0(null, null, null); return false; } catch (IOException expected) { if (!"atomic-session-state".equals(expected.getMessage())) return false; }
                return version0() == 0x58415201; // Exact experimental native ABI, not a trust boundary.
            } catch (LinkageError | RuntimeException failure) { return false; }
        }
    }
    static final class Session {
        private long handle;
        synchronized void commit() throws IOException {
            long value = handle; handle = 0;
            if (value == 0) throw new IOException("atomic-session-consumed");
            commit0(value);
        }
        synchronized void abort() throws IOException {
            long value = handle; handle = 0;
            if (value != 0) abort0(value);
        }
        void abortPreserving(Throwable primary) {
            try { abort(); } catch (Throwable failure) {
                preserveSuppression(primary, failure);
            }
        }
    }
    // Package-private only for pure-Java suppression controls; Session remains final.
    static void preserveSuppression(Throwable primary, Throwable failure) {
        if (failure != primary) try { primary.addSuppressed(failure); } catch (Throwable ignored) { }
    }
    private static native int version0();
    private static native void begin0(byte[] path, FileDescriptor descriptor, Session owner) throws IOException;
    private static native void commit0(long handle) throws IOException;
    private static native void abort0(long handle) throws IOException;
    private AtomicPreferenceFile() {}

    private static byte[] path(String identifier) throws IOException {
        File file = new File(identifier);
        SecurityManager security = System.getSecurityManager();
        if (security != null) security.checkWrite(file.getPath());
        if (identifier.indexOf('\0') >= 0) throw new FileNotFoundException("Invalid file path");
        for (String component : file.getPath().split("/"))
            if (component.equals(".") || component.equals("..")) throw new IOException("atomic-fixture-path");
        ByteBuffer encoded = StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(file.getPath()));
        byte[] bytes = new byte[encoded.remaining()]; encoded.get(bytes);
        // This boundary is mandatory in this experiment, and must never ship.
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        Path absolute = file.toPath().toAbsolutePath();
        if (!absolute.startsWith(root) || absolute.equals(root)) throw new IOException("atomic-fixture-path");
        try { if (!absolute.getParent().toRealPath().startsWith(root)) throw new IOException("atomic-fixture-path"); }
        catch (NoSuchFileException missing) { /* Native open reports the absent parent. */ }
        return bytes;
    }

    public static void write(String identifier, Object dictionary) throws IOException {
        writeWithHook(identifier, dictionary, null);
    }
    // A deterministic fixture hook; never included in a product helper.
    static void writeWithHook(String identifier, Object dictionary, Runnable hook) throws IOException {
        if (!Library.AVAILABLE) throw new IOException("atomic-library-unavailable");
        byte[] bytes = path(identifier);
        FileDescriptor descriptor = new FileDescriptor(); Session session = new Session();
        try (OutputStream output = new FileOutputStream(descriptor)) {
            begin0(bytes, descriptor, session);
            OutputStreamWriter writer = new OutputStreamWriter(output, "UTF-8");
            PropertyListUtilities.writeXML(dictionary, writer);
            writer.flush();
        } catch (Throwable primary) {
            session.abortPreserving(primary); throw primary;
        }
        // Native consumes the session even when validation/rename fails.
        try {
            if (hook != null) hook.run();
            session.commit();
        } catch (Throwable primary) {
            session.abortPreserving(primary); throw primary;
        }
    }
}
