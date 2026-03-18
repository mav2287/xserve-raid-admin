import javax.swing.*;
import java.awt.*;

/**
 * Wrapper entry point that applies UI fixes before launching the original RAID Admin.
 * Fixes white-on-white tab text in the Aqua Look & Feel on modern macOS.
 */
public class Launcher {
    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());

            // Fix tab text colors for modern macOS Aqua L&F
            UIManager.put("TabbedPane.selectedForeground", Color.BLACK);
            UIManager.put("TabbedPane.foreground", Color.BLACK);
            UIManager.put("TabbedPane.selectedTabTitleNormalColor", Color.BLACK);
            UIManager.put("TabbedPane.selectedTabTitlePressedColor", new Color(50, 50, 50));
            UIManager.put("TabbedPane.nonSelectedTabTitleNormalColor", new Color(80, 80, 80));

            UIManager.put("TableHeader.foreground", Color.BLACK);
            UIManager.put("Table.foreground", Color.BLACK);
        } catch (Exception e) {
            // Fall through to defaults
        }

        // Delegate to the original main class
        com.apple.xsr.Main.main(args);
    }
}
