package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;

/** Real ACP/queue code, in-memory HTTP transport; no actual connect or controller. */
public final class TransportObservation {
    private static PrintStream fixtureOut;
    private static void emit(String value) { fixtureOut.println(value); }
    private static final byte[] XML;
    static {
        try {
            XML = ("<?xml version=\"1.0\"?><!DOCTYPE plist SYSTEM \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">" +
                   "<plist version=\"1.0\"><dict><key>fixture</key><string>ok</string></dict></plist>").getBytes("UTF-8");
        } catch (Exception e) { throw new AssertionError("Fixture encoding unavailable"); }
    }
    private static Unsafe unsafe() throws Exception {
        Field field = Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true);
        return (Unsafe) field.get(null);
    }
    private static void set(Object target, String field, Object value) throws Exception {
        Field f = target.getClass().getDeclaredField(field); f.setAccessible(true); f.set(target, value);
    }
    public static final class FakeSystem extends RaidSystem {
        public FakeSystem() { super("fixture"); throw new AssertionError("Constructor must not run"); }
        @Override public String getPrimaryHostAddress() { return null; }
        @Override public String getSecondaryHostAddress() { return null; }
        @Override public String getName() { return "fixture"; }
        @Override public void setUserMessageIndex(int value) { }
    }
    private static final class State {
        final List<byte[]> sent = new ArrayList<byte[]>();
        final List<Integer> connections = new ArrayList<Integer>();
        int connectionCount;
        int drops;
        boolean malformed;
        byte[] rawResponse;
        boolean idleOpen;
    }
    private static final class MemoryConnection extends HttpConnection {
        ByteArrayOutputStream pending;
        final State state;
        final int ordinal;
        MemoryConnection(State state) throws IOException { super("127.0.0.1"); setPersistent(true); this.state = state; ordinal = ++state.connectionCount; }
        @Override OutputStream getOutputStream() {
            pending = new ByteArrayOutputStream(); return pending;
        }
        @Override InputStream getInputStream() throws IOException {
            if (pending == null) throw new AssertionError("Response before request");
            check(state.sent.size() < 16, "Fixture send bound exceeded");
            state.sent.add(pending.toByteArray()); pending = null;
            state.connections.add(ordinal);
            if (state.drops-- > 0) throw new IOException("synthetic response loss");
            if (state.rawResponse != null) {
                byte[] raw = state.rawResponse; state.rawResponse = null;
                final boolean idle = state.idleOpen;
                return new InputStream() {
                    final ByteArrayInputStream bytes = new ByteArrayInputStream(raw);
                    int reads;
                    @Override public int read() throws IOException {
                        check(++reads < Math.max(8192, raw.length+64), "Fixture read bound exceeded");
                        if (idle && bytes.available() == 0) throw new java.net.SocketTimeoutException("synthetic idle stream");
                        return bytes.read();
                    }
                    @Override public int available() { return bytes.available(); }
                };
            }
            byte[] body = state.malformed ? new byte[]{'<', '!'} : XML;
            ByteArrayOutputStream response = new ByteArrayOutputStream();
            response.write(("HTTP/1.1 200 OK\r\nContent-Length: " + body.length + "\r\n\r\n").getBytes("US-ASCII"));
            response.write(body);
            return new ByteArrayInputStream(response.toByteArray());
        }
        @Override public void connect() { throw new AssertionError("Real connect prohibited"); }
        @Override public void disconnect() { }
        @Override public void setTimeout(int timeout) { }
    }
    private static AcpxConnection transport(MemoryConnection memory) throws Exception {
        AcpxConnection acp = (AcpxConnection) unsafe().allocateInstance(AcpxConnection.class);
        acp.host = "127.0.0.1"; acp.persistent = true; acp.connection = memory;
        return acp;
    }
    private static void check(boolean condition, String label) { if (!condition) throw new AssertionError(label); }
    private static byte[] reply(String start, String headers, byte[] body) throws Exception {
        return boundedReply(start,headers,body,4096);
    }
    private static byte[] boundedReply(String start, String headers, byte[] body, int ceiling) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        out.write((start + "\r\n" + headers + "\r\n").getBytes("US-ASCII")); out.write(body);
        check(ceiling<=2097152 && out.size() < ceiling, "Fixture response bound exceeded");
        return out.toByteArray();
    }
    private static boolean lengthPolicy()throws Exception {
        try{Class.forName("compat.BoundedResponseBuffer").getMethod("parseLength",String.class);return true;}
        catch(ClassNotFoundException absent){return false;}catch(NoSuchMethodException absent){return false;}
    }
    private static void responseCase(String label, byte[] raw, String expected) throws Exception {
        responseCase(label, raw, expected, false);
    }
    private static void responseCase(String label, byte[] raw, String expected, boolean idle) throws Exception {
        State state = new State(); state.rawResponse = raw; state.idleOpen = idle;
        String outcome;
        AcpxConnection acp=transport(new MemoryConnection(state));
        try {
            com.apple.util.plist.PropertyList parsed = acp.send(new AcpxMessageFactory().newGetStatusRequest());
            if (parsed == null) outcome = "empty";
            else {
                BasicResponse response = new BasicResponse(Response.TYPE_COMMAND, parsed);
                outcome = "result=" + response.getResultCode();
            }
        } catch (java.net.ProtocolException e) { outcome = "protocol-error"; }
          catch (NumberFormatException e) { outcome = "invalid-length"; }
          catch (IllegalArgumentException e) {
              if(e.getClass().getName().equals("compat.UntrustedResponseException")) {
                  check(lengthPolicy() && Arrays.asList("invalid-length","negative-length","overflow-length").contains(label) && "Response length is invalid".equals(e.getMessage()) && e.getCause()==null && acp.connection==null,"Invalid marker differs");
                  emit("security_length "+label+" fixed-marker; closed; no-input-or-cause");outcome=expected;
              }else outcome="negative-length";
          }
          catch (java.net.SocketTimeoutException e) { outcome = "synthetic-idle-timeout"; }
          catch (IOException e) { outcome = "io-error"; }
        check(expected.equals(outcome), "Unexpected synthetic response outcome");
        check(state.sent.size() == 1, "Response fixture send count differs");
        OfflineGuard.assertUntouched();
        emit("response " + label + " " + outcome);
    }
    private static void responses() throws Exception {
        String length = "Content-Length: " + XML.length + "\r\n";
        for (int code : new int[]{200, 401, 403, 500})
            responseCase("http-" + code, reply("HTTP/1.1 " + code + " Fixture", length, XML), "result=0");
        responseCase("invalid-start", reply("fixture", length, XML), "result=0");
        responseCase("empty-body", reply("HTTP/1.1 200 Fixture", "Content-Length: 0\r\n", new byte[0]), "empty");
        responseCase("missing-length", reply("HTTP/1.1 200 Fixture", "", XML), "empty");
        responseCase("lowercase-length", reply("HTTP/1.1 200 Fixture", "content-length: " + XML.length + "\r\n", XML), "empty");
        responseCase("duplicate-last-valid", reply("HTTP/1.1 200 Fixture", "Content-Length: 0\r\n" + length, XML), "result=0");
        responseCase("duplicate-last-zero", reply("HTTP/1.1 200 Fixture", length + "Content-Length: 0\r\n", XML), "empty");
        responseCase("invalid-length", reply("HTTP/1.1 200 Fixture", "Content-Length: fixture\r\n", XML), "invalid-length");
        responseCase("negative-length", reply("HTTP/1.1 200 Fixture", "Content-Length: -1\r\n", XML), "negative-length");
        responseCase("overflow-length", reply("HTTP/1.1 200 Fixture", "Content-Length: 2147483648\r\n", XML), "invalid-length");
        responseCase("truncated-body", reply("HTTP/1.1 200 Fixture", length, Arrays.copyOf(XML, XML.length - 1)), "io-error");
        responseCase("invalid-header", reply("HTTP/1.1 200 Fixture", "fixture\r\n", XML), "protocol-error");
        responseCase("chunked", reply("HTTP/1.1 200 Fixture", "Transfer-Encoding: chunked\r\n", "3\r\nabc\r\n0\r\n\r\n".getBytes("US-ASCII")), "empty");
        responseCase("missing-length-idle", reply("HTTP/1.1 200 Fixture", "", XML), "empty", true);
        responseCase("truncated-body-idle", reply("HTTP/1.1 200 Fixture", length, Arrays.copyOf(XML, XML.length - 1)), "synthetic-idle-timeout", true);
        for (int code : new int[]{-16, -27, -28}) {
            byte[] body = ("<plist><dict><key>status</key><integer>" + code + "</integer></dict></plist>").getBytes("UTF-8");
            responseCase("acp-status-" + code, reply("HTTP/1.1 200 Fixture", "Content-Length: " + body.length + "\r\n", body), "result=" + code);
        }
    }
    private static void queueOrder() throws Exception {
        final State state = new State(); state.drops = 1;
        final CommunicationsManager manager = (CommunicationsManager) unsafe().allocateInstance(CommunicationsManager.class);
        set(manager, "queue", new LinkedList<Object>());
        set(manager, "system", unsafe().allocateInstance(FakeSystem.class));
        set(manager, "connection", transport(new MemoryConnection(state))); set(manager, "connected", true);
        final Object[] contexts = {new Object(), new Object()};
        final int[] count = new int[2];
        final Thread thread = Thread.currentThread();
        CommunicationHandler handler = new CommunicationHandler() {
            public void handleResponse(RaidSystem system, Response response, Object context) {
                check(Thread.currentThread() == thread, "Unexpected queue callback thread");
                try {
                    if (response.getType() == Response.TYPE_CONNECT) {
                        check(++count[0] == 1 && context == null && response.getResultCode() == -101, "Unexpected queue reconnect");
                        set(manager, "connection", transport(new MemoryConnection(state))); set(manager, "connected", true);
                    } else {
                        check(count[1] < 2 && context == contexts[count[1]] && response.getResultCode() == 0, "Queue callback order differs");
                        if (++count[1] == 2) manager.shutdown();
                    }
                } catch (Exception e) { throw new AssertionError("Queue fixture injection failed"); }
            }
        };
        AcpxMessageFactory factory = new AcpxMessageFactory();
        manager.postMessageAsync(handler, factory.newGetStatusRequest(), contexts[0]);
        manager.postMessageAsync(handler, factory.newGetTimeRequest(), contexts[1]);
        manager.run();
        check(count[0] == 1 && count[1] == 2 && state.sent.size() == 3, "Queue counts differ");
        check(Arrays.equals(state.sent.get(0), state.sent.get(1)) && !Arrays.equals(state.sent.get(1), state.sent.get(2)), "Queue wire order differs");
        check(state.connections.equals(Arrays.asList(1, 2, 2)), "Queue connection sequence differs");
        emit("queue_order first-first-second; connections 1-2-2; callbacks first-second; reconnects=1");
    }
    private static void dispatch(final RequestMessage request, int drops, boolean malformed) throws Exception {
        dispatch(request, drops, malformed, null, malformed ? -103 : 0, drops, "legacy");
    }
    private static void dispatch(final RequestMessage request, int drops, boolean malformed, byte[] raw, final int result, int reconnects, String label) throws Exception {
        final State state = new State(); state.drops = drops; state.malformed = malformed;
        state.rawResponse = raw;
        final CommunicationsManager manager = (CommunicationsManager) unsafe().allocateInstance(CommunicationsManager.class);
        set(manager, "queue", new LinkedList<Object>());
        set(manager, "system", unsafe().allocateInstance(FakeSystem.class));
        set(manager, "connection", transport(new MemoryConnection(state))); set(manager, "connected", true);
        final int[] callbacks = new int[2];
        final Object context = new Object();
        final Thread dispatchThread = Thread.currentThread();
        manager.postMessageAsync(new CommunicationHandler() {
            public void handleResponse(RaidSystem system, Response response, Object received) {
                try {
                    if (response.getType() == Response.TYPE_CONNECT) {
                        check(Thread.currentThread() == dispatchThread, "Asynchronous fixture callback");
                        check(received == null && response.getResultCode() == -101, "Unexpected reconnect callback");
                        if (++callbacks[0] > 8) throw new AssertionError("Fixture retry bound exceeded");
                        // doConnect's invalid-address callback is a test seam. Real TCP/backoff is excluded.
                        set(manager, "connection", transport(new MemoryConnection(state))); set(manager, "connected", true);
                    } else {
                        check(received == context, "Callback context lost");
                        check(response.getResultCode() == result, "Unexpected terminal result");
                        callbacks[1]++; manager.shutdown();
                    }
                } catch (Exception e) { throw new AssertionError("Fixture injection failed"); }
            }
        }, request, context);
        manager.run();
        check(callbacks[1] == 1, "Terminal callback not exactly once");
        check(callbacks[0] == reconnects, "Unexpected retry count");
        check(state.sent.size() == reconnects + 1, "Unexpected send count");
        for (byte[] sent : state.sent) check(Arrays.equals(sent, state.sent.get(0)), "Retry wire differs");
        if (raw == null) emit("dispatch drops=" + drops + " malformed=" + malformed + " sends=" + state.sent.size() + " terminal_callbacks=" + callbacks[1]);
        else emit("queue_response " + label + " result=" + result + " sends=" + state.sent.size() + " terminal_callbacks=" + callbacks[1]);
    }
    private static void queueResponses() throws Exception {
        AcpxMessageFactory factory = new AcpxMessageFactory();
        for (int code : new int[]{401, 403, 500})
            dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 " + code + " Fixture", "Content-Length: " + XML.length + "\r\n", XML), 0, 0, "http-" + code);
        for (int code : new int[]{-16, -27, -28}) {
            byte[] body = ("<plist><dict><key>status</key><integer>" + code + "</integer></dict></plist>").getBytes("UTF-8");
            dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 200 Fixture", "Content-Length: " + body.length + "\r\n", body), code, 0, "acp-" + code);
        }
        dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 200 Fixture", "content-length: " + XML.length + "\r\n", XML), 0, 0, "lowercase-length-empty-success");
        dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 200 Fixture", "Content-Length: fixture\r\n", XML), -102, 0, "invalid-length");
        dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 200 Fixture", "Content-Length: " + XML.length + "\r\n", Arrays.copyOf(XML, XML.length - 1)), 0, 1, "truncated-retry-then-valid");
    }
    private static final class SingleUseInput extends InputStream {
        final boolean throwsAfterClose;
        boolean closed;
        int index;
        SingleUseInput(boolean mode) { throwsAfterClose = mode; }
        @Override public int read() throws IOException {
            if (closed && throwsAfterClose) throw new IOException("synthetic closed stream");
            if (closed || index >= 4) return -1;
            return ++index;
        }
        @Override public void close() { closed = true; }
    }
    private static void firmwareStream(boolean throwsAfterClose) throws Exception {
        State state = new State(); state.drops = 1;
        RequestMessage request = new UpdateFirmwareRequest(RequestMessage.TARGET_TOP, 0, 0, new SingleUseInput(throwsAfterClose));
        RequestMessage clone = (RequestMessage) request.clone();
        try { transport(new MemoryConnection(state)).send(clone); throw new AssertionError("Synthetic loss absent"); }
        catch (IOException expected) { }
        check(state.sent.size() == 1, "First firmware memory send absent");
        byte[] first = state.sent.get(0);
        check(new String(first, "US-ASCII").contains("Content-Length: 4\r\n"), "First body length differs");
        check(Arrays.equals(Arrays.copyOfRange(first, first.length - 4, first.length), new byte[]{1,2,3,4}), "First firmware body differs");
        boolean failed = false;
        try { transport(new MemoryConnection(state)).send(clone); }
        catch (IOException expected) { failed = true; }
        check(failed == throwsAfterClose, "Unexpected stream-retry result");
        check(state.sent.size() == (throwsAfterClose ? 1 : 2), "Unexpected firmware memory sends");
        if (!throwsAfterClose) {
            String second = new String(state.sent.get(1), "US-ASCII");
            check(second.contains("Content-Length: 0\r\n"), "Exhausted stream body not empty");
        }
        emit("synthetic firmware stream throws_after_close=" + throwsAfterClose + " memory_sends=" + state.sent.size());
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        check(args.length == 0 || (args.length == 1 && Arrays.asList("default-logging","parser-policy","parser-policy-default-logging","allocation-policy","allocation-policy-default-logging","header-policy","header-policy-default-logging").contains(args[0])), "Unknown fixture arguments");
        boolean defaultLogging = args.length == 1 && (args[0].equals("default-logging") || args[0].endsWith("-default-logging"));
        boolean parserPolicy = args.length == 1 && args[0].startsWith("parser-policy");
        PrintStream previous = System.err;
        PrintStream previousOut = System.out; fixtureOut = previousOut;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        ByteArrayOutputStream capturedOut = new ByteArrayOutputStream();
        try {
            System.setErr(new PrintStream(captured,true,"UTF-8"));
            System.setOut(new PrintStream(capturedOut,true,"UTF-8"));
            if(args.length==1 && args[0].startsWith("header-policy")) headerPolicy(defaultLogging);
            else if(args.length==1 && args[0].startsWith("allocation-policy")) allocationPolicy(defaultLogging);
            else execute(defaultLogging,parserPolicy);
            check(captured.toString("UTF-8").equals(defaultLogging ? "RAID_ADMIN_ERROR\n" : ""), "Unexpected logging output");
            check(capturedOut.size() == 0, "Unexpected application stdout");
        } finally {
            System.setErr(previous);
            System.setOut(previousOut);
            OfflineGuard.assertUntouched();
        }
    }
    private static void followOn(boolean allocation) throws Exception {
        followOn(allocation?"allocation-limit":"invalid-length",reply("HTTP/1.1 200 Fixture","Content-Length: "+(allocation?"2147483647":"fixture")+"\r\n",new byte[0]));
    }
    private static void followOn(final String label,byte[] raw)throws Exception {
        final State state=new State();state.rawResponse=raw;
        final MemoryConnection memory=new MemoryConnection(state);
        final CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);
        set(manager,"queue",new LinkedList<Object>());set(manager,"system",unsafe().allocateInstance(FakeSystem.class));
        set(manager,"connection",transport(memory));set(manager,"connected",true);
        final int[] callbacks={0};final Object[] contexts={new Object(),new Object()};
        final Field outstanding=HttpConnection.class.getDeclaredField("requestOutstanding");outstanding.setAccessible(true);
        CommunicationHandler handler=new CommunicationHandler() {
            public void handleResponse(RaidSystem system,Response response,Object context) {
                check(response.getType()==Response.TYPE_COMMAND && response.getResultCode()==-102 && callbacks[0]<2 && context==contexts[callbacks[0]],"Follow-on response differs");
                try {check(outstanding.getBoolean(memory),"Outstanding state changed");}catch(Exception failure){throw new AssertionError("Follow-on inspection failed");}
                if(++callbacks[0]==2)manager.shutdown();
            }
        };
        AcpxMessageFactory factory=new AcpxMessageFactory();
        manager.postMessageAsync(handler,factory.newGetStatusRequest(),contexts[0]);manager.postMessageAsync(handler,factory.newGetTimeRequest(),contexts[1]);manager.run();
        check(callbacks[0]==2 && state.sent.size()==1,"Follow-on sends differ");
        emit("follow_on "+label+" results=-102,-102; sends=1; outstanding=true; reconnects=0");
    }
    private static void headerPolicy(boolean defaultLogging)throws Exception {
        if(!defaultLogging)org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        StringBuilder line=new StringBuilder("X: ");for(int i=0;i<65534;i++)line.append('x');line.append("\r\n");
        StringBuilder fields=new StringBuilder();for(int i=0;i<129;i++)fields.append("X: x\r\n");
        byte[][] cases={boundedReply("HTTP/1.1 200 X",line.toString(),new byte[0],2097152),
            reply("HTTP/1.1 200 X",fields.toString(),new byte[0]),HeaderObservation.totalHeader(1048577).getBytes("US-ASCII")};
        String[] labels={"line","count","aggregate"};
        for(int i=0;i<cases.length;i++) {
            check(cases[i].length<=1048577,"Header fixture bound exceeded");State state=new State();state.rawResponse=cases[i];
            try{transport(new MemoryConnection(state)).send(new AcpxMessageFactory().newGetStatusRequest());throw new AssertionError("Header quota not enforced");}
            catch(IllegalArgumentException expected){check("Response headers exceed limit".equals(expected.getMessage()),"Wrong header rejection");}
            check(state.sent.size()==1,"Header sends differ");
            dispatch(new AcpxMessageFactory().newGetStatusRequest(),0,false,cases[i],-102,0,"header-"+labels[i]);
        }
        emit("header follow-on recovery qualified separately");
        emit("PASS header quota observations; guarded_operations=0");
    }
    private static void allocationPolicy(boolean defaultLogging) throws Exception {
        if(!defaultLogging) org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        Class<?> helper=Class.forName("compat.BoundedResponseBuffer");
        check(helper.getSuperclass()==ByteArrayOutputStream.class,"Allocation superclass differs");
        java.lang.reflect.Method gate=helper.getDeclaredMethod("checkLength",int.class);gate.setAccessible(true);
        for(int value:(lengthPolicy()?new int[]{0,1,16777215,16777216}:new int[]{-1,0,1,16777215,16777216}))check(((Integer)gate.invoke(null,value)).intValue()==value,"Allowed allocation boundary differs");
        for(int value:new int[]{16777217,Integer.MAX_VALUE}) {
            try {gate.invoke(null,value);throw new AssertionError("Allocation quota not enforced");}
            catch(java.lang.reflect.InvocationTargetException expected) {check(expected.getCause() instanceof IllegalArgumentException && "Response length exceeds limit".equals(expected.getCause().getMessage()),"Allocation quota failure differs");}
            byte[] raw=reply("HTTP/1.1 200 Fixture","Content-Length: "+value+"\r\n",new byte[0]);
            State state=new State();state.rawResponse=raw;
            try {transport(new MemoryConnection(state)).send(new AcpxMessageFactory().newGetStatusRequest());throw new AssertionError("Oversized body accepted");}
            catch(IllegalArgumentException expected) {check("Response length exceeds limit".equals(expected.getMessage()),"Wrong allocation rejection");}
            check(state.sent.size()==1,"Allocation send count differs");
            emit("response allocation-"+value+" rejected-before-body");
            dispatch(new AcpxMessageFactory().newGetStatusRequest(),0,false,raw,-102,0,"allocation-"+value);
        }
        byte[] ceiling=reply("HTTP/1.1 200 Fixture","Content-Length: 16777216\r\n",new byte[0]);
        responseCase("allocation-ceiling-truncated",ceiling,"io-error");
        dispatch(new AcpxMessageFactory().newGetStatusRequest(),0,false,ceiling,0,1,"allocation-ceiling-truncated-retry");
        emit("allocation follow-on recovery qualified separately");
        emit("PASS response allocation observations; guarded_operations=0");
    }
    private static void execute(boolean defaultLogging, boolean parserPolicy) throws Exception {
        if (!defaultLogging) {
        org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getRootLogger().setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.CommunicationsManager").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.AcpxConnection").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.HttpConnection").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.HttpRequest").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.HttpResponse").setLevel(org.apache.log4j.Level.OFF);
        }
        if(parserPolicy) {
            AcpxMessageFactory factory=new AcpxMessageFactory();
            StringBuilder xml=new StringBuilder("<!DOCTYPE plist SYSTEM \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\" [<!ENTITY e \"x\">]><plist><string>");
            for(int i=0;i<4100;i++)xml.append("&e;");xml.append("</string></plist>");
            byte[] body=xml.toString().getBytes("UTF-8");
            dispatch(factory.newGetStatusRequest(),0,false,boundedReply("HTTP/1.1 200 Fixture","Content-Length: "+body.length+"\r\n",body,524288),-103,0,"entity-quota");
            xml=new StringBuilder("<!DOCTYPE plist SYSTEM \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist>");
            for(int i=0;i<31;i++)xml.append("<array>");xml.append("<string>fixture</string>");for(int i=0;i<31;i++)xml.append("</array>");xml.append("</plist>");
            body=xml.toString().getBytes("UTF-8");
            dispatch(factory.newGetStatusRequest(),0,false,reply("HTTP/1.1 200 Fixture","Content-Length: "+body.length+"\r\n",body),-103,0,"depth-quota");
            body="<!DOCTYPE plist [<!ENTITY e SYSTEM \"file:///__raid_security_fixture__/secret\">]><plist><string>&e;</string></plist>".getBytes("UTF-8");
            dispatch(factory.newGetStatusRequest(),0,false,reply("HTTP/1.1 200 Fixture","Content-Length: "+body.length+"\r\n",body),-103,0,"blocked-entity");
            dispatch(factory.newGetStatusRequest(),0,true);
            OfflineGuard.assertUntouched();
            emit("PASS parser failures: -103 terminal, one send each, no requeue; guarded_operations=0");
            return;
        }
        AcpxMessageFactory factory = new AcpxMessageFactory();
        RequestMessage request = factory.newGetStatusRequest();
        request.setUser("synthetic-user"); request.setPassword("synthetic-not-a-credential");
        request.setTargetController(RequestMessage.TARGET_TOP);
        State state = new State();
        MemoryConnection memory = new MemoryConnection(state);
        Object parsed = transport(memory).send(request).getRootElement();
        check(parsed instanceof Map && "ok".equals(((Map) parsed).get("fixture")), "ACP plist parse failed");
        String wire = new String(state.sent.get(0), "UTF-8");
        check(wire.contains("ACP-User: synthetic-user\r\n"), "User header missing");
        check(wire.contains("ACP-Password: synthetic-not-a-credential\r\n"), "Password header missing");
        check(wire.contains("User-Agent: Apple-Xserve_RAID_Admin/1.6.0\r\n"), "User agent differs");
        check(wire.contains("Apple-Xsync: top\r\n"), "Target header differs");
        emit("ACP synthetic authentication/target/user-agent and plist parsing PASS; fixture prints no header values");
        dispatch(factory.newGetStatusRequest(), 1, false);
        dispatch(factory.newSetTimeRequest(new Date(0)), 1, false);
        dispatch(factory.newSetTimeRequest(new Date(0)), 4, false);
        dispatch(factory.newGetStatusRequest(), 0, true);
        responses();
        queueResponses();
        queueOrder();
        if(lengthPolicy())emit("security_length follow-on qualified by recovery fixture");else followOn(false);
        firmwareStream(false);
        firmwareStream(true);
        OfflineGuard.assertUntouched();
        emit("PASS memory-only transport and queue observations; real reconnection/backoff excluded");
    }
}
