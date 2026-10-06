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
    private static final java.util.concurrent.atomic.AtomicReference<AssertionError> callbackAssertions=new java.util.concurrent.atomic.AtomicReference<AssertionError>();

    private static PrintStream out;
    private static final byte[] XML;
    static {try {XML="<plist><dict><key>fixture</key><string>ok</string></dict></plist>".getBytes("UTF-8");}catch(Exception e){throw new AssertionError();}}
    private static boolean guarded(){try{CommunicationsManager.class.getDeclaredField("workerActiveTxn");return true;}catch(NoSuchFieldException absent){return false;}}
    private static String loopMethod(){return guarded()?"dispatchLoop":"run";}
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
        byte[] raw;int closes,closeFailure;boolean ordinary,nullIo;IllegalArgumentException injected;
        final List<byte[]> sent=new ArrayList<byte[]>();
        final List<Integer> ordinals=new ArrayList<Integer>();int created;
    }
    private static final class Memory extends HttpConnection {
        final State state;final int ordinal;ByteArrayOutputStream pending;
        Memory(State state)throws IOException{super("127.0.0.1");setPersistent(true);this.state=state;ordinal=++state.created;}
        @Override OutputStream getOutputStream(){pending=new ByteArrayOutputStream();return pending;}
        @Override InputStream getInputStream()throws IOException {
            check(pending!=null&&state.sent.size()<4);state.sent.add(pending.toByteArray());state.ordinals.add(ordinal);pending=null;
            if(state.nullIo){state.nullIo=false;EOFException failure=new EOFException();failure.initCause(new IOException("DO_NOT_RENDER_SYNTHETIC_HEADER"));throw failure;}
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
        set(m,"queue",new LinkedList<Object>());set(m,"thread",Thread.currentThread());set(m,"system",unsafe().allocateInstance(FakeSystem.class));set(m,"connection",connection);set(m,"connected",true);return m;
    }
    private static byte[] lengthReply(String value)throws Exception{return ("HTTP/1.1 200 X\r\nContent-Length: "+value+"\r\n\r\n").getBytes("US-ASCII");}
    private static byte[][] cases()throws Exception {
        StringBuilder line=new StringBuilder("HTTP/1.1 200 X\r\nX: ");for(int i=0;i<65534;i++)line.append('x');line.append("\r\n");
        StringBuilder count=new StringBuilder("HTTP/1.1 200 X\r\n");for(int i=0;i<129;i++)count.append("X: x\r\n");
        byte[][] legacy=new byte[][]{("HTTP/1.1 200 X\r\nContent-Length: 2147483647\r\n\r\n").getBytes("US-ASCII"),line.toString().getBytes("US-ASCII"),count.toString().getBytes("US-ASCII"),HeaderObservation.totalHeader(1048577).getBytes("US-ASCII"),lengthReply("DO_NOT_RENDER_SYNTHETIC_HEADER"),lengthReply("2147483648"),lengthReply("-1"),lengthReply("-2147483648")};
        try{Class.forName("compat.ResponseFraming");}catch(ClassNotFoundException absent){return legacy;}
        String[] framing={"","Content-Length: 0\r\nContent-Length: 0\r\n","Content-Length: 0\r\ncontent-length: 0\r\n","Transfer-Encoding: chunked\r\n","Content-Length: 0\r\ntRaNsFeR-EnCoDiNg: identity\r\n"};
        byte[][] result=Arrays.copyOf(legacy,legacy.length+framing.length);
        for(int i=0;i<framing.length;i++)result[legacy.length+i]=("HTTP/1.1 200 X\r\n"+framing[i]+"\r\n").getBytes("US-ASCII");
        try{Class.forName("compat.ResponseFraming").getMethod("invalidHeader");}
        catch(NoSuchMethodException absent){return result;}
        byte[][] all=Arrays.copyOf(result,result.length+2);
        all[result.length]="HTTP/1.1 200 X\r\nContent-Length: 0\r\nDO_NOT_RENDER_SYNTHETIC_HEADER\r\n\r\n".getBytes("US-ASCII");
        all[result.length+1]="HTTP/1.1 200 X\r\nContent-Length: 0\r\n: DO_NOT_RENDER_SYNTHETIC_HEADER\r\n\r\n".getBytes("US-ASCII");
        return all;
    }
    private static final class Recorder extends AppenderSkeleton {
        CommunicationsManager observed;boolean requireStop;final boolean throwing;int events,markerEvents,reconnectEvents;String owner,method,markerOwner,markerMethod;boolean safe;
        Recorder(boolean throwing){this.throwing=throwing;}
        @Override protected void append(LoggingEvent event){
            events++;Object value=event.getMessage();safe=value instanceof Exception;
            check(!event.getRenderedMessage().contains("DO_NOT_RENDER_SYNTHETIC_HEADER"));
            String[] trace=event.getThrowableStrRep();if(trace!=null)for(String line:trace)check(!line.contains("DO_NOT_RENDER_SYNTHETIC_HEADER"));
            owner=event.getLocationInformation().getClassName();method=event.getLocationInformation().getMethodName();
            if(value!=null&&value.getClass().getName().equals("compat.UntrustedResponseException")){check(!requireStop||observed!=null&&observed.isStopped());markerEvents++;markerOwner=owner;markerMethod=method;}
            else if("No valid host address for system \"fixture\"".equals(event.getRenderedMessage()))reconnectEvents++;
            if(throwing && value!=null && value.getClass().getName().equals("compat.UntrustedResponseException"))throw new IllegalStateException("synthetic appender failure");
        }
        @Override public void close(){} @Override public boolean requiresLayout(){return false;}
    }
    private static boolean workerFaultStop()throws Exception{try{return Class.forName("compat.RejectionRecovery").getField("STOPS_OPERATION_FAILURES").getBoolean(null);}catch(ClassNotFoundException e){return false;}catch(NoSuchFieldException e){return false;}}
    private static void ordinaryLogging()throws Exception {
        final boolean stopped=workerFaultStop();
        Logger logger=Logger.getLogger(CommunicationsManager.class);boolean add=logger.getAdditivity();Level level=logger.getLevel();Recorder recorder=new Recorder(false);logger.setAdditivity(false);logger.setLevel(Level.ERROR);logger.addAppender(recorder);
        try {
            final State state=new State();state.ordinary=true;final CommunicationsManager m=manager(transport(new Memory(state)));final int[] n={0};recorder.observed=m;recorder.requireStop=stopped;
            m.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){try{check(response.getResultCode()==-102&&m.isStopped()==stopped&&m.isConnected()!=stopped&&state.closes==(stopped?1:0));n[0]++;m.shutdown();}catch(AssertionError callbackFailure){callbackAssertions.compareAndSet(null,callbackFailure);throw callbackFailure;}}},new AcpxMessageFactory().newGetStatusRequest());m.run();
            check(n[0]==1&&state.sent.size()==1&&recorder.events==1&&recorder.safe&&"com.apple.xsr.net.CommunicationsManager".equals(recorder.owner)&&loopMethod().equals(recorder.method));
            out.println("ordinary logger owner=CommunicationsManager method="+loopMethod()+"; terminal=-102; sends=1; "+(stopped?"connected=false; stop=true":"connected=true"));
        } finally {logger.removeAppender(recorder);logger.setAdditivity(add);logger.setLevel(level);}
    }
    private static void pair(final byte[] raw,final int closeFailure,final boolean loggingFailure,final boolean stopExpected)throws Exception {
        pair(raw,closeFailure,loggingFailure,stopExpected,false);
    }
    private static void pair(final byte[] raw,final int closeFailure,final boolean loggingFailure,final boolean stopExpected,final boolean nullIo)throws Exception {
        pair(raw,closeFailure,loggingFailure,stopExpected,nullIo,loggingFailure);
    }
    private static void pair(final byte[] raw,final int closeFailure,final boolean loggingFailure,final boolean metadataStop,final boolean nullIo,final boolean logCapture)throws Exception {
        final boolean containment=containment();final boolean stopExpected=metadataStop||containment;
        final State state=new State();state.raw=raw;state.closeFailure=closeFailure;state.nullIo=nullIo;
        final AcpxConnection old=transport(new Memory(state));final CommunicationsManager m=manager(old);
        final Object[] contexts={new Object(),new Object()};final int[] command={0},connect={0};
        Logger logger=Logger.getLogger(CommunicationsManager.class);boolean add=logger.getAdditivity();Level level=logger.getLevel();Recorder recorder=new Recorder(loggingFailure);recorder.observed=m;recorder.requireStop=containment;
        if(logCapture){logger.setAdditivity(false);logger.setLevel(Level.ERROR);logger.addAppender(recorder);}
        try {
            CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){try{
                try {
                    if(response.getType()==Response.TYPE_CONNECT){check(!stopExpected&&command[0]==1&&connect[0]++==0&&response.getResultCode()==-101&&context==null&&!m.isConnected());set(m,"connection",transport(new Memory(state)));set(m,"connected",true);return;}
                    int i=command[0]++;check(i<2&&context==contexts[i]&&response.getResultCode()==(i==0||stopExpected?-102:0));
                    if(i==0){check(state.sent.size()==1&&(state.closes>=1 || nullIo&&stopExpected));if(nullIo){check(state.closes==(metadataStop?0:1));Exception e=response.getException();check(e!=null&&e.getClass().getName().equals("compat.UntrustedResponseException")&&"Response transport failed; outcome is unconfirmed".equals(e.getMessage())&&e.getCause()==null);}check(field(CommunicationsManager.class,"connection").get(m)==old);if(!metadataStop)check(!m.isConnected());if(containment)check(m.isStopped());}
                    if(i==1)m.shutdown();
                }catch(Exception failure){throw new AssertionError("Recovery callback failed");}
            }catch(AssertionError callbackFailure){callbackAssertions.compareAndSet(null,callbackFailure);throw callbackFailure;}}};
            AcpxMessageFactory f=new AcpxMessageFactory();m.postMessageAsync(handler,containment?f.newSetTimeRequest(new Date(0)):f.newGetStatusRequest(),contexts[0]);m.postMessageAsync(handler,containment?f.newRestartSystemRequest():f.newGetTimeRequest(),contexts[1]);m.run();
            check(command[0]==2&&connect[0]==(stopExpected?0:1)&&state.sent.size()==(stopExpected?1:2));
            if(!stopExpected)check(state.ordinals.equals(Arrays.asList(1,2))&&!Arrays.equals(state.sent.get(0),state.sent.get(1)));
            if(nullIo)check(state.closes==(metadataStop||containment&&closeFailure==0?1:2));
            if(nullIo&&logCapture)check(recorder.events==(containment?1:2)&&recorder.markerEvents==1&&recorder.reconnectEvents==(containment?0:1)&&"com.apple.xsr.net.CommunicationsManager".equals(recorder.markerOwner)&&loopMethod().equals(recorder.markerMethod));
            out.println((nullIo?"null_io_recovery":"recovery")+(nullIo?" log_capture="+logCapture:"")+" close_failure="+closeFailure+" logger_failure="+loggingFailure+" stop="+stopExpected+" results="+(stopExpected?"-102,-102":"-102,0")+" sends="+state.sent.size()+" reconnect_seams="+connect[0]);
        }finally{if(logCapture){logger.removeAppender(recorder);logger.setAdditivity(add);logger.setLevel(level);}}
    }
    private static void direct(byte[] raw,boolean persistent,int closeFailure,int flag)throws Exception{direct(raw,persistent,closeFailure,flag,false);}
    private static void direct(byte[] raw,boolean persistent,int closeFailure,int flag,boolean encrypted)throws Exception{
        State state=new State();state.raw=raw;state.closeFailure=closeFailure;AcpxConnection a=transport(new Memory(state));a.persistent=persistent;a.encrypted=encrypted;
        Throwable caught=null;
        RequestMessage request=new AcpxMessageFactory().newGetStatusRequest();if(flag==1)request.setShutdownConnection(true);if(flag==2)request.setRestartConnection(true,0);
        try{a.send(request);throw new AssertionError("Rejection absent");}
        catch(IllegalArgumentException expected){caught=expected;check(expected.getClass().getName().equals("compat.UntrustedResponseException")&&expected.getCause()==null&&Arrays.asList("Response length is invalid","Response length exceeds limit","Response headers exceed limit","Response length is missing","Response length is ambiguous","Response transfer encoding is unsupported","Response header is invalid").contains(expected.getMessage()));StringWriter text=new StringWriter();expected.printStackTrace(new PrintWriter(text));check(!text.toString().contains("DO_NOT_RENDER_SYNTHETIC_HEADER"));}
        check(state.sent.size()==1&&state.closes==1);
        Method handler=Class.forName("compat.RejectionRecovery").getMethod("sendFailure",Throwable.class,AcpxConnection.class);
        check(handler.invoke(null,caught,(AcpxConnection)null)==caught);
        Throwable ordinary=new IOException("synthetic");check(handler.invoke(null,ordinary,a)==ordinary&&state.closes==1);
        out.println("direct persistent="+persistent+" legacy_body_codec="+encrypted+" connection_flag="+flag+" close_failure="+closeFailure+" marker_identity=true sends=1");
    }
    private static void lengthGates()throws Exception {
        Class<?> helper=Class.forName("compat.BoundedResponseBuffer");Method parse=helper.getMethod("parseLength",String.class),gate=helper.getDeclaredMethod("checkLength",int.class);gate.setAccessible(true);
        for(String value:new String[]{"0","-0","+0","1","+1","0001","16777215","16777216","2147483647","-2147483648"})check(((Integer)parse.invoke(null,value)).intValue()==Integer.parseInt(value));
        String[] invalid={null,""," "," 1","1 ","+","-","1x","2147483648","-2147483649","DO_NOT_RENDER_SYNTHETIC_HEADER"};
        for(String value:invalid){try{Integer.parseInt(value);throw new AssertionError("Runtime accepted presumed invalid input");}catch(NumberFormatException expected){}try{parse.invoke(null,value);throw new AssertionError();}catch(InvocationTargetException failed){Throwable actual=failed.getCause();check(actual.getClass().getName().equals("compat.UntrustedResponseException")&&actual.getCause()==null&&"Response length is invalid".equals(actual.getMessage()));StringWriter text=new StringWriter();actual.printStackTrace(new PrintWriter(text));check(!text.toString().contains("DO_NOT_RENDER_SYNTHETIC_HEADER"));}}
        for(int value:new int[]{-1,Integer.MIN_VALUE})try{gate.invoke(null,value);throw new AssertionError();}catch(InvocationTargetException failed){check(failed.getCause().getClass().getName().equals("compat.UntrustedResponseException")&&"Response length is invalid".equals(failed.getCause().getMessage())&&failed.getCause().getCause()==null);}
        out.println("length gates: runtime parseInt parity, malformed/overflow/negative fixed markers; no-input-or-cause");
    }
    private static void markerIdentity()throws Exception {
        Constructor<?> constructor=Class.forName("compat.UntrustedResponseException").getDeclaredConstructor(String.class);constructor.setAccessible(true);
        State state=new State();state.injected=(IllegalArgumentException)constructor.newInstance("Response headers exceed limit");
        try{transport(new Memory(state)).send(new AcpxMessageFactory().newGetStatusRequest());throw new AssertionError();}
        catch(IllegalArgumentException actual){check(actual==state.injected&&state.closes==1&&state.sent.size()==1);}
        out.println("actual send handler preserves injected marker identity; sends=1");
    }
    private static void throwingCallback(final boolean nullIo)throws Exception {
        State state=new State();state.nullIo=nullIo;if(!nullIo)state.raw=cases()[0];
        final CommunicationsManager m=manager(transport(new Memory(state)));final int[] callbacks={0};
        CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){try{check(m.isStopped()&&!m.isConnected()&&response.getResultCode()==-102);callbacks[0]++;throw new IllegalStateException("synthetic callback");}catch(AssertionError callbackFailure){callbackAssertions.compareAndSet(null,callbackFailure);throw callbackFailure;}}};
        AcpxMessageFactory factory=new AcpxMessageFactory();m.postMessageAsync(handler,factory.newSetTimeRequest(new Date(0)));m.postMessageAsync(handler,factory.newRestartSystemRequest());
        if(guarded()){m.run();javax.swing.SwingUtilities.invokeAndWait(()->{});check(callbacks[0]==2);}else{try{m.run();throw new AssertionError("Callback did not throw");}catch(IllegalStateException expected){check(callbacks[0]==1);}}
        check(m.isStopped()&&!m.isConnected()&&state.sent.size()==1&&state.closes==1&&((LinkedList)field(CommunicationsManager.class,"queue").get(m)).size()==(guarded()?0:1));
        out.println("containment callback-throws null_io="+nullIo+(guarded()?"; sends=1; stopped=true; queued=0; callbacks=2; terminal-drain":"; sends=1; stopped=true; queued=1; callback-drain-unqualified"));
    }
    private static boolean containment()throws Exception {
        try{return Class.forName("compat.RejectionRecovery").getField("STOPS_REJECTED_SESSIONS").getBoolean(null);}
        catch(ClassNotFoundException absent){return false;}catch(NoSuchFieldException absent){return false;}
    }
    public static void main(String[] args)throws Exception{
        check(args.length==1);boolean fixed=Boolean.parseBoolean(args[0]);OfflineGuard.install();out=System.out;PrintStream err=System.err;
        ByteArrayOutputStream captured=new ByteArrayOutputStream(),errors=new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(captured,true,"UTF-8"));System.setErr(new PrintStream(errors,true,"UTF-8"));
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.ERROR);ordinaryLogging();
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.OFF);
            if(fixed){lengthGates();byte[][] cases=cases();for(byte[] raw:cases){check(raw.length<=1048577);pair(raw,0,false,false);for(boolean persistent:new boolean[]{true,false})for(int failure=0;failure<=2;failure++)direct(raw,persistent,failure,0);}
                if(cases.length==15){
                    for(int flag=1;flag<=2;flag++)for(int failure=1;failure<=2;failure++)direct(cases[13],true,failure,flag);
                    for(int failure=0;failure<=2;failure++)direct(cases[13],true,failure,0,true);
                    org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.ERROR);pair(cases[13],0,true,false);org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.OFF);
                }
                for(int i=0;i<2;i++)for(int flag=1;flag<=2;flag++)for(int failure=1;failure<=2;failure++)direct(cases[i],true,failure,flag);markerIdentity();
                for(int i=0;i<2;i++)for(int failure=0;failure<=2;failure++)direct(cases[i],true,failure,0,true);
                for(int failure=1;failure<=2;failure++)pair(cases[0],failure,false,false);
                org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.ERROR);pair(cases[0],0,true,false);org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.OFF);
                Class<?> helper=Class.forName("compat.RejectionRecovery");Field metadata=field(helper,"connectedField");Object previous=metadata.get(null);metadata.set(null,null);
                try{pair(cases[0],0,false,true);}finally{metadata.set(null,previous);}
                boolean nullFixed;try{helper.getMethod("nullMessage");nullFixed=true;}catch(NoSuchMethodException absent){nullFixed=false;}
                if(nullFixed){
                    for(int failure=0;failure<=2;failure++)pair(null,failure,false,false,true);
                    org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.ERROR);pair(null,0,true,false,true);pair(null,0,false,false,true,true);org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.OFF);
                    metadata.set(null,null);try{pair(null,0,false,true,true);}finally{metadata.set(null,previous);}
                }
            }
            if(fixed&&containment()){throwingCallback(false);throwingCallback(true);}
            check(callbackAssertions.get()==null);check(captured.size()==0&&errors.size()==0);out.println("PASS recovery fixed="+fixed+"; guarded_operations=0");
        }finally{System.setOut(out);System.setErr(err);OfflineGuard.assertUntouched();}
    }
}
