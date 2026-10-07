package atomicfixture;
import java.io.*;
/** Pure Java controls; no library, native session, profile or file access. */
public final class SuppressionObservation {
    static void check(boolean value) { if (!value) throw new AssertionError("atomic-suppression:primary"); }
    static final class Disabled extends Error { Disabled() { super("fixture-disabled", null, false, false); } }
    public static void main(String[] arguments) {
        final OutOfMemoryError self = new OutOfMemoryError("fixture-self");
        AtomicPreferenceFile.preserveSuppression(self, self); check(self.getSuppressed().length == 0);
        final IOException cleanup = new IOException("fixture-cleanup");
        Error primary = new Error("fixture-primary"); AtomicPreferenceFile.preserveSuppression(primary, cleanup);
        check(primary.getSuppressed().length == 1 && primary.getSuppressed()[0] == cleanup);
        Disabled disabled = new Disabled(); AtomicPreferenceFile.preserveSuppression(disabled, cleanup); check(disabled.getSuppressed().length == 0);
        System.out.println("PASS atomic suppression; cases=3; primary_preserved=true");
    }
}
