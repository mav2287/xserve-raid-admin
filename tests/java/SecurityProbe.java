import com.apple.util.plist.PropertyList;
import com.apple.util.plist.PropertyListUtilities;
import com.apple.util.plist.PropertyListException;
import com.apple.xsr.net.*;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.*;
import java.security.MessageDigest;
import java.util.*;
import org.xml.sax.*;

/** Differential local-plist and request-format checks; external IO forbidden before parsing. */
public final class SecurityProbe {
    private static final String APPLE = "http://www.apple.com/DTDs/PropertyList-1.0.dtd";
    private static final String HEADER = "<?xml version=\"1.0\"?><!DOCTYPE plist SYSTEM \"" + APPLE + "\">";
    private static void check(boolean ok, String label) { if (!ok) throw new AssertionError(label); }
    private static String digest(byte[] bytes) throws Exception {
        StringBuilder result = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(bytes)) result.append(String.format("%02x",b & 255));
        return result.toString();
    }
    private static PropertyList parse(String xml, boolean stream) throws Exception {
        return stream ? new PropertyList(new ByteArrayInputStream(xml.getBytes("UTF-8"))) : new PropertyList(new StringReader(xml));
    }
    private static String canonical(PropertyList list) throws Exception {
        StringWriter writer = new StringWriter(); PropertyListUtilities.writeXML(list.getRootElement(),writer); return writer.toString();
    }
    private static void rejected(String xml) throws Exception {
        for (boolean stream : new boolean[]{false,true}) {
            try { parse(xml,stream); throw new AssertionError("Unsafe/malformed XML accepted"); }
            catch (PropertyListException expected) { }
        }
    }
    public static void main(String[] args) throws Exception {
        boolean fixed = Boolean.parseBoolean(args[0]);
        OfflineGuard.install();
        Class<?> type = Class.forName("com.apple.util.plist.PropertyListUtilities$Handler");
        check(type.getSuperclass().getName().equals("org.xml.sax.helpers.DefaultHandler"),"Resolver hierarchy changed");
        check(!org.xml.sax.ext.EntityResolver2.class.isAssignableFrom(type),"Unexpected resolver2 path");
        Constructor<?> constructor = type.getDeclaredConstructor(); constructor.setAccessible(true);
        Object handler = constructor.newInstance();
        Method resolve = type.getMethod("resolveEntity",String.class,String.class); resolve.setAccessible(true);
        InputSource dtd = (InputSource) resolve.invoke(handler,null,APPLE);
        check(dtd.getCharacterStream() instanceof StringReader && dtd.getByteStream() == null &&
              dtd.getSystemId() == null && dtd.getPublicId() == null && dtd.getEncoding() == null,"DTD source semantics changed");
        StringBuilder text = new StringBuilder(); int ch;
        while ((ch = dtd.getCharacterStream().read()) != -1) text.append((char) ch);
        System.out.println("embedded_dtd_sha256=" + digest(text.toString().getBytes("UTF-8")));
        String[] nodes = {"<string>fixture &amp; caf\u00e9</string>","<integer>42</integer>","<real>1.25</real>",
            "<true/>","<false/>","<date>2004-01-01T00:00:00Z</date>","<data>AAEC</data>",
            "<array><string>x</string><integer>2</integer></array>",
            "<dict><key>fixture</key><array><string>x</string><false/></array></dict>"};
        for (int i=0;i<nodes.length;i++) {
            String xml = HEADER + "<plist version=\"1.0\">" + nodes[i] + "</plist>";
            String reader = canonical(parse(xml,false)), stream = canonical(parse(xml,true));
            check(reader.equals(stream),"Reader/InputStream differ");
            check(reader.equals(canonical(parse(reader,false))),"Plist roundtrip differs");
            System.out.println("plist_fixture_" + i + "=" + digest(reader.getBytes("UTF-8")));
        }
        for (String bad : new String[]{"", "<!", HEADER, HEADER + "<plist><string>truncated"}) rejected(bad);
        if (fixed) {
            for (String id : new String[]{null,"file:///__raid_security_fixture__/secret", "http://127.0.0.1:1/fixture.dtd",
                 "https://www.apple.com/DTDs/PropertyList-1.0.dtd", "HTTP://www.apple.com/DTDs/PropertyList-1.0.dtd",
                 "file://localhost/System/Library/DTDs/PropertyList.dtd", "jar:file:///__raid_security_fixture__/archive.jar!/fixture.dtd",
                 "ftp://127.0.0.1/fixture.dtd", "urn:fixture", "PropertyList.dtd"}) {
                try { resolve.invoke(handler,"-//Apple//DTD PLIST 1.0//EN",id); throw new AssertionError("External resolver fallback"); }
                catch (InvocationTargetException expected) { check(expected.getCause() instanceof SAXException,"Wrong resolver exception"); }
                if (id != null) rejected("<!DOCTYPE plist SYSTEM \"" + id + "\"><plist><string>x</string></plist>");
            }
            check(resolve.invoke(handler,null,APPLE + ".synthetic-suffix") instanceof InputSource,"Legacy local prefix behavior changed");
            rejected("<!DOCTYPE plist SYSTEM \"" + APPLE + "\" [<!ENTITY x SYSTEM \"file:///__raid_security_fixture__/secret\">]><plist><string>&x;</string></plist>");
            rejected("<!DOCTYPE plist [<!ENTITY % x SYSTEM \"http://127.0.0.1:1/fixture.dtd\">%x;]><plist><string>x</string></plist>");
        }
        AcpxMessageFactory factory = new AcpxMessageFactory();
        Map<String,Object> passwords = new HashMap<String,Object>();
        passwords.put(com.apple.net.acp.AcpPropertyCode.SYS_PASSWORD_RW.toString(), "synthetic-private-payload");
        RequestMessage passwordChange = factory.newSetPropertiesRequest(passwords);
        RequestMessage[] requests = {passwordChange,factory.newGetStatusRequest(),factory.newSetPropertyRequest("synthetic", "synthetic-private-payload"),
            new UpdateFirmwareRequest(RequestMessage.TARGET_TOP,0,0,new ByteArrayInputStream(new byte[0]))};
        for (RequestMessage request : requests) {
            request.setUser("synthetic-private-user"); request.setPassword("synthetic-private-password");
            String rendered = request.toString();
            if (fixed) check(rendered.equals("RAID Admin request [details redacted]"),"Request diagnostic leaks fields");
            else {
                check(rendered.contains("synthetic-private-password"),"Original request observation changed");
                if (request == passwordChange) check(rendered.contains("synthetic-private-payload"),"Original password payload observation changed");
            }
        }
        OfflineGuard.assertUntouched();
        System.out.println("PASS fixed=" + fixed + "; Reader/InputStream roundtrips and malformed input; request formatting; guarded operations=0");
    }
}
