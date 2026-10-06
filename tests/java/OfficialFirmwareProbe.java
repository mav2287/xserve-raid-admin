import com.apple.xsr.update.FirmwareBundleConnection;
import fixture.OfflineGuard;
import java.io.*;
import java.net.URL;
import java.security.MessageDigest;
import java.util.jar.Attributes;

/** Hash-reads a pinned public firmware package; never loads an updater or request class. */
public final class OfficialFirmwareProbe {
    private static void check(boolean value) { if (!value) throw new AssertionError("Official archive fixture mismatch"); }
    private static FirmwareBundleConnection open(File archive,String entry) throws Exception {
        return new FirmwareBundleConnection(new URL("jar:"+archive.toURI().toASCIIString()+"!/"+entry));
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        try {
            File source=new File(FirmwareBundleConnection.class.getProtectionDomain().getCodeSource().getLocation().toURI());
            check(source.getCanonicalFile().equals(new File(args[1]).getCanonicalFile()));
            File archive=new File(args[0]);
            Attributes main=open(archive,"").getMainAttributes();
            String[] keys={"xserveraid-coprocessor-update-image","xserveraid-raid-controller-update-image"};
            String[] names={"coprocessor/updateROM.bin","raid-controller/updateROM.bin"};
            String[] versions={"1.5.1","1.51c"};
            check(main.getValue("xserveraid-coprocessor-full-image") == null);
            for (int i=0;i<names.length;i++) {
                check(names[i].equals(main.getValue(keys[i])));
                FirmwareBundleConnection image=open(archive,names[i]);
                check(versions[i].equals(image.getAttributes().getValue("firmware-version")));
                check("12/08/2006".equals(image.getAttributes().getValue("firmware-date")));
                MessageDigest hash=MessageDigest.getInstance("SHA-256");
                int size=0, count; byte[] buffer=new byte[8192];
                InputStream stream=image.getInputStream();
                try {
                    while ((count=stream.read(buffer)) != -1) {
                        size += count; check(size <= 16*1024*1024); hash.update(buffer,0,count);
                    }
                } finally { stream.close(); }
                StringBuilder value=new StringBuilder();
                for (byte b:hash.digest()) value.append(String.format("%02x",b & 255));
                System.out.println("image_"+i+"_size="+size);
                System.out.println("image_"+i+"_sha256="+value);
                try { stream.read(); throw new AssertionError("Deflated closed stream remained readable"); }
                catch (IOException expected) { }
            }
        } finally { OfflineGuard.assertUntouched(); }
        System.out.println("PASS official_archive_metadata_and_hashes; optional_full_image_absent; guarded_operations=0");
    }
}
