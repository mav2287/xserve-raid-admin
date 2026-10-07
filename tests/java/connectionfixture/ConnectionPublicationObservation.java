import com.apple.xsr.net.HttpConnection;
import com.apple.xsr.net.AcpxConnection;
import com.apple.xsr.net.AcpxMessageFactory;
import com.apple.xsr.net.RequestMessage;
import fixture.OfflineGuard;
import fixture.FixtureIdentity;
import java.io.*;
import java.net.*;
import java.lang.reflect.*;
import org.apache.log4j.Level;
import org.apache.log4j.LogManager;
import org.apache.log4j.AppenderSkeleton;
import org.apache.log4j.Logger;
import org.apache.log4j.spi.LoggingEvent;

/** Real patched HttpConnection/helper, JVM-local SocketImpl; never creates native sockets. */
public final class ConnectionPublicationObservation {
    static HttpConnection owner;
    static AcpxConnection target;
    static Field connectionField, outstandingField, persistentField;
    static int requestTouches, writes, cases, attempts, nativeOutputAttempts, logEvents;
    static boolean guardDenial;
    static final IOException marker=new IOException("Fixture marker");
    static final SecurityException security=new SecurityException("Fixture security");
    static final Error fatal=new Error("Fixture fatal");
    static Field socketField, connectedField, timeoutField;
    static boolean memoryFactory, liveConfiguration, bootstrapping;
    static MemoryImpl lastImpl;
    static int fault, constructions, closes, connections, permissionChecks;
    static String order;
    static IOException constructorFailure=new SocketTimeoutException();
    static void check(boolean value) { if (!value) throw new AssertionError("Publication assertion"); }
    static void unpublished() {
        try { if(!bootstrapping)check(connectionField.get(target)==null); }
        catch(IllegalAccessException failure){throw new AssertionError("Fixture access");}
    }
    static void configurationState() {
        if(!liveConfiguration) { unpublished();return; }
        try { owner=(HttpConnection)connectionField.get(target);
            check(owner!=null && socketField.get(owner)!=null && connectedField.getBoolean(owner)); }
        catch(IllegalAccessException failure){throw new AssertionError("Fixture access");}
    }
    static final class MemoryImpl extends SocketImpl {
        int timeout;
        protected void create(boolean stream) { check(memoryFactory && stream); }
        protected void connect(SocketAddress address,int deadline) throws IOException {
            unpublished(); order+="connect,"; connections++;
            check(deadline==0 && ((InetSocketAddress)address).getPort()==80);
            if(fault==2)throw constructorFailure;
            if(fault==5)throw security;
            if(fault==6)throw fatal;
        }
        protected void connect(String host,int port) { throw new AssertionError("Unbounded connect"); }
        protected void connect(InetAddress host,int port) { throw new AssertionError("Unbounded connect"); }
        protected void bind(InetAddress host,int port) { throw new AssertionError("Bind forbidden"); }
        protected void listen(int backlog) { throw new AssertionError("Listen forbidden"); }
        protected void accept(SocketImpl impl) { throw new AssertionError("Accept forbidden"); }
        protected InputStream getInputStream() { throw new AssertionError("Read forbidden"); }
        protected OutputStream getOutputStream() { nativeOutputAttempts++;throw new AssertionError("Write forbidden"); }
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
            permissionChecks++;if(guardDenial)throw security;
        }
        @Override public void checkConnect(String host,int port,Object context) { checkConnect(host,port); }
    }
    static RequestMessage request(final int timeout) {
        final RequestMessage original=new AcpxMessageFactory().newNoOpRequest();
        original.setTimeout(timeout);
        return (RequestMessage)java.lang.reflect.Proxy.newProxyInstance(RequestMessage.class.getClassLoader(),new Class[]{RequestMessage.class},(proxy,method,args)->{
            requestTouches++;
            if(method.getName().equals("getTimeout"))liveConfiguration=true;
            if(method.getName().equals("writeTo")) {
                writes++;owner=(HttpConnection)connectionField.get(target);
                int expected=timeout==0?30000:timeout;
                check(owner!=null && connectedField.getBoolean(owner) && socketField.get(owner)!=null);
                check(lastImpl.timeout==expected && timeoutField.getInt(owner)==expected);
                check(persistentField.getBoolean(owner)==expectedPersistent);
                check(order.equals(timeout==7301?"connect,set,read,set,":"connect,set,read,"));
                throw marker;
            }
            try { return method.invoke(original,args); }
            catch(InvocationTargetException e){throw e.getCause();}
        });
    }
    static boolean expectedPersistent;
    static void reset(int nextFault) {
        fault=nextFault;constructions=closes=connections=requestTouches=writes=logEvents=0;
        order="";liveConfiguration=false;
    }
    static void expectFault(Throwable e,int nextFault) { if(e instanceof AssertionError)throw (AssertionError)e;
        if(nextFault==5){check(e==security);return;}
        if(nextFault==6){check(e==fatal);return;}
        Class<?> expected=nextFault==2?SocketTimeoutException.class:nextFault==1?SocketException.class:IOException.class;
        check(e.getClass()==expected && e.getCause()==null && "Connection setup failed".equals(e.getMessage()));
    }
    static void failure(int nextFault,int timeout,boolean persistent) throws Exception {
        target.close();target.setPersistent(persistent);reset(nextFault);
        RequestMessage message=request(timeout);
        for(int n=1;n<=3;n++) {
            attempts++;
            try { target.send(message);throw new AssertionError("Failure ignored"); }
            catch(Throwable e){expectFault(e,nextFault);}
            check(connectionField.get(target)==null && constructions==n && connections==n && requestTouches==0 && writes==0 && logEvents==0);
            check(nextFault==6 ? closes==0 : closes==n);
        }
        cases++;
    }
    static final class CountAppender extends AppenderSkeleton {
        protected void append(LoggingEvent event){logEvents++;}
        public boolean requiresLayout(){return false;}
        public void close(){}
    }
    public static void main(String[] args) throws Exception {
        FixtureIdentity.verify();
        for(String name:new String[]{"socket","connected","timeout","requestOutstanding","persistent"}) {
            Field f=HttpConnection.class.getDeclaredField(name);f.setAccessible(true);
            if(name.equals("socket"))socketField=f;else if(name.equals("connected"))connectedField=f;
            else if(name.equals("timeout"))timeoutField=f;else if(name.equals("persistent"))persistentField=f;else outstandingField=f;
        }
        connectionField=AcpxConnection.class.getDeclaredField("connection");connectionField.setAccessible(true);
        Socket.setSocketImplFactory(()->{check(memoryFactory);constructions++;lastImpl=new MemoryImpl();return lastImpl;});
        memoryFactory=true;System.setSecurityManager(new MemoryGuard());
        Logger.getRootLogger().setLevel(Level.WARN);Logger.getRootLogger().removeAllAppenders();Logger.getRootLogger().addAppender(new CountAppender());
        LogManager.getLoggerRepository().setThreshold(Level.WARN);
        // Normal constructor and failed constructor: no bypass, local memory transport only.
        bootstrapping=true;reset(0);target=new AcpxConnection("127.0.0.1");bootstrapping=false;
        owner=(HttpConnection)connectionField.get(target);check(owner!=null && connectedField.getBoolean(owner));cases++;
        Method existing=AcpxConnection.class.getDeclaredMethod("createConnection");existing.setAccessible(true);
        existing.invoke(target);check(connectionField.get(target)==owner && constructions==1 && connections==1 && logEvents==1);cases++;
        for(int nextFault:new int[]{1,2,3,4,5,6}) {
            bootstrapping=true;reset(nextFault);
            try { new AcpxConnection("127.0.0.1");throw new AssertionError("Constructor failure ignored"); }
            catch(Throwable e){expectFault(e,nextFault);check(constructions==1 && connections==1 && closes==(nextFault==6?0:1) && logEvents==0);}
            finally{bootstrapping=false;}cases++;
        }
        for(boolean persistent:new boolean[]{true,false})for(int timeout:new int[]{0,30000,7301}) {
            failure(2,timeout,persistent);
            target.setPersistent(persistent);expectedPersistent=persistent;reset(0);
            try { target.send(request(timeout));throw new AssertionError("Marker missing"); }
            catch(IOException e){check(e==marker);}
            check(constructions==1 && connections==1 && writes==1);
            check(connectionField.get(target)==(persistent?owner:null));
            check(outstandingField.getBoolean(owner)); // Original send bookkeeping on writeTo failure is preserved.
            check(closes==(persistent?0:1));target.close();cases++;
        }
        for(int nextFault:new int[]{1,3,4,5,6})failure(nextFault,7301,true);
        target.close();reset(0);guardDenial=true;attempts++;
        try { target.send(request(7301));throw new AssertionError("Guard denial ignored"); }
        catch(SecurityException e){check(e==security && connectionField.get(target)==null && connections==0 && constructions<=1 && requestTouches==0 && logEvents==0);}
        finally{guardDenial=false;}cases++;
        check(attempts==34 && nativeOutputAttempts==0);
        OfflineGuard.assertUntouched();
        System.out.println("PASS connection publication; cases="+cases+"; explicit_failure_attempts="+attempts+"; native_socket_creation_forbidden=true; native_output_attempts="+nativeOutputAttempts);
    }
}
