import java.io.File;
import java.net.InetAddress;
import java.net.URL;
import java.security.Permission;

/** Origin/folder lookups only: no app entry point, preference reads, GUI or sockets. */
public final class ClassOriginProbe {
    private static String origin(Class<?> cls) throws Exception {
        java.security.CodeSource source = cls.getProtectionDomain().getCodeSource();
        if (source != null) return "classpath:" + new File(source.getLocation().toURI()).getName();
        URL resource = cls.getResource("/" + cls.getName().replace('.', '/') + ".class");
        if (resource != null && resource.getProtocol().equals("jar")) {
            String archive = resource.toString().split("!", 2)[0];
            return "runtime:" + archive.substring(archive.lastIndexOf('/') + 1);
        }
        return "runtime";
    }
    public static void main(String[] args) throws Exception {
        System.setSecurityManager(new SecurityManager() {
            @Override public void checkPermission(Permission p) { }
            @Override public void checkConnect(String host, int port) { throw new SecurityException("Network prohibited"); }
            @Override public void checkListen(int port) { throw new SecurityException("Network prohibited"); }
            @Override public void checkMulticast(InetAddress address) { throw new SecurityException("Network prohibited"); }
            @Override public void checkWrite(String path) { throw new SecurityException("Writes prohibited"); }
            @Override public void checkDelete(String path) { throw new SecurityException("Deletes prohibited"); }
        });
        for (String name : new String[]{"Launcher", "com.apple.eio.FileManager", "com.apple.mrj.MRJFileUtils", "com.apple.mrj.MRJApplicationUtils", "sun.io.MalformedInputException", "com.apple.xsr.net.AcpxMessageFactory"}) {
            try { System.out.println(name + "=" + origin(Class.forName(name, false, ClassOriginProbe.class.getClassLoader()))); }
            catch (ClassNotFoundException absent) { System.out.println(name + "=absent"); }
        }
        File desktop = com.apple.mrj.MRJFileUtils.findFolder(com.apple.mrj.MRJFileUtils.kDesktopFolderType);
        System.out.println("mrj_desktop_nonnull=" + (desktop != null));
        System.out.println("mrj_desktop_matches_home=" + new File(System.getProperty("user.home"), "Desktop").equals(desktop));
        Class<?> fm = Class.forName("com.apple.eio.FileManager");
        String preferences = (String) fm.getMethod("findFolder", short.class, int.class, boolean.class).invoke(null, (short)-32763, 0x70726566, false);
        System.out.println("runtime_preferences_matches_home=" + new File(System.getProperty("user.home"), "Library/Preferences").getPath().equals(preferences));
        System.out.println("file_encoding=" + System.getProperty("file.encoding"));
        System.out.println("extension_dirs_empty=" + "".equals(System.getProperty("java.ext.dirs")));
        System.out.println("sax_factory=" + javax.xml.parsers.SAXParserFactory.newInstance().getClass().getName());
    }
}
