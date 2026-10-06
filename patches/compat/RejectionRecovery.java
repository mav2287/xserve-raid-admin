package compat;

import com.apple.xsr.net.AcpxConnection;
import com.apple.xsr.net.CommunicationsManager;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;

/** Stop worker faults before callbacks; never replay an unconfirmed operation. */
public final class RejectionRecovery {
    public static final boolean STOPS_REJECTED_SESSIONS = true;
    public static final boolean TERMINATES_AMBIGUOUS_IO = true;
    public static final boolean STOPS_OPERATION_FAILURES = true;
    public static final boolean STOPS_REPORTED_CONNECT_FAILURES = true;
    public static final boolean AVOIDS_STOP_LOCK_INVERSION = true;
    /** The controller may have acted; never retain an untrusted cause chain. */
    public static Exception nullMessage() {
        return new UntrustedResponseException("Response transport failed; outcome is unconfirmed");
    }
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
    private static void shutdownRequired(CommunicationsManager manager) {
        if(manager==null || manager.getClass()!=CommunicationsManager.class)
            throw new IllegalStateException("Response session stop failed");
        try { manager.shutdown(); }
        catch(Exception ignored) { throw new IllegalStateException("Response session stop failed"); }
        catch(LinkageError ignored) { throw new IllegalStateException("Response session stop failed"); }
    }
    /** Worker only: stopping precedes cleanup and the original prefix error log. */
    public static void retire(CommunicationsManager manager) {
        shutdownRequired(manager);
        retireConnection(manager);
    }
    public static void report(CommunicationsManager manager, Exception failure) {
        // Stop local dispatch before logging or callback code can post dependent writes.
        // This is not a controller shutdown command. A failed stop never returns.
        shutdownRequired(manager);
        try { log(failure); } catch(Exception ignored) {} catch(LinkageError ignored) {}
        retireConnection(manager);
    }
    private static void retireConnection(CommunicationsManager manager) {
        try {
            if(!metadata()) { stop(manager); return; }
            AcpxConnection connection;
            synchronized(manager) {
                connection=(AcpxConnection)connectionField.get(manager);
                connectedField.setBoolean(manager,false);
            }
            // Retain the reference for original stopped-worker exit cleanup.
            // Closing outside the lock keeps isConnected/shutdown responsive.
            close(connection);
        } catch(Exception ignored) { stop(manager); } catch(LinkageError ignored) { stop(manager); }
    }
}
