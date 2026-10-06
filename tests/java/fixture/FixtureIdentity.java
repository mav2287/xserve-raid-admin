package fixture;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/** Binds every allowed fixture, shadow and helper class to its actual source. */
public final class FixtureIdentity {
    private FixtureIdentity() {}
    public static void verify() throws Exception {
        String path=System.getProperty("fixture.identitymanifest");
        if(path==null)throw new AssertionError("Class manifest missing");
        Set<String> seen=new HashSet<String>();
        try(BufferedReader lines=Files.newBufferedReader(new File(path).toPath(),StandardCharsets.UTF_8)) {
            for(String line;(line=lines.readLine())!=null;) {
                String[] parts=line.split("\t",-1);
                if(parts.length!=3 || !seen.add(parts[0]))throw new AssertionError("Class manifest shape differs");
                Class<?> cls=Class.forName(parts[0],false,FixtureIdentity.class.getClassLoader());
                File actual=new File(cls.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile();
                if(!actual.equals(new File(parts[1]).getCanonicalFile()))throw new AssertionError("Class CodeSource differs");
                MessageDigest hash=MessageDigest.getInstance("SHA-256");
                try(InputStream in=cls.getResourceAsStream("/"+parts[0].replace('.','/')+".class")) {
                    if(in==null)throw new AssertionError("Class resource missing");
                    byte[] block=new byte[4096];
                    for(int n;(n=in.read(block))!=-1;)hash.update(block,0,n);
                }
                StringBuilder hex=new StringBuilder();
                for(byte b:hash.digest())hex.append(String.format(Locale.ROOT,"%02x",b&255));
                if(!hex.toString().equals(parts[2]))throw new AssertionError("Class resource differs");
            }
        }
        if(seen.isEmpty())throw new AssertionError("Class manifest empty");
    }
}
