package compat;
import java.io.IOException;
/** Nonshipping adapter for the exact audit27 FileBasedPreferences call site. */
public final class PreferenceIO {
    private PreferenceIO() { }
    public static void write(String identifier, Object value) throws IOException {
        atomicfixture.AtomicPreferenceFile.write(identifier, value);
    }
}
