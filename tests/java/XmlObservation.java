import com.apple.util.plist.PropertyList;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.security.Permission;

/** Baseline observation, not a claim of XML safety. Uses only a disposable sentinel. */
public final class XmlObservation {
    private static int networkAttempts;
    public static void main(String[] args) throws Exception {
        System.setSecurityManager(new SecurityManager() {
            @Override public void checkPermission(Permission p) { }
            @Override public void checkConnect(String host, int port) {
                networkAttempts++;
                throw new SecurityException("External network denied");
            }
        });
        String known = "<?xml version=\"1.0\"?><!DOCTYPE plist SYSTEM \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><string>fixture</string></plist>";
        Object value = new PropertyList(new StringReader(known)).getRootElement();
        if (!"fixture".equals(value) || networkAttempts != 0) throw new AssertionError("Known DTD fixture failed");
        System.out.println("known_apple_dtd_resolved_locally=true");
        Path sentinel = Files.createTempFile("raid-xml-fixture-", ".txt");
        try {
            Files.write(sentinel, "synthetic-fixture-marker".getBytes("UTF-8"));
            String xml = "<?xml version=\"1.0\"?><!DOCTYPE plist [<!ELEMENT plist (string)><!ELEMENT string (#PCDATA)><!ENTITY probe SYSTEM \"" + sentinel.toUri() + "\">]><plist><string>&probe;</string></plist>";
            Object result = new PropertyList(new StringReader(xml)).getRootElement();
            System.out.println("external_file_entity_expanded=" + "synthetic-fixture-marker".equals(result));
        } finally { Files.deleteIfExists(sentinel); }
        try {
            new PropertyList(new StringReader(known.replace("http://www.apple.com/DTDs/PropertyList-1.0.dtd", "http://127.0.0.1:1/fixture.dtd")));
        } catch (Exception expected) { /* Do not print arbitrary parser errors. */ }
        System.out.println("unknown_external_dtd_network_attempt=" + (networkAttempts > 0));
    }
}
