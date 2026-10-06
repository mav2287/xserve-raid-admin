import com.apple.util.plist.PropertyList;
import com.apple.util.plist.PropertyListUtilities;
import com.apple.util.plist.PropertyListException;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.Method;
import javax.xml.parsers.SAXParser;
import org.xml.sax.XMLReader;

/** Actual getParser path: pinned quotas, hostile ambient settings, fresh instances. */
public final class ParserPolicyProbe {
    private static final String PREFIX = "<!DOCTYPE plist SYSTEM \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"";
    private static void check(boolean ok) { if (!ok) throw new AssertionError("Parser policy fixture failed"); }
    private static String repeated(String value, int count) {
        StringBuilder result = new StringBuilder(); for (int i=0;i<count;i++) result.append(value); return result.toString();
    }
    private static void cases() throws Exception {
        for (String reference : new String[]{"&amp;", "&#233;"}) {
            String xml = PREFIX + "><plist><string>" + repeated(reference,70000) + "</string></plist>";
            check(xml.length()<524288);
            Object value = new PropertyList(new StringReader(xml)).getRootElement();
            check(value instanceof String && ((String)value).length()==70000);
            check(value.equals(new PropertyList(new ByteArrayInputStream(xml.getBytes("UTF-8"))).getRootElement()));
        }
        final java.util.concurrent.atomic.AtomicBoolean failed=new java.util.concurrent.atomic.AtomicBoolean();
        Thread[] threads=new Thread[4];
        for(int i=0;i<threads.length;i++) {
            threads[i]=new Thread(new Runnable() {public void run() {
                try {for(int j=0;j<4;j++) check("fixture".equals(new PropertyList(new StringReader(PREFIX+"><plist><string>fixture</string></plist>")).getRootElement()));}
                catch(Throwable failure) {failed.set(true);}
            }});
            threads[i].setDaemon(true);threads[i].start();
        }
        for(Thread thread:threads) {thread.join(2000);check(!thread.isAlive());}
        check(!failed.get());
        String allowed = PREFIX + " [<!ENTITY e \"x\">]><plist><string>" + repeated("&e;",63900) + "</string></plist>";
        check(((String)new PropertyList(new StringReader(allowed)).getRootElement()).length()==63900);
        check(((String)new PropertyList(new ByteArrayInputStream(allowed.getBytes("UTF-8"))).getRootElement()).length()==63900);
        String xml = PREFIX + " [<!ENTITY e \"x\">]><plist><string>" + repeated("&e;",65000) + "</string></plist>";
        check(xml.length()<524288);
        rejected(xml,"64000");
        for (int depth : new int[]{30,31}) {
            String node = "<string>fixture</string>";
            for(int i=0;i<depth;i++) node="<dict><key>fixture</key>"+node+"</dict>";
            try {new PropertyList(new StringReader(PREFIX+"><plist>"+node+"</plist>")); check(depth==30);}
            catch(PropertyListException expected) {check(depth==31); rejected(PREFIX+"><plist>"+node+"</plist>","maxElementDepth");}
        }
    }
    private static void rejected(String xml, String reason) throws Exception {
        for(boolean stream:new boolean[]{false,true}) {
            try {
                if(stream) new PropertyList(new ByteArrayInputStream(xml.getBytes("UTF-8")));
                else new PropertyList(new StringReader(xml));
                throw new AssertionError("Expected quota rejection");
            } catch(PropertyListException expected) {
                check(expected.getMessage()!=null && expected.getMessage().contains(reason));
            }
        }
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        PrintStream out=System.out,err=System.err; ByteArrayOutputStream capturedOut=new ByteArrayOutputStream(),capturedErr=new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(capturedOut,true,"UTF-8"));System.setErr(new PrintStream(capturedErr,true,"UTF-8"));
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
            Method method=PropertyListUtilities.class.getDeclaredMethod("getParser");method.setAccessible(true);
            SAXParser parser=(SAXParser)method.invoke(null),second=(SAXParser)method.invoke(null);
            check(parser!=second && parser.getXMLReader()!=second.getXMLReader());
            XMLReader reader=parser.getXMLReader();
            check(reader.getClass().getClassLoader()==null && reader.getFeature(javax.xml.XMLConstants.FEATURE_SECURE_PROCESSING));
            String[][] limits={{"entityExpansionLimit","64000"},{"totalEntitySizeLimit","50000000"},{"maxGeneralEntitySizeLimit","0"},
                {"maxParameterEntitySizeLimit","1000000"},{"elementAttributeLimit","10000"},{"maxOccurLimit","5000"},
                {"entityReplacementLimit","3000000"},{"maxXMLNameLimit","1000"},{"maxElementDepth","32"}};
            for(String[] limit:limits) check(limit[1].equals(String.valueOf(reader.getProperty("http://www.oracle.com/xml/jaxp/properties/"+limit[0]))));
            check("".equals(reader.getProperty(javax.xml.XMLConstants.ACCESS_EXTERNAL_DTD)) && "".equals(reader.getProperty(javax.xml.XMLConstants.ACCESS_EXTERNAL_SCHEMA)));
            check(reader.getFeature("http://xml.org/sax/features/validation") && !reader.getFeature("http://xml.org/sax/features/namespaces"));
            cases(); check(capturedOut.size()==0 && capturedErr.size()==0);
        } finally {System.setOut(out);System.setErr(err);OfflineGuard.assertUntouched();}
        out.println("PASS parser policy: bootstrap provider, fresh instances, explicit quotas, external access empty, predefined references, entity quota, dict depth boundary; guarded_operations=0");
    }
}
