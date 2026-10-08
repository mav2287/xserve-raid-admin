package uifixture;

import com.apple.xsr.DriveSelectionPanel;
import fixture.FixtureIdentity;
import fixture.OfflineGuard;
import java.awt.Color;
import java.awt.Graphics;
import java.awt.Image;
import java.awt.image.BufferedImage;
import java.lang.reflect.Field;
import java.util.Arrays;
import javax.swing.ImageIcon;
import javax.swing.JLabel;
import javax.swing.SwingUtilities;

/** Headless rendering boundary only: no models, controllers, profiles or app startup. */
public final class ArrayHighlightObservation {
    public static final class Panel extends DriveSelectionPanel {
        // Required for compilation, deliberately never executed.
        public Panel() { super(4, null, null, null, null); }
        @Override public Image createImage(int width, int height) {
            return new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        }
        // Exclude the unrelated model-dependent summary UI from this observation.
        @Override public void syncSummary() {}
    }
    static void set(Panel panel, String name, Object value) throws Exception {
        Field field = DriveSelectionPanel.class.getDeclaredField(name);
        field.setAccessible(true); field.set(panel, value);
    }
    static void check(boolean value) {
        if (!value) throw new AssertionError("array-highlight-observation");
    }
    static void observe() throws Exception {
        com.apple.xsr.Resources.load();
        Field field = sun.misc.Unsafe.class.getDeclaredField("theUnsafe");
        field.setAccessible(true);
        Panel panel = (Panel)((sun.misc.Unsafe)field.get(null)).allocateInstance(Panel.class);
        int[] arrays = new int[14], states = new int[14];
        Arrays.fill(states, -2);
        for (int i = 0; i < 14; i++) arrays[i] = i < 7 ? 1 : 2;
        JLabel[] labels = new JLabel[14];
        for (int i = 0; i < 14; i++) labels[i] = new JLabel();
        BufferedImage base = new BufferedImage(18, 68, BufferedImage.TYPE_INT_ARGB);
        Graphics graphics = base.getGraphics();
        graphics.setColor(Color.GRAY); graphics.fillRect(0, 0, 18, 68); graphics.dispose();
        set(panel, "driveArrays", arrays); set(panel, "driveStates", states);
        set(panel, "driveIcon", labels); set(panel, "presentImage", base);
        set(panel, "selectionMode", 4); set(panel, "addNotifyCalled", true);
        panel.setArrayIndex(1);
        int selected = ((BufferedImage)((ImageIcon)labels[0].getIcon()).getImage()).getRGB(3, 3);
        check(selected != base.getRGB(3, 3));
        for (int iteration = 0; iteration < 1000; iteration++) {
            int array = iteration % 2 + 1;
            panel.setArrayIndex(array);
            for (int i = 0; i < 14; i++) {
                BufferedImage image = (BufferedImage)((ImageIcon)labels[i].getIcon()).getImage();
                check(image.getRGB(3, 3) == (arrays[i] == array ? selected : base.getRGB(3, 3)));
                check(states[i] == -2 && arrays[i] == (i < 7 ? 1 : 2));
            }
        }
        // Array selection after individual-drive display: the old drive highlight must clear.
        set(panel, "driveIndex", 1);
        panel.setSelectionMode(3);
        check(((BufferedImage)((ImageIcon)labels[1].getIcon()).getImage()).getRGB(3, 3) == selected);
        panel.setArrayIndex(2); panel.setSelectionMode(4);
        for (int i = 0; i < 14; i++)
            check(((BufferedImage)((ImageIcon)labels[i].getIcon()).getImage()).getRGB(3, 3)
                == (i >= 7 ? selected : base.getRGB(3, 3)));
        // Preserve and observe the original sentinel behavior, rather than assuming
        // all selected drives must occupy a complete controller bank.
        int[] mixed = {1, 0, 1, 1, 1, 1, 0, 2, 0, 0, 0, 0, 0, 0};
        System.arraycopy(mixed, 0, arrays, 0, 14);
        for (int i = 0; i < 14; i++) states[i] = arrays[i] == 0 ? 0 : -2;
        // Observe both description-label paths, including the info view's hidden radio.
        Class<?> rowClass = Class.forName("com.apple.xsr.ArraySelectionPanel$ArrayLabel");
        for (boolean withRadio : new boolean[]{false, true}) {
        final Object row = rowClass.newInstance();
        final int[] rowEvent = {-999};
        rowClass.getMethod("addActionListener", java.awt.event.ActionListener.class).invoke(row,
            new java.awt.event.ActionListener() { public void actionPerformed(java.awt.event.ActionEvent event) {
                try {
                    check("ArrayIndex".equals(event.getActionCommand()) && event.getSource() == row);
                    Field id = row.getClass().getDeclaredField("id"); id.setAccessible(true);
                    rowEvent[0] = id.getInt(row);
                } catch (Exception problem) { throw new AssertionError("row-event-observation"); }
            }});
        javax.swing.JToggleButton button = withRadio
            ? (javax.swing.JToggleButton)rowClass.getMethod("createButton", Class.class, boolean.class)
                .invoke(row, javax.swing.JRadioButton.class, false) : null;
        JLabel description = (JLabel)rowClass.getMethod("createDescriptionLabel").invoke(row);
        rowClass.getMethod("clear").invoke(row);
        for (java.awt.event.MouseListener listener : description.getMouseListeners())
            listener.mouseReleased(new java.awt.event.MouseEvent(description,
                java.awt.event.MouseEvent.MOUSE_RELEASED, 0L, 0, 1, 1, 1, false));
        check(rowEvent[0] == 0);
        if (withRadio) check(!button.isVisible() && button.isSelected());
        }
        for (int array : new int[]{1, 2, 0, -10}) {
            panel.setArrayIndex(array);
            for (int i = 0; i < 14; i++)
                check(((BufferedImage)((ImageIcon)labels[i].getIcon()).getImage()).getRGB(3, 3)
                    == (arrays[i] == array ? selected : base.getRGB(3, 3)));
        }
    }
    public static void main(String[] args) throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")));
        check(System.getProperty("os.arch").equals(System.getProperty("fixture.expectedArch")));
        OfflineGuard.install(); FixtureIdentity.verify();
        final Throwable[] failure = new Throwable[1];
        SwingUtilities.invokeAndWait(new Runnable() { public void run() {
            try { observe(); } catch (Throwable problem) { failure[0] = problem; }
        }});
        if (failure[0] != null) {
            // Only exception type and class/method identifiers; never payloads or paths.
            for (Throwable cause = failure[0]; cause != null; cause = cause.getCause()) {
                System.out.println(cause.getClass().getName());
                for (StackTraceElement element : cause.getStackTrace())
                    System.out.println(element.getClassName() + "." + element.getMethodName());
            }
        }
        check(failure[0] == null); OfflineGuard.assertUntouched();
        System.out.println("PASS array highlight; transitions=1000; pixel_checks=14000; drive_to_array=true; cleared_row_paths=2; zero_tints_unassigned=true; minus_ten_clears=true; fresh_buffer_only=true; forbidden_operations=0");
    }
}
