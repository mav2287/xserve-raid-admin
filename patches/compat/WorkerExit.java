package compat;

import com.apple.xsr.net.AcpxConnection;
import com.apple.xsr.net.BasicResponse;
import com.apple.xsr.net.CommShutdownException;
import com.apple.xsr.net.CommunicationHandler;
import com.apple.xsr.net.CommunicationsManager;
import com.apple.xsr.net.RequestMessage;
import com.apple.xsr.net.Response;
import com.apple.xsr.som.RaidSystem;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.Iterator;
import java.util.List;
import javax.swing.SwingUtilities;
import org.apache.log4j.Logger;

/** Original loop exits; no controller operation or replay. */
public final class WorkerExit {
    private static volatile boolean ready;
    private static Class<?> transactionClass, senderClass;
    private static Field handlerField, contextField, connectedField;
    private WorkerExit() {}

    private static Field field(Class<?> owner, String name, Class<?> type, int flags)
        throws Exception {
        Field f=owner.getDeclaredField(name);
        if(f.getType()!=type || f.getModifiers()!=flags)
            throw new IllegalStateException("Worker compatibility metadata differs");
        f.setAccessible(true);
        return f;
    }

    /** Invoked by the Manager constructor before creating/starting its thread. */
    public static synchronized void prepare() {
        if(ready) return;
        try {
            ClassLoader loader=CommunicationsManager.class.getClassLoader();
            Class<?> tx=Class.forName("com.apple.xsr.net.CommunicationsManager$Transaction",false,loader);
            Class<?> sender=Class.forName("com.apple.xsr.net.CommunicationsManager$SyncSender",false,loader);
            if(tx.getClassLoader()!=loader || sender.getClassLoader()!=loader ||
               tx.getModifiers()!=(Modifier.PRIVATE|Modifier.STATIC) ||
               sender.getModifiers()!=Modifier.PRIVATE ||
               tx.getDeclaredFields().length!=3 || tx.getDeclaredMethods().length!=3 ||
               sender.getDeclaredFields().length!=4 || sender.getDeclaredMethods().length!=3)
                throw new IllegalStateException("Worker compatibility metadata differs");
            Field h=field(tx,"handler",CommunicationHandler.class,0);
            Field c=field(tx,"context",Object.class,0);
            field(tx,"message",RequestMessage.class,0);
            field(sender,"claimed",Boolean.TYPE,Modifier.PRIVATE);
            if(sender.getDeclaredMethod("claim").getModifiers()!=Modifier.SYNCHRONIZED ||
               sender.getDeclaredMethod("handleResponse",RaidSystem.class,Response.class,Object.class)
                   .getModifiers()!=(Modifier.PUBLIC|Modifier.SYNCHRONIZED))
                throw new IllegalStateException("Worker compatibility metadata differs");
            Field connected=field(CommunicationsManager.class,"connected",Boolean.TYPE,Modifier.PRIVATE);
            field(CommunicationsManager.class,"stopped",Boolean.TYPE,Modifier.PRIVATE|Modifier.VOLATILE);
            field(CommunicationsManager.class,"workerActiveTxn",Object.class,Modifier.PRIVATE);
            field(CommunicationsManager.class,"workerActiveStarted",Boolean.TYPE,Modifier.PRIVATE);
            handlerField=h;contextField=c;connectedField=connected;
            transactionClass=tx;senderClass=sender;
            ready=true;
        } catch(ThreadDeath failure) { throw failure; }
          catch(Throwable failure) {
            // No arbitrary cause is retained or rendered at the startup boundary.
            throw new IllegalStateException("RAID Admin worker compatibility unavailable");
        }
    }

    /** Constructor initializes production instances; supports guarded fixture bypass too. */
    public static void ensurePrepared() { if(!ready)prepare(); }

    private static void signal() {
        try { Logger.getLogger(CommunicationsManager.class).error("RAID_ADMIN_WORKER_EXIT_FAILED"); }
        catch(ThreadDeath failure) { throw failure; }
        catch(Throwable ignored) {}
    }

    /** Already-stopped connection notifications retain their original worker/context.
     * Callback failures must never enter legacy transport/logging classification.
     */
    public static void connectCallback(CommunicationHandler handler,RaidSystem system,
                                       Response response,Object context) {
        try { handler.handleResponse(system,response,context); }
        catch(ThreadDeath failure) { throw failure; }
        catch(Throwable failure) { signal(); }
    }

    private static final class Entry {
        final CommunicationHandler handler;
        final Object context;
        final Response response;
        Entry(Object tx,boolean started)throws Exception {
            if(tx==null || tx.getClass()!=transactionClass)
                throw new IllegalStateException("Worker transaction metadata differs");
            handler=(CommunicationHandler)handlerField.get(tx);
            context=contextField.get(tx);
            Exception failure=started
                ? new UntrustedResponseException("Worker stopped; operation outcome is unconfirmed")
                : new CommShutdownException();
            response=new BasicResponse(Response.TYPE_COMMAND,null,Response.IO_ERR,failure);
        }
    }

    private static final class CallbackBatch implements Runnable {
        private final List<Entry> entries;
        private final RaidSystem system;
        CallbackBatch(List<Entry> entries,RaidSystem system){this.entries=entries;this.system=system;}
        public void run() {
            for(Entry e:entries) {
                try { e.handler.handleResponse(system,e.response,e.context); }
                catch(ThreadDeath failure) { throw failure; }
                catch(StackOverflowError failure) { signal(); }
                catch(VirtualMachineError failure) { signal(); return; }
                catch(Throwable failure) { signal(); }
            }
        }
    }

    /** Wrapper writes stopped directly before entry; no callback runs under locks. */
    public static void exit(CommunicationsManager manager,LinkedList<?> queue,Object active,
                            boolean started,RaidSystem system,AcpxConnection connection,
                            Throwable cause) {
        try {
            if(!ready || manager==null || manager.getClass()!=CommunicationsManager.class ||
               queue==null || queue.getClass()!=LinkedList.class)
                throw new IllegalStateException("Worker compatibility metadata unavailable");
            Object[] pending;
            synchronized(queue) { pending=queue.toArray(); }
            List<Entry> all=new ArrayList<Entry>(pending.length+(active==null?0:1));
            if(active!=null)all.add(new Entry(active,started));
            for(Object tx:pending)if(tx!=active)all.add(new Entry(tx,false));
            List<Entry> asynchronous=new ArrayList<Entry>(all.size());
            for(int i=0;i<all.size();i++) {
                Entry e=all.get(i);
                if(e.handler!=null && e.handler.getClass()!=senderClass)asynchronous.add(e);
            }
            // Retain queued ownership until every response has been prepared.
            synchronized(queue) {
                if(queue.size()!=pending.length)throw new IllegalStateException("Worker queue changed after stop");
                Iterator<?> items=queue.iterator();
                for(int i=0;i<pending.length;i++)
                    if(items.next()!=pending[i])throw new IllegalStateException("Worker queue changed after stop");
                queue.clear();
            }
            for(int i=0;i<all.size();i++) {
                Entry e=all.get(i);
                if(e.handler==null)continue;
                if(e.handler.getClass()==senderClass) {
                    try { e.handler.handleResponse(system,e.response,e.context); }
                    catch(ThreadDeath failure) { throw failure; }
                    catch(Throwable failure) { signal(); }
                }
            }
            // Synchronous callers may have held the Manager monitor; release them first.
            synchronized(manager) { connectedField.setBoolean(manager,false); }
            if(!asynchronous.isEmpty())
                SwingUtilities.invokeLater(new CallbackBatch(asynchronous,system));
            if(cause!=null || active!=null || pending.length!=0)signal();
        } catch(ThreadDeath failure) { throw failure; }
          catch(Throwable failure) { signal(); }
          finally {
            // Close even when entry preparation fails; ordinary completions precede this.
            // Normal original epilogue already closes. No command is transmitted here.
            if(cause!=null && connection!=null) {
                try { connection.close(); }
                catch(ThreadDeath failure) { throw failure; }
                catch(Throwable failure) { signal(); }
            }
        }
        // VM failures have no completion guarantee. Never render the caught cause.
        // Ordinary Errors and VM Errors leave this stopped worker terminated quietly.
        if(cause instanceof ThreadDeath)throw (ThreadDeath)cause;
    }
}
