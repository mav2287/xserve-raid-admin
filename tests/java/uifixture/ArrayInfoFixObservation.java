package uifixture;

import com.apple.xsr.DriveSelectionPanel;
import fixture.FixtureIdentity;
import fixture.OfflineGuard;
import java.awt.CardLayout;
import java.awt.Color;
import java.awt.Graphics;
import java.awt.Image;
import java.awt.image.BufferedImage;
import java.beans.PropertyChangeEvent;
import java.beans.PropertyChangeListener;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Arrays;
import javax.swing.ImageIcon;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JProgressBar;
import javax.swing.JRadioButton;
import javax.swing.SwingUtilities;

/** Actual information listener and null-system refresh; no app or legacy profile initialization. */
public final class ArrayInfoFixObservation {
    public static final class Panel extends DriveSelectionPanel {
        int calls;
        public Panel() { super(4, null, null, null, null); } // Never executed.
        @Override public Image createImage(int w, int h) { return new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB); }
        @Override public void syncSummary() {} // Model-dependent wizard summary excluded.
        @Override public void setArrayIndex(int id) { calls++; super.setArrayIndex(id); }
    }
    // Constructors are never run: SelectableLabel -> Gestalt initializes legacy preferences.
    public static final class Label extends com.apple.xsr.SelectableLabel {
        String text;
        @Override public void setText(String value) { text = value; }
        @Override public void setVisible(boolean value) {}
    }
    public static final class Status extends com.apple.xsr.SelectableStatusLabel {
        String text; int status;
        @Override public void setText(String value) { text = value; }
        @Override public void setStatus(int value) { status = value; }
    }
    static Field field(Class<?> cls, String name) throws Exception {
        Field f = cls.getDeclaredField(name); f.setAccessible(true); return f;
    }
    static void put(Object target, Class<?> cls, String name, Object value) throws Exception { field(cls, name).set(target, value); }
    static void check(boolean value, String code) {
        if (!value) throw new AssertionError("array-info:" + code);
    }
    static void observe() throws Exception {
        com.apple.xsr.Resources.load();
        check(DriveSelectionPanel.class.getField("INDEX_NONE").getInt(null) == -10, "sentinel");
        Field uf = sun.misc.Unsafe.class.getDeclaredField("theUnsafe"); uf.setAccessible(true);
        sun.misc.Unsafe unsafe = (sun.misc.Unsafe)uf.get(null);
        final Panel panel = (Panel)unsafe.allocateInstance(Panel.class);
        final int[] memberships = {1, 0, 2, 3, 4, 5, 6, -2, 0, -3, 1, 2, 0, 0};
        int[] states = new int[14];
        for (int i = 0; i < 14; i++) states[i] = memberships[i] == 0 ? 0 : -2;
        int[] initialStates = states.clone(), initialMemberships = memberships.clone();
        final JLabel[] icons = new JLabel[14];
        for (int i = 0; i < 14; i++) icons[i] = new JLabel();
        BufferedImage base = new BufferedImage(18, 68, BufferedImage.TYPE_INT_ARGB);
        Graphics g = base.getGraphics(); g.setColor(Color.GRAY); g.fillRect(0, 0, 18, 68); g.dispose();
        put(panel, DriveSelectionPanel.class, "driveArrays", memberships);
        put(panel, DriveSelectionPanel.class, "driveStates", states);
        put(panel, DriveSelectionPanel.class, "driveIcon", icons);
        put(panel, DriveSelectionPanel.class, "presentImage", base);
        put(panel, DriveSelectionPanel.class, "selectionMode", 4);
        put(panel, DriveSelectionPanel.class, "addNotifyCalled", true);
        panel.setArrayIndex(1);
        final int selectedPixel = pixel(icons[0]), basePixel = base.getRGB(3, 3);
        check(selectedPixel != basePixel, "tint-oracle");

        final Class<?> infoClass = Class.forName("com.apple.xsr.SystemInfoPane$ArrayDrivePanel");
        final Object info = unsafe.allocateInstance(infoClass);
        for (Field f : infoClass.getDeclaredFields()) {
            if (java.lang.reflect.Modifier.isStatic(f.getModifiers())) continue;
            Object value = null;
            if (f.getType() == com.apple.xsr.SelectableLabel.class) value = unsafe.allocateInstance(Label.class);
            if (f.getType() == com.apple.xsr.SelectableStatusLabel.class) value = unsafe.allocateInstance(Status.class);
            if (f.getType() == JLabel.class) value = new JLabel();
            if (f.getType() == JProgressBar.class) value = new JProgressBar();
            if (f.getName().equals("messagePanel")) value = unsafe.allocateInstance(f.getType()); // Invisible; setVisible(false) is a no-op.
            if (value != null) { f.setAccessible(true); f.set(info, value); }
        }
        final JRadioButton radio = new JRadioButton();
        CardLayout layout = new CardLayout(); final JPanel cards = new JPanel(layout);
        final JPanel arraysCard = new JPanel(), drivesCard = new JPanel();
        cards.add(arraysCard, "arrays"); cards.add(drivesCard, "drives");
        put(info, infoClass, "drivePanel", panel); put(info, infoClass, "arraysRadioButton", radio);
        put(info, infoClass, "cardLayout", layout); put(info, infoClass, "cardPanel", cards);
        Class<?> listenerClass = Class.forName("com.apple.xsr.SystemInfoPane$5");
        Constructor<?> ctor = listenerClass.getDeclaredConstructor(infoClass); ctor.setAccessible(true);
        final PropertyChangeListener listener = (PropertyChangeListener)ctor.newInstance(info);
        final boolean fixed = Boolean.parseBoolean(System.getProperty("fixture.fixed"));
        if (fixed) {
            try {
                Class.forName("compat.ArrayInfoSelection").getMethod("setArrayIndex", DriveSelectionPanel.class, int.class)
                    .invoke(null, null, 0);
                throw new AssertionError("array-info:null-behavior");
            } catch (java.lang.reflect.InvocationTargetException expected) {
                check(expected.getCause() instanceof NullPointerException, "null-behavior");
            }
        }
        for (int id : new int[]{1, 2, 3, 4, 5, 6, -2, -3, -10, 0, 1, 0, 2}) {
            int calls = panel.calls;
            layout.show(cards, "drives"); radio.setSelected(false);
            listener.propertyChange(new PropertyChangeEvent(info, "ArrayIndex", -1, id));
            int effective = fixed && id == 0 ? -10 : id;
            check(panel.calls == calls + 1 && panel.getArrayIndex() == effective, "forwarding");
            check(field(infoClass, "selectedArray").getInt(info) == id - 1, "detail-selection");
            check(panel.getSelectionMode() == 4 && radio.isSelected() && arraysCard.isVisible() && !drivesCard.isVisible(), "view-state");
            check(((Status)field(infoClass, "arrayStatus").get(info)).status == -3, "null-system-refresh");
            for (int i = 0; i < 14; i++) check(pixel(icons[i]) == (memberships[i] == effective ? selectedPixel : basePixel), "pixels");
        }
        // The old listener must fail the FIXED oracle specifically at forwarding.
        if (Boolean.getBoolean("fixture.requireFixed")) {
            listener.propertyChange(new PropertyChangeEvent(info, "ArrayIndex", -1, 0));
            check(panel.getArrayIndex() == -10, "missing-fix");
        }
        // Actual cleared-row radio event, feeding the original/candidate listener.
        Class<?> rowClass = Class.forName("com.apple.xsr.ArraySelectionPanel$ArrayLabel");
        Object row = rowClass.newInstance();
        rowClass.getMethod("createButton", Class.class, boolean.class).invoke(row, JRadioButton.class, false);
        rowClass.getMethod("addActionListener", java.awt.event.ActionListener.class).invoke(row,
            new java.awt.event.ActionListener() { public void actionPerformed(java.awt.event.ActionEvent event) {
                listener.propertyChange(new PropertyChangeEvent(event.getSource(), "ArrayIndex", -1, 0));
            }});
        JLabel description = (JLabel)rowClass.getMethod("createDescriptionLabel").invoke(row);
        rowClass.getMethod("clear").invoke(row);
        for (java.awt.event.MouseListener mouse : description.getMouseListeners())
            mouse.mouseReleased(new java.awt.event.MouseEvent(description, java.awt.event.MouseEvent.MOUSE_RELEASED, 0L, 0, 1, 1, 1, false));
        check(panel.getArrayIndex() == (fixed ? -10 : 0), "radio-row");
        panel.setSelectionMode(3); panel.setSelectionMode(4);
        for (int i = 0; i < 14; i++) check(pixel(icons[i]) == (!fixed && memberships[i] == 0 ? selectedPixel : basePixel), "mode-transition");
        // Repeated listener calls in compiled mode; real info listener and refresh remain executed.
        for (int i = 0; i < 100; i++) listener.propertyChange(new PropertyChangeEvent(info, "ArrayIndex", -1, i % 7));
        check(Arrays.equals(states, initialStates) && Arrays.equals(memberships, initialMemberships), "model-unchanged");
        check(field(infoClass, "system").get(info) == null, "no-model");
    }
    static int pixel(JLabel label) { return ((BufferedImage)((ImageIcon)label.getIcon()).getImage()).getRGB(3, 3); }
    public static void main(String[] args) throws Exception {
        check("true".equals(System.getProperty("java.awt.headless")), "headless");
        check(System.getProperty("os.arch").equals(System.getProperty("fixture.expectedArch")), "architecture");
        OfflineGuard.install(); FixtureIdentity.verify();
        final Throwable[] failure = new Throwable[1];
        SwingUtilities.invokeAndWait(new Runnable() { public void run() {
            try { observe(); } catch (Throwable value) { failure[0] = value; }
        }});
        OfflineGuard.assertUntouched();
        if (failure[0] != null) {
            if (failure[0] instanceof AssertionError && "array-info:missing-fix".equals(failure[0].getMessage()))
                System.out.println("EXPECTED_NEGATIVE missing-fix");
            else {
                for (Throwable value = failure[0]; value != null; value = value.getCause()) {
                    System.out.println(value.getClass().getName());
                    for (StackTraceElement element : value.getStackTrace()) System.out.println(element.getClassName() + "." + element.getMethodName());
                }
            }
            throw new AssertionError("array-info-fixture-failed");
        }
        OfflineGuard.assertUntouched();
        System.out.println("PASS array info listener; fixed=" + System.getProperty("fixture.fixed") + "; valid_ids_preserved=true; raw_detail_selection_preserved=true; setter_once=true; radio_card_preserved=true; mode_transition=true; model_unchanged=true; forbidden_operations=0");
    }
}
