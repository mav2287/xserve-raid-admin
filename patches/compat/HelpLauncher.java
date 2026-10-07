package compat;

import java.awt.Desktop;
import java.awt.GraphicsEnvironment;
import java.net.URI;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;

/** Browser boundary only. Never rewrites an Apple URL or renders exception details. */
public final class HelpLauncher {
    interface Opener { void open(URI uri) throws Exception; }
    interface Reporter { void report(String code); }
    private HelpLauncher() {}
    private static final class UnsupportedBrowse extends Exception {}
    private static final Opener DESKTOP = new Opener() {
        public void open(URI uri) throws Exception {
            if (GraphicsEnvironment.isHeadless() || !Desktop.isDesktopSupported())
                throw new UnsupportedBrowse();
            Desktop desktop = Desktop.getDesktop();
            if (!desktop.isSupported(Desktop.Action.BROWSE)) throw new UnsupportedBrowse();
            desktop.browse(uri);
        }
    };
    private static final Reporter NOTIFY = new Reporter() {
        public void report(final String code) {
            // Fixed codes only; never print a URL, cause, stack trace or input string.
            System.err.println(code);
            if (GraphicsEnvironment.isHeadless()) return;
            Runnable notice = new Runnable() {
                public void run() {
                    try {
                        JOptionPane.showMessageDialog(null,
                            "RAID Admin could not open this link in your browser.",
                            "RAID Admin", JOptionPane.ERROR_MESSAGE);
                    } catch (RuntimeException ignored) {
                        // Fixed stderr code above remains the fallback.
                    } catch (LinkageError ignored) {}
                }
            };
            try {
                if (SwingUtilities.isEventDispatchThread()) notice.run();
                else SwingUtilities.invokeLater(notice);
            } catch (RuntimeException ignored) {} catch (LinkageError ignored) {}
        }
    };
    public static void openURL(String url) { openURL(url, DESKTOP, NOTIFY); }
    // Package-private, immutable per-call seam for offline fixtures. No public backend setter.
    static void openURL(String url, Opener opener, Reporter reporter) {
        if (url == null || url.trim().length() == 0) { reporter.report("HELP_URL_MISSING"); return; }
        final URI uri;
        try {
            uri = new URI(url);
            if (!uri.isAbsolute()) throw new java.net.URISyntaxException("", "");
        } catch (java.net.URISyntaxException invalid) { reporter.report("HELP_URL_INVALID"); return; }
        try { opener.open(uri); }
        catch (UnsupportedBrowse unsupported) { reporter.report("BROWSE_UNSUPPORTED"); }
        catch (Exception failure) { reporter.report("BROWSE_FAILED"); }
        catch (LinkageError failure) { reporter.report("BROWSE_FAILED"); }
    }
}
