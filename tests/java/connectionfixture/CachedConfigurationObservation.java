import com.apple.xsr.net.HttpConnection;
import com.apple.xsr.net.AcpxConnection;
import com.apple.xsr.net.AcpxMessageFactory;
import com.apple.xsr.net.RequestMessage;
import fixture.OfflineGuard;
import fixture.FixtureIdentity;
import java.io.*;
import java.net.*;
import java.lang.reflect.Field;
import org.apache.log4j.Level;
import org.apache.log4j.LogManager;

/** Real patched HttpConnection/helper, JVM-local SocketImpl; never creates native sockets. */
public final class CachedConfigurationObservation {
    static HttpConnection owner;
    static Field socketField, connectedField, timeoutField;
    static boolean memoryFactory, liveConfiguration, bootstrapping;
    static MemoryImpl lastImpl;
    static int fault, constructions, closes, connections, permissionChecks;
    static String order;
    static IOException constructorFailure=new SocketTimeoutException();
    static void check(boolean value) { if (!value) throw new AssertionError("Publication assertion"); }
    static void unpublished() {
        if(bootstrapping) { check(owner==null);return; }
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
        FixtureIdentity.verify();
        for(String name:new String[]{"socket","connected","timeout"}) {
            Field f=HttpConnection.class.getDeclaredField(name);f.setAccessible(true);
            if(name.equals("socket"))socketField=f;else if(name.equals("connected"))connectedField=f;else timeoutField=f;
        }
        final AcpxConnection[] holder=new AcpxConnection[1];
        final Field connection=AcpxConnection.class.getDeclaredField("connection");connection.setAccessible(true);
        Socket.setSocketImplFactory(()->{
            check(memoryFactory);try { if(!bootstrapping)owner=(HttpConnection)connection.get(holder[0]); }
            catch(IllegalAccessException failure){throw new AssertionError("Fixture access");}
            constructions++;lastImpl=new MemoryImpl();return lastImpl;
        });memoryFactory=true;
        System.setSecurityManager(new MemoryGuard());LogManager.getLoggerRepository().setThreshold(Level.OFF);
        bootstrapping=true;owner=null;fault=0;
        try { holder[0]=new AcpxConnection("127.0.0.1"); } finally { bootstrapping=false; }
        final AcpxConnection acpx=holder[0];owner=(HttpConnection)connection.get(acpx);
        check(connectedField.getBoolean(owner) && socketField.get(owner)!=null);
        acpx.close();check(connection.get(acpx)==null);unpublished();
        RequestMessage request=new AcpxMessageFactory().newNoOpRequest();request.setTimeout(7301);
        fault=2;constructions=closes=connections=0;order="";
        try { acpx.send(request);throw new AssertionError("Initial failure ignored"); }
        catch(SocketTimeoutException expected){ }
        check(connection.get(acpx)==owner);unpublished();check(constructions==1&&connections==1&&closes==1);
        fault=0;
        try { acpx.send(request);throw new AssertionError("Cached failure missing"); }
        catch(NullPointerException expected){ }
        unpublished();check(constructions==1&&connections==1&&closes==1&&timeoutField.getInt(owner)==30000);
        Field outstanding=HttpConnection.class.getDeclaredField("requestOutstanding");outstanding.setAccessible(true);
        check(outstanding.getBoolean(owner));
        try { acpx.send(request);throw new AssertionError("Outstanding failure missing"); }
        catch(IllegalStateException expected){ }
        check(outstanding.getBoolean(owner) && constructions==1 && connections==1 && closes==1);
        OfflineGuard.assertUntouched();
        System.out.println("PASS cached connection gap characterized; calls=3; native_sockets=0; output_acquisitions=0; custom_timeout_null_socket=true");
    }
}
