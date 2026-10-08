package compat;

import com.apple.xsr.SystemInfoPane;
import javax.swing.AbstractButton;
import javax.swing.SwingUtilities;

/** Remove simulated press sleep only from information-view programmatic clicks. */
public final class InfoSelectionClick {
    private InfoSelectionClick() {}

    public static void viewMode(AbstractButton button) {
        button.doClick(0);
    }

    public static void arrayRow(AbstractButton button) {
        if (SwingUtilities.getAncestorOfClass(SystemInfoPane.class, button) != null)
            button.doClick(0);
        else
            button.doClick();
    }
}
