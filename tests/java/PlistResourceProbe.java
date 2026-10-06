import com.apple.util.plist.PropertyList;
import com.apple.util.plist.PropertyListUtilities;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.Method;
import java.security.MessageDigest;
import java.util.*;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;
import org.xml.sax.*;

/** Small synthetic resource cases; never grow inputs until the process crashes. */
public final class PlistResourceProbe {
    private static final String HEADER = "<!DOCTYPE plist SYSTEM \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"";
    private static PrintStream out;
    private static void check(boolean ok) { if (!ok) throw new AssertionError("XML resource fixture failed"); }
    private static String repeated(String text, int count) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < count; i++) result.append(text);
        return result.toString();
    }
    private static String hash(String text) throws Exception {
        StringBuilder result = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(text.getBytes("UTF-8")))
            result.append(String.format("%02x", b & 255));
        return result.toString();
    }
    private static void origin(Class<?> type, File jar) throws Exception {
        check(type.getProtectionDomain().getCodeSource() != null);
        check(new File(type.getProtectionDomain().getCodeSource().getLocation().toURI()).equals(jar));
    }
    private static void metadata(File jar) throws Exception {
        SAXParserFactory factory = SAXParserFactory.newInstance();
        check(factory.getClass().getName().equals("org.apache.xerces.jaxp.SAXParserFactoryImpl"));
        origin(factory.getClass(), jar);
        Method method = PropertyListUtilities.class.getDeclaredMethod("getParser"); method.setAccessible(true);
        SAXParser parser = (SAXParser) method.invoke(null);
        XMLReader reader = parser.getXMLReader();
        check(reader.getClass().getName().equals("org.apache.xerces.parsers.SAXParser"));
        origin(reader.getClass(), jar);
        check(reader.getFeature("http://xml.org/sax/features/validation"));
        out.println("provider bundled-xerces; validation=true; origin=expected-jar");
        try {
            boolean enabled = reader.getFeature(javax.xml.XMLConstants.FEATURE_SECURE_PROCESSING);
            out.println("secure_processing recognized=" + enabled);
        } catch (SAXNotRecognizedException failure) { out.println("secure_processing unrecognized"); }
          catch (SAXNotSupportedException failure) { out.println("secure_processing unsupported"); }
        String[] keys = {"entityExpansionLimit", "totalEntitySizeLimit", "maxGeneralEntitySizeLimit", "maxElementDepth"};
        for (String key : keys) {
            try {
                reader.getProperty("http://www.oracle.com/xml/jaxp/properties/" + key);
                out.println("limit " + key + " recognized");
            } catch (SAXNotRecognizedException failure) { out.println("limit " + key + " unrecognized"); }
              catch (SAXNotSupportedException failure) { out.println("limit " + key + " unsupported"); }
        }
    }
    private static void control(String label, String xml, boolean lowered) throws Exception {
        SAXParserFactory factory = SAXParserFactory.newInstance("com.sun.org.apache.xerces.internal.jaxp.SAXParserFactoryImpl", null);
        check(factory.getClass().getClassLoader() == null);
        factory.setValidating(false);
        XMLReader reader = factory.newSAXParser().getXMLReader();
        org.xml.sax.helpers.DefaultHandler handler = new org.xml.sax.helpers.DefaultHandler() {
            @Override public void error(SAXParseException failure) throws SAXException { throw new SAXException("Synthetic control rejected"); }
            @Override public void fatalError(SAXParseException failure) throws SAXException { throw new SAXException("Synthetic control rejected"); }
        };
        reader.setContentHandler(handler); reader.setErrorHandler(handler);
        reader.setEntityResolver(new EntityResolver() {
            public InputSource resolveEntity(String publicId, String systemId) throws SAXException { throw new SAXException("External control resource prohibited"); }
        });
        boolean rejected = false;
        try { reader.parse(new InputSource(new StringReader(xml))); }
        catch (SAXException failure) { rejected = true; }
        check(rejected == lowered);
        OfflineGuard.assertUntouched();
        out.println("jdk_control " + label + " rejected=" + rejected);
    }
    private static void controls(boolean lowered) throws Exception {
        control("entity-count", "<!DOCTYPE root [<!ENTITY e \"fixture\">]><root>" + repeated("&e;", 512) + "</root>", lowered);
        control("entity-size", "<!DOCTYPE root [<!ENTITY e \"" + repeated("x", 512) + "\">]><root>&e;</root>", lowered);
        control("depth", repeated("<n>", 32) + "fixture" + repeated("</n>", 32), lowered);
    }
    private static String canonical(Object value) throws Exception {
        StringWriter writer = new StringWriter(); PropertyListUtilities.writeXML(value, writer); return writer.toString();
    }
    private static void fixture(String label, String subset, String node, String expectedLeaf, int depth) throws Exception {
        String xml = HEADER + subset + "><plist>" + node + "</plist>";
        check(xml.length() < 131072);
        String digest = null;
        for (boolean stream : new boolean[]{false, true}) {
            PropertyList list;
            try { list = stream ? new PropertyList(new ByteArrayInputStream(xml.getBytes("UTF-8"))) : new PropertyList(new StringReader(xml)); }
            catch (com.apple.util.plist.PropertyListException failure) {
                String category = failure.getMessage().contains("maxElementDepth") ? "rejected-depth-limit" : "rejected-property-list";
                try { PropertyListUtilities.readXML(new StringReader(xml)); throw new AssertionError("Rejection not reproducible"); }
                catch (SAXException direct) {
                    if (direct.getException() instanceof ArrayIndexOutOfBoundsException) category = "rejected-legacy-array-bounds";
                }
                if (digest != null) check(digest.equals(category));
                digest = category; OfflineGuard.assertUntouched(); continue;
            }
            Object root = list.getRootElement(), leaf = root;
            for (int i = 0; i < depth; i++) {
                check(leaf instanceof List && ((List<?>) leaf).size() == 1);
                leaf = ((List<?>) leaf).get(0);
            }
            check(expectedLeaf.equals(leaf));
            String encoded = canonical(root);
            check(encoded.length() < 131072);
            check(encoded.equals(canonical(new PropertyList(new StringReader(encoded)).getRootElement())));
            String current = hash(encoded);
            if (digest != null) check(digest.equals(current));
            digest = current;
            OfflineGuard.assertUntouched();
        }
        out.println("fixture " + label + " outcome=" + digest);
    }
    private static void execute(File jar) throws Exception {
        metadata(jar);
        fixture("internal-entity", " [<!ENTITY e \"fixture\">]", "<string>&e;</string>", "fixture", 0);
        fixture("flat-entities-512", " [<!ENTITY e \"fixture\">]", "<string>" + repeated("&e;", 512) + "</string>", repeated("fixture", 512), 0);
        fixture("nested-entities-64", " [<!ENTITY e \"x\"><!ENTITY a \"&e;&e;&e;&e;\"><!ENTITY b \"&a;&a;&a;&a;\"><!ENTITY c \"&b;&b;&b;&b;\">]", "<string>&c;</string>", repeated("x", 64), 0);
        for (int depth : new int[]{8, 30, 31, 32, 128})
            fixture("arrays-" + depth, "", repeated("<array>", depth) + "<string>fixture</string>" + repeated("</array>", depth), "fixture", depth);
        for (int length : new int[]{4096, 65536}) {
            String text = repeated("x", length);
            fixture("string-" + length, "", "<string>" + text + "</string>", text, 0);
        }
        String text = repeated("\u00e9", 32768);
        fixture("unicode-32768", "", "<string>" + text + "</string>", text, 0);
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install(); check(args.length == 2 && (args[1].equals("default") || args[1].equals("lowered-jaxp-properties")));
        PrintStream previousOut = System.out, previousErr = System.err; out = previousOut;
        ByteArrayOutputStream capturedOut = new ByteArrayOutputStream(), capturedErr = new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(capturedOut, true, "UTF-8"));
            System.setErr(new PrintStream(capturedErr, true, "UTF-8"));
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
            execute(new File(args[0]).getAbsoluteFile());
            controls(args[1].equals("lowered-jaxp-properties"));
            check(capturedOut.size() == 0 && capturedErr.size() == 0);
        } finally {
            System.setOut(previousOut); System.setErr(previousErr); OfflineGuard.assertUntouched();
        }
        out.println("PASS bounded XML resource observations; guarded_operations=0");
    }
}
