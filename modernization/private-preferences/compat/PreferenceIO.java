package compat;
import java.io.IOException;
/** Preserve original caller catch/count/monitor semantics; report fixed failures. */
public final class PreferenceIO {
    private PreferenceIO() {}
    public static void write(String identifier, Object dictionary) throws IOException {
        try { PrivatePreferenceFile.write(identifier, dictionary); }
        catch (IOException | RuntimeException failure) { try { PreferenceSaveFailure.report(failure); } catch (Throwable ignored) { } throw failure; }
    }
}
