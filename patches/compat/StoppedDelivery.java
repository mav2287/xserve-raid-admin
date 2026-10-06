package compat;

import com.apple.xsr.net.BasicResponse;
import com.apple.xsr.net.CommShutdownException;
import com.apple.xsr.net.CommunicationHandler;
import com.apple.xsr.net.CommunicationsManager;
import com.apple.xsr.net.Response;
import com.apple.xsr.som.RaidSystem;
import javax.swing.SwingUtilities;
import org.apache.log4j.Logger;

/** Only locally refused posts; never touches a controller or a connection. */
public final class StoppedDelivery {
    private StoppedDelivery() {}

    /** Called outside the queue monitor; the original worker drain is unchanged. */
    public static void deliver(CommunicationHandler handler, RaidSystem system,
                               Object context, boolean synchronous) {
        if (handler == null) return;
        Response response = new BasicResponse(Response.TYPE_COMMAND, null,
                                              Response.IO_ERR, new CommShutdownException());
        if (synchronous) {
            // SyncSender checks handled before waiting: no lost notification.
            handler.handleResponse(system, response, context);
        } else {
            // Never invoke GUI callbacks on the poster's stack or under its locks.
            // On a non-EDT poster this event may run before deliver returns.
            SwingUtilities.invokeLater(new Callback(handler, system, response, context));
        }
    }

    private static void signal() {
        try { Logger.getLogger(CommunicationsManager.class).error("RAID_ADMIN_STOPPED_CALLBACK_FAILED"); }
        catch (Exception ignored) {} catch (LinkageError ignored) {}
    }

    private static final class Callback implements Runnable {
        private final CommunicationHandler handler;
        private final RaidSystem system;
        private final Response response;
        private final Object context;
        Callback(CommunicationHandler handler, RaidSystem system,
                         Response response, Object context) {
            this.handler = handler; this.system = system;
            this.response = response; this.context = context;
        }
        public void run() {
            try { handler.handleResponse(system, response, context); }
            catch (Exception ignored) { signal(); }
            catch (LinkageError ignored) { signal(); }
        }
    }
}
