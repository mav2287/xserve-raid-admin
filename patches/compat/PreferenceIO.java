package compat;

import com.apple.util.plist.PropertyListUtilities;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;

/** Own the original noninterruptible stream without flushing buffered failure output. */
public final class PreferenceIO {
    private PreferenceIO() {}
    public static void write(String identifier, Object dictionary) throws IOException {
        try (OutputStream output = new FileOutputStream(new File(identifier))) {
            OutputStreamWriter writer = new OutputStreamWriter(output, "UTF-8");
            PropertyListUtilities.writeXML(dictionary, writer);
            writer.flush();
            // Close only the raw stream: closing the Writer on failure would flush
            // buffered partial XML that the original implementation never wrote.
        }
    }
}
