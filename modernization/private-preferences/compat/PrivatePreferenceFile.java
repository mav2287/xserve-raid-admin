package compat;

import com.apple.util.plist.PropertyListUtilities;
import java.io.*;
import java.nio.*;
import java.nio.charset.*;

/** Private atomic preference save using the original serializer and raw stream. */
public final class PrivatePreferenceFile {
    private static final class Library {
        private static int state;
        static synchronized boolean available() {
            if (state == 0) { state = -1; if (load()) state = 1; }
            return state == 1;
        }
        private static boolean load() {
            try {
                java.net.URL location = PrivatePreferenceFile.class.getProtectionDomain().getCodeSource().getLocation();
                if (!"file".equals(location.getProtocol())) return false;
                File jar = new File(location.toURI());
                if (!jar.isFile()) return false;
                File library = new File(new File(jar.getParentFile().getParentFile(), "Frameworks"), "libPrivatePreference.dylib");
                System.load(library.getAbsolutePath());
                // Loading a stale library without JNI_OnLoad is insufficient. Bind
                // each method without creating a session, descriptor or file.
                try { abort0(null); return false; } catch (IOException expected) { if (!"atomic-session-state".equals(expected.getMessage())) return false; }
                try { commit0(null); return false; } catch (IOException expected) { if (!"atomic-session-state".equals(expected.getMessage())) return false; }
                try { begin0(null, null, null); return false; } catch (IOException expected) { if (!"atomic-session-state".equals(expected.getMessage())) return false; }
                return version0() == 0x58415204; // Exact production native ABI, not a trust boundary.
            } catch (Throwable failure) { return false; }
        }
    }
    static final class Session {
        private long handle;
        synchronized void commit() throws IOException {
            if (handle == 0) throw new IOException("atomic-session-consumed");
            commit0(this);
        }
        synchronized void abort() throws IOException {
            if (handle != 0) abort0(this);
        }
        void abortPreserving(Throwable primary) {
            try { abort(); } catch (Throwable failure) {
                preserveSuppression(primary, failure);
            }
        }
    }
    // Cleanup must never replace the original serialization failure.
    static void preserveSuppression(Throwable primary, Throwable failure) {
        if (failure != primary) try { primary.addSuppressed(failure); } catch (Throwable ignored) { }
    }
    private static native int version0();
    private static native void begin0(byte[] path, FileDescriptor descriptor, Session owner) throws IOException;
    private static native void commit0(Session owner) throws IOException;
    private static native void abort0(Session owner) throws IOException;
    private PrivatePreferenceFile() {}

    private static byte[] path(String identifier) throws IOException {
        File file = new File(identifier);
        SecurityManager security = System.getSecurityManager();
        if (security != null) security.checkWrite(file.getPath());
        if (identifier.indexOf('\0') >= 0) throw new FileNotFoundException("Invalid file path");
        ByteBuffer encoded;
        try { encoded = StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(file.getPath())); }
        catch (CharacterCodingException invalid) { throw new IOException("atomic-path-encoding"); }
        byte[] bytes = new byte[encoded.remaining()]; encoded.get(bytes);
        return bytes;
    }

    public static void write(String identifier, Object dictionary) throws IOException {
        byte[] bytes = path(identifier);
        if (!Library.available()) throw new IOException("atomic-library-unavailable");
        FileDescriptor descriptor = new FileDescriptor(); Session session = new Session();
        try (OutputStream output = new FileOutputStream(descriptor)) {
            begin0(bytes, descriptor, session);
            OutputStreamWriter writer = new OutputStreamWriter(output, "UTF-8");
            PropertyListUtilities.writeXML(dictionary, writer);
            writer.flush();
        } catch (Throwable primary) {
            try { session.abortPreserving(primary); } catch (Throwable ignored) { }
            throw primary;
        }
        // Native consumes the session even when validation/rename fails.
        try {
            session.commit();
        } catch (Throwable primary) {
            try { session.abortPreserving(primary); } catch (Throwable ignored) { }
            throw primary;
        }
    }
}
