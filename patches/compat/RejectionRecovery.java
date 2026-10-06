package compat;

import com.apple.xsr.net.AcpxConnection;
import com.apple.xsr.net.CommunicationsManager;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;

/** Retire a rejected response without replay; ordinary exception handling stays legacy. */
public final class RejectionRecovery {
    private static Field connectedField, connectionField;
    private static boolean initialized;
    private static Logger logger() { return Logger.getLogger(CommunicationsManager.class); }
    private static void log(Exception failure) {
        logger().log("compat.RejectionRecovery", Level.ERROR, failure, failure);
    }
    private static void signal() {
        try { logger().error("RAID_ADMIN_REJECTION_CLEANUP_FAILED"); }
        catch(Exception ignored) {} catch(LinkageError ignored) {}
    }
    private static void close(AcpxConnection connection) {
        if(connection!=null) try { connection.close(); }
        catch(Exception ignored) { signal(); } catch(LinkageError ignored) { signal(); }
    }
    /** Exact-marker handler precedes the original finally; cleanup cannot mask its signal. */
    public static Throwable sendFailure(Throwable failure, AcpxConnection connection) {
        if(failure!=null && failure.getClass()==UntrustedResponseException.class) close(connection);
        return failure;
    }
    private static synchronized boolean metadata() {
        if(!initialized) {
            initialized=true;
            try {
                Field a=CommunicationsManager.class.getDeclaredField("connected");
                Field b=CommunicationsManager.class.getDeclaredField("connection");
                if(a.getType()!=Boolean.TYPE || b.getType()!=AcpxConnection.class ||
                   a.getModifiers()!=Modifier.PRIVATE || b.getModifiers()!=Modifier.PRIVATE)
                    return false;
                a.setAccessible(true); b.setAccessible(true);
                connectedField=a; connectionField=b;
            } catch(Exception ignored) { return false; } catch(LinkageError ignored) { return false; }
        }
        return connectedField!=null && connectionField!=null;
    }
    private static void stop(CommunicationsManager manager) {
        try { manager.shutdown(); }
        catch(Exception ignored) {} catch(LinkageError ignored) {}
        signal();
    }
    public static void report(CommunicationsManager manager, Exception failure) {
        if(failure==null || failure.getClass()!=UntrustedResponseException.class) {
            log(failure); return;
        }
        // The new security path contains logging failures so they cannot skip retirement.
        try { log(failure); } catch(Exception ignored) {} catch(LinkageError ignored) {}
        try {
            if(manager.getClass()!=CommunicationsManager.class || !metadata()) { stop(manager); return; }
            AcpxConnection connection;
            synchronized(manager) {
                connection=(AcpxConnection)connectionField.get(manager);
                connectedField.setBoolean(manager,false);
            }
            // Retain the host-bearing reference for the original controller alternation.
            // Closing outside the lock keeps isConnected/shutdown responsive.
            close(connection);
        } catch(Exception ignored) { stop(manager); } catch(LinkageError ignored) { stop(manager); }
    }
}
