package compat;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.StringReader;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

/** Only the original locally embedded Apple DTD is permitted; no external fallback. */
public final class SafePlistResolver {
    private SafePlistResolver() { }
    public static InputSource resolve(String publicId, String systemId) throws SAXException {
        if (systemId == null || !systemId.startsWith("http://www.apple.com/DTDs/PropertyList"))
            throw new SAXException("External XML resource blocked");
        try (InputStream input = SafePlistResolver.class.getResourceAsStream("PropertyList.dtd")) {
            if (input == null) throw new SAXException("Embedded property-list DTD unavailable");
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] buffer = new byte[1024]; int count;
            while ((count = input.read(buffer)) != -1) {
                if (bytes.size() + count > 4096) throw new SAXException("Invalid embedded property-list DTD");
                bytes.write(buffer, 0, count);
            }
            // Match the original InputSource: StringReader, no publicId/systemId/encoding.
            return new InputSource(new StringReader(new String(bytes.toByteArray(), "UTF-8")));
        } catch (java.io.IOException failure) {
            throw new SAXException("Embedded property-list DTD unavailable");
        }
    }
}
