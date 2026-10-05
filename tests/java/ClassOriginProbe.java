/** Class loading only; does not launch UI, discovery or controller transport. */
public final class ClassOriginProbe {
    public static void main(String[] args) throws Exception {
        for (String name : new String[]{"Launcher", "com.apple.eio.FileManager", "com.apple.mrj.MRJApplicationUtils", "sun.io.MalformedInputException", "com.apple.xsr.net.AcpxMessageFactory"}) {
            try {
                Class<?> cls = Class.forName(name, false, ClassOriginProbe.class.getClassLoader());
                System.out.println(name + "=" + (cls.getClassLoader() == null ? "bootstrap-runtime" : "application-classpath"));
            } catch (ClassNotFoundException absent) { System.out.println(name + "=absent"); }
        }
        System.out.println("sax_factory=" + javax.xml.parsers.SAXParserFactory.newInstance().getClass().getName());
    }
}
