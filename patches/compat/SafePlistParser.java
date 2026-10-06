package compat;

import javax.xml.XMLConstants;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;
import org.xml.sax.SAXException;
import org.xml.sax.XMLReader;

/** Pinned JDK parser at the original construction boundary; original Handler remains. */
public final class SafePlistParser {
    private SafePlistParser() { }
    private static final String FACTORY = "com.sun.org.apache.xerces.internal.jaxp.SAXParserFactoryImpl";
    private static final String READER = "com.sun.org.apache.xerces.internal.jaxp.SAXParserImpl$JAXPSAXParser";
    // Explicit security policy: bounded custom entity work, regardless of ambient settings.
    // Depth 32 preserves
    // the original validator's observed acceptance boundary without its array failure.
    private static final String[][] LIMITS = {
        {"entityExpansionLimit", "4096"}, {"totalEntitySizeLimit", "1048576"},
        {"maxGeneralEntitySizeLimit", "262144"}, {"maxParameterEntitySizeLimit", "65536"},
        {"elementAttributeLimit", "10000"}, {"maxOccurLimit", "5000"},
        {"entityReplacementLimit", "100000"}, {"maxXMLNameLimit", "1000"},
        {"maxElementDepth", "32"}
    };
    private static void require(boolean ok) throws ParserConfigurationException {
        if (!ok) throw new ParserConfigurationException("Compatible XML parser configuration unavailable");
    }
    private static SAXParserFactory factory() throws ReflectiveOperationException {
        try {
            // Java 9+ exposes bootstrap provider selection through public JAXP.
            // Reflective construction of an internal class is module-restricted.
            java.lang.reflect.Method method = SAXParserFactory.class.getMethod("newDefaultInstance");
            return (SAXParserFactory) method.invoke(null);
        } catch (NoSuchMethodException java8) {
            Class<?> type = Class.forName(FACTORY, true, null);
            if (type.getClassLoader() != null) throw new ClassNotFoundException("Bootstrap XML provider unavailable");
            return (SAXParserFactory) type.newInstance();
        }
    }
    public static SAXParser create() throws ParserConfigurationException, SAXException {
        final SAXParserFactory factory;
        try {
            factory = factory();
        } catch (ReflectiveOperationException failure) {
            throw new ParserConfigurationException("Compatible XML parser unavailable");
        }
        require(factory.getClass().getName().equals(FACTORY) && factory.getClass().getClassLoader() == null);
        factory.setValidating(true);
        factory.setNamespaceAware(false);
        factory.setXIncludeAware(false);
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        SAXParser parser = factory.newSAXParser();
        XMLReader reader = parser.getXMLReader();
        require(reader.getClass().getName().equals(READER) && reader.getClass().getClassLoader() == null);
        for (String[] limit : LIMITS) {
            String key = "http://www.oracle.com/xml/jaxp/properties/" + limit[0];
            parser.setProperty(key, limit[1]);
            require(limit[1].equals(String.valueOf(reader.getProperty(key))));
        }
        parser.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        parser.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        require("".equals(reader.getProperty(XMLConstants.ACCESS_EXTERNAL_DTD)) &&
                "".equals(reader.getProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA)));
        require(reader.getFeature("http://xml.org/sax/features/validation") &&
                !reader.getFeature("http://xml.org/sax/features/namespaces") &&
                factory.getFeature(XMLConstants.FEATURE_SECURE_PROCESSING));
        return parser;
    }
}
