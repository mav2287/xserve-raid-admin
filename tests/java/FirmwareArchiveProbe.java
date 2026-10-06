import com.apple.xsr.update.FirmwareBundleConnection;
import fixture.OfflineGuard;
import java.io.*;
import java.net.URL;
import java.util.jar.*;

/** Synthetic archive loading only. Never constructs FirmwareUpdater or controller models. */
public final class FirmwareArchiveProbe {
    private static void check(boolean ok) { if (!ok) throw new AssertionError("Archive fixture mismatch"); }
    private static FirmwareBundleConnection open(File file, String entry) throws Exception {
        return new FirmwareBundleConnection(new URL("jar:" + file.toURI().toASCIIString() + "!/" + entry));
    }
    private static String error(IOException error) {
        if (error instanceof java.util.zip.ZipException) return "ZIP_ERROR";
        if (error instanceof FileNotFoundException) return "MISSING_ENTRY";
        return "IO_ERROR";
    }
    private static void valid(File file) throws Exception {
        FirmwareBundleConnection root = open(file, "");
        check(root.getEntryName() == null && root.getAttributes() == null);
        Manifest manifest = root.getManifest();
        check(manifest != null);
        Attributes main = root.getMainAttributes();
        String[] keys = {"xserveraid-raid-controller-update-image", "xserveraid-coprocessor-full-image", "xserveraid-coprocessor-update-image"};
        String[] entries = {"raid.bin", "full.bin", "update.bin"};
        for (int i=0; i<keys.length; i++) {
            check(entries[i].equals(main.getValue(keys[i])));
            FirmwareBundleConnection item = open(file,entries[i]);
            check(entries[i].equals(item.getEntryName()));
            check("9.9.9".equals(item.getAttributes().getValue("firmware-version")));
            check("2000-01-01".equals(item.getAttributes().getValue("firmware-date")));
            InputStream stream = item.getInputStream();
            try {
                for (int n=0;n<4;n++) check(stream.read() == n);
                check(stream.read() == -1);
            } finally { stream.close(); }
            String closed;
            try { closed = stream.read() == -1 ? "EOF" : "DATA"; }
            catch (IOException expected) { closed = "IO_ERROR"; }
            check(!closed.equals("DATA"));
            System.out.println("closed_stream_" + i + "=" + closed);
        }
        check(main.getValue("Fixture-Continuation").length() == 80);
        check(manifest.getAttributes("ghost.bin") != null);
        try { open(file,"ghost.bin").getInputStream(); throw new AssertionError("Missing image accepted"); }
        catch (FileNotFoundException expected) { }
        System.out.println("PASS manifest_entries_metadata_continuation_orphan");
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        try {
            File actual = new File(FirmwareBundleConnection.class.getProtectionDomain().getCodeSource().getLocation().toURI());
            check(actual.getCanonicalFile().equals(new File(args[1]).getCanonicalFile()));
            File directory = new File(args[0]);
            valid(new File(directory,"stored.xfb"));
            valid(new File(directory,"deflated.xfb"));
            FirmwareBundleConnection noManifest = open(new File(directory,"no-manifest.xfb"),"");
            check(noManifest.getManifest() == null && noManifest.getMainAttributes() == null);
            for (String name : new String[]{"malformed.xfb","truncated.xfb","corrupt-local-header.xfb"}) {
                try { open(new File(directory,name),"").getManifest(); throw new AssertionError("Invalid ZIP accepted"); }
                catch (IOException expected) { System.out.println(name + "=" + error(expected)); }
            }
            FirmwareBundleConnection duplicate = open(new File(directory,"duplicate.xfb"),"duplicate.bin");
            InputStream duplicateStream = duplicate.getInputStream();
            int selected;
            try { selected = duplicateStream.read(); check(duplicateStream.read() == -1); }
            finally { duplicateStream.close(); }
            check(selected == 1 || selected == 2);
            System.out.println("duplicate_entry_selected=" + selected);
            try { new FirmwareBundleConnection(new File(directory,"stored.xfb").toURI().toURL()); throw new AssertionError("Non-JAR URL accepted"); }
            catch (IllegalArgumentException expected) { }
        } finally { OfflineGuard.assertUntouched(); }
        System.out.println("PASS wrapper_source_verified; local_archive_loading; guarded_operations=0");
    }
}
