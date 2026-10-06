package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import org.apache.log4j.*;
import org.apache.log4j.spi.LoggingEvent;
import sun.misc.Unsafe;

/** Strictly memory-only, actual send/dispatch code; no production constructors. */
public final class RecoveryObservation {
    private static PrintStream out;
    private static final byte[] XML;
    static {try {XML="<plist><dict><key>fixture</key><string>ok</string></dict></plist>".getBytes("UTF-8");}catch(Exception e){throw new AssertionError();}}
    private static void check(boolean ok){if(!ok)throw new AssertionError("Recovery fixture failed");}
    private static Unsafe unsafe()throws Exception{Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);return (Unsafe)f.get(null);}
    private static Field field(Class<?> type,String name)throws Exception{Field f=type.getDeclaredField(name);f.setAccessible(true);return f;}
    private static void set(Object target,String name,Object value)throws Exception{field(CommunicationsManager.class,name).set(target,value);}
    public static final class FakeSystem extends RaidSystem {
        public FakeSystem(){super("fixture");throw new AssertionError();}
        @Override public String getPrimaryHostAddress(){return null;}
        @Override public String getSecondaryHostAddress(){return null;}
        @Override public String getName(){return "fixture";}
        @Override public void setUserMessageIndex(int value){}
    }
    private static final class State {
        byte[] raw;int closes,closeFailure;boolean ordinary;IllegalArgumentException injected;
        final List<byte[]> sent=new ArrayList<byte[]>();
        final List<Integer> ordinals=new ArrayList<Integer>();int created;
    }
    private static final class Memory extends HttpConnection {
        final State state;final int ordinal;ByteArrayOutputStream pending;
        Memory(State state)throws IOException{super("127.0.0.1");setPersistent(true);this.state=state;ordinal=++state.created;}
        @Override OutputStream getOutputStream(){pending=new ByteArrayOutputStream();return pending;}
        @Override InputStream getInputStream()throws IOException {
            check(pending!=null&&state.sent.size()<4);state.sent.add(pending.toByteArray());state.ordinals.add(ordinal);pending=null;
            if(state.injected!=null)throw state.injected;
            if(state.ordinary){state.ordinary=false;throw new IllegalStateException("synthetic ordinary failure");}
            byte[] raw=state.raw;state.raw=null;
            if(raw!=null)return new ByteArrayInputStream(raw);
            ByteArrayOutputStream b=new ByteArrayOutputStream();b.write(("HTTP/1.1 200 X\r\nContent-Length: "+XML.length+"\r\n\r\n").getBytes("US-ASCII"));b.write(XML);return new ByteArrayInputStream(b.toByteArray());
        }
        @Override public void connect(){throw new AssertionError("Real connection prohibited");}
        @Override public void setTimeout(int timeout){}
        @Override public void disconnect()throws IOException {
            check(++state.closes<8);
            if(state.closeFailure==1)throw new IOException("synthetic close failure");
            if(state.closeFailure==2)throw new IllegalStateException("synthetic close failure");
        }
    }
    private static AcpxConnection transport(Memory memory)throws Exception{
        AcpxConnection a=(AcpxConnection)unsafe().allocateInstance(AcpxConnection.class);a.host="127.0.0.1";a.persistent=true;a.connection=memory;return a;
    }
    private static CommunicationsManager manager(AcpxConnection connection)throws Exception {
        CommunicationsManager m=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);
        set(m,"queue",new LinkedList<Object>());set(m,"system",unsafe().allocateInstance(FakeSystem.class));set(m,"connection",connection);set(m,"connected",true);return m;
    }
    private static byte[][] cases()throws Exception {
        StringBuilder line=new StringBuilder("HTTP/1.1 200 X\r\nX: ");for(int i=0;i<65534;i++)line.append('x');line.append("\r\n");
        StringBuilder count=new StringBuilder("HTTP/1.1 200 X\r\n");for(int i=0;i<129;i++)count.append("X: x\r\n");
        return new byte[][]{("HTTP/1.1 200 X\r\nContent-Length: 2147483647\r\n\r\n").getBytes("US-ASCII"),line.toString().getBytes("US-ASCII"),count.toString().getBytes("US-ASCII"),HeaderObservation.totalHeader(1048577).getBytes("US-ASCII")};
    }
    private static final class Recorder extends AppenderSkeleton {
        final boolean throwing;int events;String owner,method;boolean safe;
        Recorder(boolean throwing){this.throwing=throwing;}
        @Override protected void append(LoggingEvent event){
            events++;Object value=event.getMessage();safe=value instanceof Exception;
            owner=event.getLocationInformation().getClassName();method=event.getLocationInformation().getMethodName();
            if(throwing && value!=null && value.getClass().getName().equals("compat.UntrustedResponseException"))throw new IllegalStateException("synthetic appender failure");
        }
        @Override public void close(){} @Override public boolean requiresLayout(){return false;}
    }
    private static void ordinaryLogging()throws Exception {
        Logger logger=Logger.getLogger(CommunicationsManager.class);boolean add=logger.getAdditivity();Level level=logger.getLevel();Recorder recorder=new Recorder(false);logger.setAdditivity(false);logger.setLevel(Level.ERROR);logger.addAppender(recorder);
        try {
            final State state=new State();state.ordinary=true;final CommunicationsManager m=manager(transport(new Memory(state)));final int[] n={0};
            m.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){check(response.getResultCode()==-102&&m.isConnected()&&state.closes==0);n[0]++;m.shutdown();}},new AcpxMessageFactory().newGetStatusRequest());m.run();
            check(n[0]==1&&state.sent.size()==1&&recorder.events==1&&recorder.safe&&"com.apple.xsr.net.CommunicationsManager".equals(recorder.owner)&&"run".equals(recorder.method));
            out.println("ordinary logger owner=CommunicationsManager method=run; terminal=-102; sends=1; connected=true");
        } finally {logger.removeAppender(recorder);logger.setAdditivity(add);logger.setLevel(level);}
    }
    private static void pair(final byte[] raw,final int closeFailure,final boolean loggingFailure,final boolean stopExpected)throws Exception {
        final State state=new State();state.raw=raw;state.closeFailure=closeFailure;
        final AcpxConnection old=transport(new Memory(state));final CommunicationsManager m=manager(old);
        final Object[] contexts={new Object(),new Object()};final int[] command={0},connect={0};
        Logger logger=Logger.getLogger(CommunicationsManager.class);boolean add=logger.getAdditivity();Level level=logger.getLevel();Recorder recorder=new Recorder(loggingFailure);
        if(loggingFailure){logger.setAdditivity(false);logger.setLevel(Level.ERROR);logger.addAppender(recorder);}
        try {
            CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){
                try {
                    if(response.getType()==Response.TYPE_CONNECT){check(!stopExpected&&command[0]==1&&connect[0]++==0&&response.getResultCode()==-101&&context==null&&!m.isConnected());set(m,"connection",transport(new Memory(state)));set(m,"connected",true);return;}
                    int i=command[0]++;check(i<2&&context==contexts[i]&&response.getResultCode()==(i==0||stopExpected?-102:0));
                    if(i==0){check(state.sent.size()==1&&state.closes>=1);check(field(CommunicationsManager.class,"connection").get(m)==old);if(!stopExpected)check(!m.isConnected());}
                    if(i==1)m.shutdown();
                }catch(Exception failure){throw new AssertionError("Recovery callback failed");}
            }};
            AcpxMessageFactory f=new AcpxMessageFactory();m.postMessageAsync(handler,f.newGetStatusRequest(),contexts[0]);m.postMessageAsync(handler,f.newGetTimeRequest(),contexts[1]);m.run();
            check(command[0]==2&&connect[0]==(stopExpected?0:1)&&state.sent.size()==(stopExpected?1:2));
            if(!stopExpected)check(state.ordinals.equals(Arrays.asList(1,2))&&!Arrays.equals(state.sent.get(0),state.sent.get(1)));
            out.println("recovery close_failure="+closeFailure+" logger_failure="+loggingFailure+" stop="+stopExpected+" results="+(stopExpected?"-102,-102":"-102,0")+" sends="+state.sent.size()+" reconnect_seams="+connect[0]);
        }finally{if(loggingFailure){logger.removeAppender(recorder);logger.setAdditivity(add);logger.setLevel(level);}}
    }
    private static void direct(byte[] raw,boolean persistent,int closeFailure,int flag)throws Exception{direct(raw,persistent,closeFailure,flag,false);}
    private static void direct(byte[] raw,boolean persistent,int closeFailure,int flag,boolean encrypted)throws Exception{
        State state=new State();state.raw=raw;state.closeFailure=closeFailure;AcpxConnection a=transport(new Memory(state));a.persistent=persistent;a.encrypted=encrypted;
        Throwable caught=null;
        RequestMessage request=new AcpxMessageFactory().newGetStatusRequest();if(flag==1)request.setShutdownConnection(true);if(flag==2)request.setRestartConnection(true,0);
        try{a.send(request);throw new AssertionError("Rejection absent");}
        catch(IllegalArgumentException expected){caught=expected;check(expected.getClass().getName().equals("compat.UntrustedResponseException"));}
        check(state.sent.size()==1&&state.closes==1);
        Method handler=Class.forName("compat.RejectionRecovery").getMethod("sendFailure",Throwable.class,AcpxConnection.class);
        check(handler.invoke(null,caught,(AcpxConnection)null)==caught);
        Throwable ordinary=new IOException("synthetic");check(handler.invoke(null,ordinary,a)==ordinary&&state.closes==1);
        out.println("direct persistent="+persistent+" legacy_body_codec="+encrypted+" connection_flag="+flag+" close_failure="+closeFailure+" marker_identity=true sends=1");
    }
    private static void markerIdentity()throws Exception {
        Constructor<?> constructor=Class.forName("compat.UntrustedResponseException").getDeclaredConstructor(String.class);constructor.setAccessible(true);
        State state=new State();state.injected=(IllegalArgumentException)constructor.newInstance("Response headers exceed limit");
        try{transport(new Memory(state)).send(new AcpxMessageFactory().newGetStatusRequest());throw new AssertionError();}
        catch(IllegalArgumentException actual){check(actual==state.injected&&state.closes==1&&state.sent.size()==1);}
        out.println("actual send handler preserves injected marker identity; sends=1");
    }
    public static void main(String[] args)throws Exception{
        check(args.length==1);boolean fixed=Boolean.parseBoolean(args[0]);OfflineGuard.install();out=System.out;PrintStream err=System.err;
        ByteArrayOutputStream captured=new ByteArrayOutputStream(),errors=new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(captured,true,"UTF-8"));System.setErr(new PrintStream(errors,true,"UTF-8"));
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.ERROR);ordinaryLogging();
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.OFF);
            if(fixed){byte[][] cases=cases();for(byte[] raw:cases){check(raw.length<=1048577);pair(raw,0,false,false);for(boolean persistent:new boolean[]{true,false})for(int failure=0;failure<=2;failure++)direct(raw,persistent,failure,0);}
                for(int i=0;i<2;i++)for(int flag=1;flag<=2;flag++)for(int failure=1;failure<=2;failure++)direct(cases[i],true,failure,flag);markerIdentity();
                for(int i=0;i<2;i++)for(int failure=0;failure<=2;failure++)direct(cases[i],true,failure,0,true);
                for(int failure=1;failure<=2;failure++)pair(cases[0],failure,false,false);
                org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.ERROR);pair(cases[0],0,true,false);org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.OFF);
                Class<?> helper=Class.forName("compat.RejectionRecovery");Field metadata=field(helper,"connectedField");Object previous=metadata.get(null);metadata.set(null,null);
                try{pair(cases[0],0,false,true);}finally{metadata.set(null,previous);}
            }
            check(captured.size()==0&&errors.size()==0);out.println("PASS recovery fixed="+fixed+"; guarded_operations=0");
        }finally{System.setOut(out);System.setErr(err);OfflineGuard.assertUntouched();}
    }
}
