import com.apple.xsr.net.HttpConnection;
import fixture.OfflineGuard;
import java.io.*;
import java.net.*;
import java.lang.reflect.Field;
import org.apache.log4j.Level;
import org.apache.log4j.LogManager;

/** Real patched HttpConnection/helper, JVM-local SocketImpl; never creates native sockets. */
public final class ConfigurationPublicationObservation {
    static HttpConnection owner;
    static Field socketField, connectedField, timeoutField;
    static boolean memoryFactory, liveConfiguration;
    static MemoryImpl lastImpl;
    static int fault, constructions, closes, connections, permissionChecks;
    static String order;
    static IOException constructorFailure=new SocketTimeoutException();
    static void check(boolean value) { if (!value) throw new AssertionError("Publication assertion"); }
    static void unpublished() {
        try { check(socketField.get(owner)==null && !connectedField.getBoolean(owner)); }
        catch (IllegalAccessException e) { throw new AssertionError("Fixture access"); }
    }
    static void configurationState() {
        if(!liveConfiguration) { unpublished(); return; }
        try { check(socketField.get(owner)!=null && connectedField.getBoolean(owner)); }
        catch(IllegalAccessException e) { throw new AssertionError("Fixture access"); }
    }
    static final class MemoryImpl extends SocketImpl {
        int timeout;
        protected void create(boolean stream) { check(memoryFactory && stream); }
        protected void connect(SocketAddress address,int deadline) throws IOException {
            unpublished(); order+="connect,"; connections++;
            check(deadline==0 && ((InetSocketAddress)address).getPort()==80);
            if(fault==2)throw constructorFailure;
        }
        protected void connect(String host,int port) { throw new AssertionError("Unbounded connect"); }
        protected void connect(InetAddress host,int port) { throw new AssertionError("Unbounded connect"); }
        protected void bind(InetAddress host,int port) { throw new AssertionError("Bind forbidden"); }
        protected void listen(int backlog) { throw new AssertionError("Listen forbidden"); }
        protected void accept(SocketImpl impl) { throw new AssertionError("Accept forbidden"); }
        protected InputStream getInputStream() { throw new AssertionError("Read forbidden"); }
        protected OutputStream getOutputStream() { throw new AssertionError("Write forbidden"); }
        protected int available() { throw new AssertionError("Read forbidden"); }
        protected void close() throws IOException { closes++; if(fault==4)throw new IOException(); }
        protected void sendUrgentData(int data) { throw new AssertionError("Write forbidden"); }
        public void setOption(int option,Object value) throws SocketException {
            configurationState(); check(option==SocketOptions.SO_TIMEOUT); order+="set,";
            if(fault==1)throw new SocketException();
            timeout=(Integer)value;
        }
        public Object getOption(int option) throws SocketException {
            configurationState(); check(option==SocketOptions.SO_TIMEOUT); order+="read,";
            return (fault==3 || fault==4)?Integer.valueOf(0):Integer.valueOf(timeout);
        }
    }
    static final class MemoryGuard extends SecurityManager {
        final OfflineGuard deny = new OfflineGuard();
        @Override public void checkPermission(java.security.Permission p) { deny.checkPermission(p); }
        @Override public void checkRead(String p) { deny.checkRead(p); }
        @Override public void checkWrite(String p) { deny.checkWrite(p); }
        @Override public void checkWrite(FileDescriptor p) { deny.checkWrite(p); }
        @Override public void checkDelete(String p) { deny.checkDelete(p); }
        @Override public void checkExec(String p) { deny.checkExec(p); }
        @Override public void checkExit(int p) { deny.checkExit(p); }
        @Override public void checkListen(int p) { deny.checkListen(p); }
        @Override public void checkMulticast(InetAddress p) { deny.checkMulticast(p); }
        @Override public void checkConnect(String host,int port) {
            if(!memoryFactory || !host.equals("127.0.0.1") || (port!=80 && port!=-1))deny.checkConnect(host,port);
            permissionChecks++;
        }
        @Override public void checkConnect(String host,int port,Object context) { checkConnect(host,port); }
    }
    public static void main(String[] args) throws Exception {
        // No app Main, profile, credentials, command or native socket is involved.
        // Logging initialization follows the memory guard installation.
        for(String name:new String[]{"socket","connected","timeout"}) {
            Field f=HttpConnection.class.getDeclaredField(name);f.setAccessible(true);
            if(name.equals("socket"))socketField=f;
            else if(name.equals("connected"))connectedField=f;
            else timeoutField=f;
        }
        Socket.setSocketImplFactory(()->{ check(memoryFactory); constructions++; lastImpl=new MemoryImpl(); return lastImpl; });
        memoryFactory=true;
        System.setSecurityManager(new MemoryGuard()); LogManager.getLoggerRepository().setThreshold(Level.OFF);
        int cases=0;
        for(int scenario=0;scenario<5;scenario++) {
            fault=scenario;constructions=closes=connections=0;order="";
            owner=new HttpConnection("127.0.0.1");
            if(scenario==0)timeoutField.setInt(owner,7301);
            try {
                owner.connect();check(scenario==0);
                check(connectedField.getBoolean(owner) && socketField.get(owner)!=null);
                check(lastImpl.timeout==7301);
                check(order.equals("connect,set,read,") && constructions==1 && closes==0 && connections==1);
                owner.connect();check(constructions==1 && connections==1);
                liveConfiguration=true;
                try { owner.setTimeout(9001);check(owner.getTimeout()==9001 && lastImpl.timeout==9001); }
                finally { liveConfiguration=false; }
                owner.disconnect();unpublished();owner.connect();
                check(connectedField.getBoolean(owner) && constructions==2 && connections==2 && lastImpl.timeout==9001);cases++;
            } catch(IOException e) {
                check(scenario!=0 && "Connection setup failed".equals(e.getMessage()) && e.getCause()==null);
                check((scenario==2)==(e instanceof SocketTimeoutException));
                unpublished();check(constructions==1 && closes==1 && connections==1);cases++;
            }
            check(timeoutField.getInt(owner)==(scenario==0?9001:30000));
        }
        for(IOException failure:new IOException[]{new UnknownHostException(),new ConnectException(),new NoRouteToHostException(),new SocketTimeoutException(),new BindException(),new SocketException(),new InterruptedIOException(),new IOException()}) {
            fault=2;constructorFailure=failure;constructions=closes=connections=0;order="";
            owner=new HttpConnection("127.0.0.1");
            if(failure instanceof InterruptedIOException)((InterruptedIOException)failure).bytesTransferred=7;
            Thread.currentThread().interrupt();
            try { owner.connect(); throw new AssertionError("Constructor failure ignored"); }
            catch(IOException clean) {
                check(clean.getClass()==failure.getClass() && "Connection setup failed".equals(clean.getMessage()));
                check(clean.getCause()==null && clean.getSuppressed().length==0 && Thread.currentThread().isInterrupted());
                if(clean instanceof InterruptedIOException)check(((InterruptedIOException)clean).bytesTransferred==7);
            } finally { Thread.interrupted(); }
            unpublished();check(constructions==1 && closes==1 && connections==1);cases++;
        }
        constructorFailure=new ConnectException(){
            @Override public String getMessage(){throw new AssertionError("Cause rendered");}
            @Override public String toString(){throw new AssertionError("Cause rendered");}
        };
        fault=2;constructions=closes=connections=0;owner=new HttpConnection("127.0.0.1");
        try { owner.connect();throw new AssertionError("Hostile failure ignored"); }
        catch(ConnectException clean){check("Connection setup failed".equals(clean.getMessage()) && clean.getCause()==null);}
        unpublished();check(closes==1);cases++;
        // Direct HttpConnection retry is characterized; Manager retry policy is untouched.
        fault=0;owner.connect();check(connectedField.getBoolean(owner) && constructions==2 && connections==2);
        owner.disconnect();unpublished();owner.connect();check(connectedField.getBoolean(owner) && constructions==3 && connections==3);cases++;
        OfflineGuard.assertUntouched();check(cases==15 && permissionChecks>0);
        System.out.println("PASS actual read-timeout configuration prototype; cases=15; native_sockets=0");
    }
}
