import com.apple.util.plist.PropertyList;
import com.apple.util.plist.PropertyListUtilities;
import fixture.OfflineGuard;
import java.io.*;
import java.security.MessageDigest;
import java.util.*;

/** Differential accepted-value coverage; failures are never accepted as parity. */
public final class ParserParityProbe {
    private static final String HEAD="<!DOCTYPE plist SYSTEM \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist>";
    private static void check(boolean ok) {if(!ok) throw new AssertionError("Parser parity failed");}
    private static String repeat(String value,int n) {StringBuilder b=new StringBuilder();for(int i=0;i<n;i++)b.append(value);return b.toString();}
    private static String canonical(Object value) throws Exception {StringWriter w=new StringWriter();PropertyListUtilities.writeXML(value,w);return w.toString();}
    private static void fixture(PrintStream out,String label,String node) throws Exception {
        fixture(out,label,node,HEAD,"UTF-8");
    }
    private static void fixture(PrintStream out,String label,String node,String header,String encoding) throws Exception {
        String xml=header+node+"</plist>";check(xml.length()<262144);
        String value=canonical(new PropertyList(new StringReader(xml)).getRootElement());
        check(value.length()<262144);
        check(value.equals(canonical(new PropertyList(new ByteArrayInputStream(xml.getBytes(encoding))).getRootElement())));
        check(value.equals(canonical(new PropertyList(new StringReader(value)).getRootElement())));
        StringBuilder hash=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(value.getBytes("UTF-8")))hash.append(String.format("%02x",b&255));
        out.println("fixture "+label+" sha256="+hash);
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();PrintStream out=System.out,err=System.err;
        ByteArrayOutputStream captured=new ByteArrayOutputStream(),errors=new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(captured,true,"UTF-8"));System.setErr(new PrintStream(errors,true,"UTF-8"));
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
            for(int n:new int[]{4095,4096,4097,8191,8192,8193,16383,16384,16385})
                fixture(out,"text-"+n,"<string>"+repeat("x",n)+"&amp;<![CDATA[<fixture>]]>\u00e9</string>");
            String[] values={"<string/>","<array/>","<dict/>","<integer>-9223372036854775808</integer>","<integer>9223372036854775807</integer>","<real>NaN</real>","<real>Infinity</real>","<real>-0.0</real>","<date>2004-01-01T00:00:00Z</date>","<array><!--fixture--><?fixture value?><true/><false/></array>","<dict><key>a</key><string>first</string><key>a</key><string>last</string></dict>"};
            for(int i=0;i<values.length;i++)fixture(out,"value-"+i,values[i]);
            for(String kind:new String[]{"dict","mixed","empty-array","empty-dict"}) {
                String node=kind.equals("empty-array")?"<array/>":kind.equals("empty-dict")?"<dict/>":"<string>fixture</string>";
                for(int depth=0;depth<30;depth++)node=kind.equals("mixed")&&depth%2==0?"<array>"+node+"</array>":"<dict><key>fixture</key>"+node+"</dict>";
                fixture(out,"depth-30-"+kind,node);
            }
            String publicHead="<!DOCTYPE plist PUBLIC \"-//Apple Computer//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist>";
            for(String encoding:new String[]{"UTF-8"})
                fixture(out,"declaration-"+encoding,"<string>caf\u00e9 &amp; fixture</string>","<?xml version=\"1.0\" encoding=\""+encoding+"\"?>"+publicHead,encoding);
            String siblings="<dict><key>a</key><array><string>one</string><string>two</string></array><key>b</key><dict><key>c</key><string>three</string></dict></dict>";
            for(int i=0;i<28;i++)siblings="<array>"+siblings+"</array>";
            fixture(out,"siblings-boundary",siblings);
            fixture(out,"data-plain","<data>"+repeat("eHh4",16384)+"</data>");
            fixture(out,"data-lines","<data>"+repeat(repeat("eHh4",19)+"\n",862)+"</data>");
            check(captured.size()==0&&errors.size()==0);
        } finally {System.setOut(out);System.setErr(err);OfflineGuard.assertUntouched();}
        out.println("PASS accepted parser parity; guarded_operations=0");
    }
}
