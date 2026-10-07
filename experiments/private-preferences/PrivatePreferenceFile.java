package privatefixture;

import com.apple.util.plist.PropertyListUtilities;
import java.io.*;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.*;
import java.nio.file.*;

/** Experimental fixture only: not included by the application build or launcher. */
public final class PrivatePreferenceFile {
    private static final class Library {
        static final boolean AVAILABLE = load();
        private static boolean load() {
            try {
                String path = System.getProperty("fixture.private.library");
                if (path == null || !new File(path).isAbsolute()) return false;
                System.load(path); return true;
            } catch (LinkageError | RuntimeException failure) { return false; }
        }
    }
    private PrivatePreferenceFile() {}
    private static native void open0(byte[] path, FileDescriptor descriptor) throws IOException;
    static native int flags0(FileDescriptor descriptor) throws IOException;

    private static byte[] path(String identifier) throws IOException {
        // A deliberately mandatory fixture boundary; never call this on a real profile.
        Path root = Paths.get(System.getProperty("fixture.directory")).toRealPath();
        File file = new File(identifier).getAbsoluteFile();
        if (identifier.indexOf('\0') >= 0) throw new IOException("private-fixture-path");
        for (String component : file.getPath().split("/"))
            if (component.equals(".") || component.equals("..")) throw new IOException("private-fixture-path");
        SecurityManager manager = System.getSecurityManager();
        if (manager != null) manager.checkWrite(file.getPath());
        ByteBuffer encoded = StandardCharsets.UTF_8.newEncoder()
            .onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
            .encode(CharBuffer.wrap(file.getPath()));
        byte[] bytes = new byte[encoded.remaining()];
        encoded.get(bytes);
        Path value = file.toPath().normalize();
        if (!value.startsWith(root) || value.equals(root)) throw new IOException("private-fixture-path");
        try {
            if (!value.getParent().toRealPath().startsWith(root)) throw new IOException("private-fixture-path");
        } catch (NoSuchFileException missing) { /* Native open must reject the missing parent. */ }
        return bytes;
    }

    static FileOutputStream open(String identifier) throws IOException {
        if (!Library.AVAILABLE) throw new IOException("private-library-unavailable");
        byte[] bytes = path(identifier);
        FileDescriptor descriptor = new FileDescriptor();
        // Attachment and descriptor permission checks occur BEFORE native open.
        FileOutputStream output = new FileOutputStream(descriptor);
        try {
            open0(bytes, descriptor);
            return output;
        } catch (Throwable failure) {
            try { output.close(); }
            catch (Throwable closeFailure) { failure.addSuppressed(closeFailure); }
            throw failure;
        }
    }

    public static void write(String identifier, Object dictionary) throws IOException {
        try (OutputStream output = open(identifier)) {
            OutputStreamWriter writer = new OutputStreamWriter(output, "UTF-8");
            PropertyListUtilities.writeXML(dictionary, writer);
            writer.flush();
            // Keep original failure buffering: close the raw stream, not the Writer.
        }
    }
}
