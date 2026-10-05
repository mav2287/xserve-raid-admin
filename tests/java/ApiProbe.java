/** Read-only API availability probe; never initializes the UI. */
public final class ApiProbe {
    public static void main(String[] args) throws Exception {
        Class<?> desktop = Class.forName("java.awt.Desktop", false, ApiProbe.class.getClassLoader());
        boolean about = false;
        try { Class.forName("java.awt.desktop.AboutHandler", false, ApiProbe.class.getClassLoader()); about = true; }
        catch (ClassNotFoundException expected) { }
        System.out.println("desktop_class_present=" + (desktop != null));
        System.out.println("java_awt_desktop_about_handler_present=" + about);
        System.out.println("jdk=" + System.getProperty("java.version"));
        System.out.println("architecture=" + System.getProperty("os.arch"));
    }
}
