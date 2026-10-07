package compat;
import java.awt.GraphicsEnvironment;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import java.util.concurrent.atomic.AtomicBoolean;

/** At most one fixed diagnostic per result category; never render user data. */
final class PreferenceSaveFailure {
    interface Reporter { void report(int result); }
    private static final AtomicBoolean failedReported = new AtomicBoolean(), uncertainReported = new AtomicBoolean(), committedReported = new AtomicBoolean();
    private static Reporter reporter = new Reporter() {
        public void report(final int result) {
            System.err.println(result == 2 ? "RAID_ADMIN_PREFERENCES_SAVE_UNCONFIRMED" : result == 1 ? "RAID_ADMIN_PREFERENCES_COMMITTED_CLEANUP_FAILED" : "RAID_ADMIN_PREFERENCES_SAVE_FAILED");
            if (Boolean.getBoolean("raid.admin.gui") && !GraphicsEnvironment.isHeadless()) SwingUtilities.invokeLater(new Runnable() {
                public void run() {
                    try {
                        JOptionPane.showMessageDialog(null, result == 2
                            ? "RAID Admin could not confirm the preference save. The file may already contain your changes. Restart RAID Admin when convenient."
                            : result == 1
                            ? "Preferences were saved. Resource cleanup reported a warning. Restart RAID Admin when convenient."
                            : "RAID Admin could not save its preferences. Changes remain in memory. Check folder and file ownership, permissions and link configuration.",
                            "RAID Admin", result==0 ? JOptionPane.ERROR_MESSAGE : JOptionPane.WARNING_MESSAGE);
                    } catch (Throwable ignored) { /* Diagnostics cannot change save handling. */ }
                }
            });
        }
    };
    private static boolean claim(int result) {
        return (result == 2 ? uncertainReported : result == 1 ? committedReported : failedReported).compareAndSet(false,true);
    }
    static void report(Throwable failure) {
        try {
            String code = failure instanceof java.io.IOException ? failure.getMessage() : null;
            int result = "atomic-committed:close".equals(code) ? 1
                : code != null && (code.equals("atomic-rename-uncertain") || code.equals("atomic-rename-uncertain+close") || code.equals("atomic-rename-uncertain+leftover") || code.equals("atomic-rename-uncertain+leftover+close")) ? 2 : 0;
            if (claim(result)) reporter.report(result);
        } catch (Throwable ignored) { /* Preserve the primary exception or Error. */ }
    }
    private PreferenceSaveFailure() {}
}
