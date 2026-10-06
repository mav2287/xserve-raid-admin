import fixture.OfflineGuard;
import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.XMLConstants;

/** Independent pinned-Java-8 measurement, before production policy overrides. */
public final class ParserDefaultsProbe {
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        Class<?> type=Class.forName("com.sun.org.apache.xerces.internal.jaxp.SAXParserFactoryImpl",true,null);
        if(type.getClassLoader()!=null)throw new AssertionError("Default provider origin differs");
        SAXParserFactory factory=(SAXParserFactory)type.newInstance();
        factory.setValidating(true);factory.setNamespaceAware(false);factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING,true);
        SAXParser parser=factory.newSAXParser();
        String[][] defaults={{"entityExpansionLimit","64000"},{"totalEntitySizeLimit","50000000"},{"maxGeneralEntitySizeLimit","0"},
            {"maxParameterEntitySizeLimit","1000000"},{"elementAttributeLimit","10000"},{"maxOccurLimit","5000"},
            {"entityReplacementLimit","3000000"},{"maxXMLNameLimit","1000"},{"maxElementDepth","0"}};
        for(String[] value:defaults) {
            if(!value[1].equals(String.valueOf(parser.getProperty("http://www.oracle.com/xml/jaxp/properties/"+value[0]))))throw new AssertionError("Pinned default quota differs");
            System.out.println("vendor_default "+value[0]+"="+value[1]);
        }
        OfflineGuard.assertUntouched();System.out.println("PASS pinned Java8 secure-processing defaults; guarded_operations=0");
    }
}
