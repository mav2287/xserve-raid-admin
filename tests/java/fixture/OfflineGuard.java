package fixture;

import java.io.File;
import java.net.InetAddress;
import java.security.Permission;

/** Guard for trusted, reviewed legacy-code fixtures; not a general JVM sandbox. */
public final class OfflineGuard extends SecurityManager {
    private static int denied;
    private static SecurityException deny(String message) { denied++; return new SecurityException(message); }
    public static void assertUntouched() { if (denied != 0) throw new AssertionError("Forbidden operation attempted"); }
    public static void install() { System.setSecurityManager(new OfflineGuard()); }
    @Override public void checkPermission(Permission permission) {
        if (permission instanceof RuntimePermission &&
            (permission.getName().equals("setSecurityManager") || permission.getName().equals("preferences")))
            throw deny("Profile access and guard replacement prohibited");
    }
    @Override public void checkRead(String path) {
        String normalized = new File(path).toPath().toAbsolutePath().normalize().toString();
        if (normalized.startsWith("/__raid_security_fixture__")) throw deny("External fixture file read prohibited");
        if (normalized.contains("/Library/Preferences/") || normalized.endsWith("/Library/Preferences"))
            throw deny("Preference reads prohibited");
    }
    @Override public void checkWrite(String path) { throw deny("Writes prohibited"); }
    @Override public void checkDelete(String path) { throw deny("Deletes prohibited"); }
    @Override public void checkExec(String command) { throw deny("Subprocesses prohibited"); }
    @Override public void checkConnect(String host, int port) { throw deny("Sockets prohibited"); }
    @Override public void checkListen(int port) { throw deny("Sockets prohibited"); }
    @Override public void checkMulticast(InetAddress address) { throw deny("Sockets prohibited"); }
}
