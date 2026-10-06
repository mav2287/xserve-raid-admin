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
    private static boolean unsafeWorkerFailureObserved;
    private static boolean unsafeSyncEnqueueObserved;
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
        int nullDrops;
        IOException injectedFailure;
        RuntimeException injectedRuntime;
        boolean clearOutstandingBeforeFailure;
        int preRequestFaultCalls;
        CommunicationsManager stopOnSecondResponse;
        int writeFault=-1;
        boolean bodyWriteFault;
        boolean bodyFaultReached;
        int failureAfter=1;
        int attempts;
        int partialBytes;
        int closeFailures;
        int closes;
        boolean unsafeFailureObserved;
        boolean prewriteFailure;
        boolean nonpersistent;
        boolean legacyBodyCodec;
        boolean malformed;
        byte[] rawResponse;
        boolean idleOpen;
    }
    private static final class MemoryConnection extends HttpConnection {
        ByteArrayOutputStream pending;
        final State state;
        final int ordinal;
        MemoryConnection(State state) throws IOException { super("127.0.0.1"); setPersistent(true); this.state = state; ordinal = ++state.connectionCount; }
        @Override OutputStream getOutputStream() throws IOException {
            check(++state.attempts<=16,"Fixture attempt bound exceeded");
            if(state.prewriteFailure){state.prewriteFailure=false;throw new java.net.ConnectException("DO_NOT_RENDER_PREWRITE");}
            pending = new ByteArrayOutputStream();
            if(state.writeFault>=0||state.bodyWriteFault){final int count=state.writeFault;state.writeFault=-1;return new OutputStream(){
                private int tail;
                private boolean body;
                public void write(int b)throws IOException{if(body&&state.bodyWriteFault){state.bodyFaultReached=true;throw new IOException("DO_NOT_RENDER_BODY_WRITE");}if(state.partialBytes==count)throw new IOException("DO_NOT_RENDER_WRITE");pending.write(b);state.partialBytes++;tail=(tail<<8)|(b&255);if(tail==0x0d0a0d0a)body=true;}
            };}
            return pending;
        }
        @Override InputStream getInputStream() throws IOException {
            if (pending == null) throw new AssertionError("Response before request");
            check(state.sent.size() < 16, "Fixture send bound exceeded");
            state.sent.add(pending.toByteArray()); pending = null;
            state.connections.add(ordinal);
            if(state.stopOnSecondResponse!=null&&state.sent.size()==2)state.stopOnSecondResponse.shutdown();
            if(state.clearOutstandingBeforeFailure&&(state.injectedRuntime!=null||state.injectedFailure!=null))setRequestOutstanding(false);
            if(state.injectedRuntime!=null){RuntimeException failure=state.injectedRuntime;state.injectedRuntime=null;throw failure;}
            if(state.injectedFailure!=null&&state.attempts>=state.failureAfter){IOException failed=state.injectedFailure;state.injectedFailure=null;throw failed;}
            if(state.nullDrops>0){state.nullDrops--;throw new IOException();}
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
        @Override public void disconnect() throws IOException { state.closes++;if(state.closeFailures>0){state.closeFailures--;throw new IOException("DO_NOT_RENDER_CLEANUP");} }
        @Override public void setTimeout(int timeout) { }
    }
    private static AcpxConnection transport(MemoryConnection memory) throws Exception {
        AcpxConnection acp = (AcpxConnection) unsafe().allocateInstance(AcpxConnection.class);
        acp.host = "127.0.0.1"; acp.persistent = !memory.state.nonpersistent; acp.encrypted=memory.state.legacyBodyCodec; acp.connection = memory;
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
    private static boolean invalidHeaderPolicy()throws Exception {
        try{Class.forName("compat.ResponseFraming").getMethod("invalidHeader");return true;}
        catch(ClassNotFoundException absent){return false;}catch(NoSuchMethodException absent){return false;}
    }
    private static boolean framingPolicy()throws Exception {
        try{Class.forName("compat.ResponseFraming");return true;}catch(ClassNotFoundException absent){return false;}
    }
    private static void responseCase(String label, byte[] raw, String expected) throws Exception {
        responseCase(label, raw, expected, false);
    }
    private static void responseCase(String label, byte[] raw, String expected, boolean idle) throws Exception {
        State state = new State(); state.rawResponse = raw; state.idleOpen = idle;
        boolean framing=framingPolicy();
        String framingMessage=null;
        if(label.equals("invalid-header")&&invalidHeaderPolicy()){framingMessage="Response header is invalid";expected="framing-rejected";}
        if(framing) {
            if(label.equals("missing-length")||label.equals("missing-length-idle"))framingMessage="Response length is missing";
            if(label.equals("duplicate-last-valid")||label.equals("duplicate-last-zero"))framingMessage="Response length is ambiguous";
            if(label.equals("chunked"))framingMessage="Response transfer encoding is unsupported";
            if(framingMessage!=null)expected="framing-rejected";
            if(label.equals("lowercase-length"))expected="result=0";
        }
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
                  if(framingMessage!=null){check(framingMessage.equals(e.getMessage())&&e.getCause()==null&&acp.connection==null,"Framing marker differs");outcome="framing-rejected";}
                  else {
                  check(lengthPolicy() && Arrays.asList("invalid-length","negative-length","overflow-length").contains(label) && "Response length is invalid".equals(e.getMessage()) && e.getCause()==null && acp.connection==null,"Invalid marker differs");
                  emit("security_length "+label+" fixed-marker; closed; no-input-or-cause");outcome=expected;
                  }
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
    private static boolean terminalIoPolicy() throws Exception {
        try{return Class.forName("compat.RejectionRecovery").getField("TERMINATES_AMBIGUOUS_IO").getBoolean(null);}
        catch(ClassNotFoundException absent){return false;}catch(NoSuchFieldException absent){return false;}
    }
    private static void queueOrder() throws Exception {
        final boolean terminal=terminalIoPolicy();
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
                        check(count[1] < 2 && context == contexts[count[1]] && response.getResultCode() == (terminal?-102:0), "Queue callback order differs");
                        if(terminal)check(manager.isStopped(), "Queue session not stopped before callback");
                        if (++count[1] == 2) manager.shutdown();
                    }
                } catch (Exception e) { throw new AssertionError("Queue fixture injection failed"); }
            }
        };
        AcpxMessageFactory factory = new AcpxMessageFactory();
        manager.postMessageAsync(handler, factory.newGetStatusRequest(), contexts[0]);
        manager.postMessageAsync(handler, terminal?factory.newRestartSystemRequest():factory.newGetTimeRequest(), contexts[1]);
        manager.run();
        if(terminal){
            check(count[0]==0&&count[1]==2&&state.sent.size()==1&&state.connections.equals(Arrays.asList(1)), "Terminal queue counts differ");
            emit("queue_order first-only; connections 1; callbacks first-second; blocked-followup=true; reconnects=0");return;
        }
        check(count[0] == 1 && count[1] == 2 && state.sent.size() == 3, "Queue counts differ");
        check(Arrays.equals(state.sent.get(0), state.sent.get(1)) && !Arrays.equals(state.sent.get(1), state.sent.get(2)), "Queue wire order differs");
        check(state.connections.equals(Arrays.asList(1, 2, 2)), "Queue connection sequence differs");
        emit("queue_order first-first-second; connections 1-2-2; callbacks first-second; reconnects=1");
    }
    private static void dispatch(final RequestMessage request, int drops, boolean malformed) throws Exception {
        dispatch(request, drops, malformed, null, malformed ? -103 : 0, drops, "legacy");
    }
    private static void dispatch(final RequestMessage request, int drops, boolean malformed, byte[] raw, final int result, int reconnects, String label) throws Exception {
        final boolean terminal=terminalIoPolicy()&&result==0&&reconnects>0;
        final boolean healthyReply=label.startsWith("acp-")||label.startsWith("http-");
        final int expectedResult=terminal?-102:result;
        final int expectedReconnects=terminal?0:reconnects;
        if(terminal&&label.equals("truncated-retry-then-valid"))label="truncated-terminal";
        if(terminal&&label.equals("allocation-ceiling-truncated-retry"))label="allocation-ceiling-truncated-terminal";
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
                        check(response.getResultCode() == expectedResult, "Unexpected terminal result");
                        if(terminal){Exception e=response.getException();check(manager.isStopped()&&!manager.isConnected()&&e!=null&&e.getClass().getName().equals("compat.UntrustedResponseException")&&"Response transport failed; outcome is unconfirmed".equals(e.getMessage())&&e.getCause()==null,"Ambiguous IO not contained");}
                        if(expectedResult==-103)check(manager.isStopped()==operationFailureStop(),"Parser-prefix stop policy differs");
                        else if(healthyReply||(!terminal&&expectedResult!=-102))check(!manager.isStopped(),"Healthy policy changed");
                        callbacks[1]++; manager.shutdown();
                    }
                } catch (Exception e) { throw new AssertionError("Fixture injection failed"); }
            }
        }, request, context);
        manager.run();
        check(callbacks[1] == 1, "Terminal callback not exactly once");
        check(callbacks[0] == expectedReconnects, "Unexpected retry count");
        check(state.sent.size() == expectedReconnects + 1, "Unexpected send count");
        for (byte[] sent : state.sent) check(Arrays.equals(sent, state.sent.get(0)), "Retry wire differs");
        if (raw == null) emit("dispatch drops=" + drops + " malformed=" + malformed + " sends=" + state.sent.size() + " terminal_callbacks=" + callbacks[1]);
        else emit("queue_response " + label + " result=" + expectedResult + " sends=" + state.sent.size() + " terminal_callbacks=" + callbacks[1]);
    }
    private static void queueResponses() throws Exception {
        AcpxMessageFactory factory = new AcpxMessageFactory();
        for (int code : new int[]{401, 403, 500})
            dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 " + code + " Fixture", "Content-Length: " + XML.length + "\r\n", XML), 0, 0, "http-" + code);
        for (int code : new int[]{-16, -27, -28}) {
            byte[] body = ("<plist><dict><key>status</key><integer>" + code + "</integer></dict></plist>").getBytes("UTF-8");
            dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 200 Fixture", "Content-Length: " + body.length + "\r\n", body), code, 0, "acp-" + code);
        }
        dispatch(factory.newGetStatusRequest(), 0, false, reply("HTTP/1.1 200 Fixture", "content-length: " + XML.length + "\r\n", XML), 0, 0, framingPolicy()?"lowercase-length-parsed-success":"lowercase-length-empty-success");
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
        check(args.length == 0 || (args.length == 1 && Arrays.asList("default-logging","parser-policy","parser-policy-default-logging","allocation-policy","allocation-policy-default-logging","header-policy","header-policy-default-logging","io-characterization","null-io-policy","terminal-io-policy","operation-failure-characterization","worker-failure-policy","verify-worker-stop-prefix","verify-worker-stop-report","verify-worker-stop-shim","verify-worker-stop-tail","verify-manager-unsafe-policy","verify-manager-corrupt","sync-preenqueue-original","sync-preenqueue-candidate","verify-sync-preenqueue").contains(args[0])), "Unknown fixture arguments");
        boolean defaultLogging = args.length == 1 && (args[0].equals("default-logging") || args[0].endsWith("-default-logging"));
        boolean parserPolicy = args.length == 1 && args[0].startsWith("parser-policy");
        PrintStream previous = System.err;
        PrintStream previousOut = System.out; fixtureOut = previousOut;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        ByteArrayOutputStream capturedOut = new ByteArrayOutputStream();
        try {
            System.setErr(new PrintStream(captured,true,"UTF-8"));
            System.setOut(new PrintStream(capturedOut,true,"UTF-8"));
            if(args.length==1 && args[0].equals("verify-manager-corrupt")) {
                try{Class.forName("com.apple.xsr.net.CommunicationsManager").getDeclaredMethods();throw new AssertionError("Corrupt manager verified");}
                catch(VerifyError expected){emit("PASS corrupt manager rejected by verifier; guarded_operations=0");}
            }
            else if(args.length==1 && args[0].equals("verify-manager-unsafe-policy")) {
                Class.forName("com.apple.xsr.net.CommunicationsManager").getDeclaredMethods();
                org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
                State unsafeState=new State();unsafeState.injectedFailure=new IOException("DO_NOT_RENDER_UNSAFE");
                boolean rejected=false;try{fixedFailure(unsafeState,"unsafe-negative",false,1);}catch(AssertionError expected){rejected=unsafeState.unsafeFailureObserved;}
                check(rejected,"Unsafe semantic policy not specifically observed");OfflineGuard.assertUntouched();emit("PASS verified unsafe manager fails containment fixture; guarded_operations=0");
            }
            else if(args.length==1 && args[0].equals("verify-sync-preenqueue")) {
                Class.forName("com.apple.xsr.net.CommunicationsManager$SyncSender").getDeclaredMethods();
                unsafeSyncEnqueueObserved=false;boolean rejected=false;
                try{syncPreenqueue(true);}catch(AssertionError expected){rejected=unsafeSyncEnqueueObserved;}
                check(rejected,"Unsafe sync enqueue not specifically observed");OfflineGuard.assertUntouched();emit("PASS verified preenqueue bypass fails queue fixture; guarded_operations=0");
            }
            else if(args.length==1 && args[0].startsWith("sync-preenqueue-")) syncPreenqueue(args[0].endsWith("candidate"));
            else if(args.length==1 && args[0].startsWith("verify-worker-stop-")) {
                Class.forName("com.apple.xsr.net.CommunicationsManager").getDeclaredMethods();Class.forName("compat.RejectionRecovery").getDeclaredMethods();unsafeWorkerFailureObserved=false;
                boolean rejected=false;try{operationFailures(new String[]{args[0].endsWith("prefix")||args[0].endsWith("tail")?"prefix":args[0].endsWith("shim")?"shim":"generic"});}catch(AssertionError expected){rejected=unsafeWorkerFailureObserved;}
                check(rejected,"Worker-stop bypass not specifically observed");OfflineGuard.assertUntouched();emit("PASS verified worker-stop bypass fails sequencing fixture; guarded_operations=0");
            }
            else if(args.length==1 && args[0].equals("worker-failure-policy")) {operationFailures();workerFailureExtras();}
            else if(args.length==1 && args[0].equals("operation-failure-characterization")) operationFailures();
            else if(args.length==1 && args[0].equals("terminal-io-policy")) terminalIoFaults();
            else if(args.length==1 && args[0].equals("null-io-policy")) nullIoPolicy();
            else if(args.length==1 && args[0].equals("io-characterization")) ioCharacterization();
            else if(args.length==1 && args[0].startsWith("header-policy")) headerPolicy(defaultLogging);
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
    private static CommunicationsManager ioManager(State state)throws Exception {
        CommunicationsManager m=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);
        set(m,"queue",new LinkedList<Object>());set(m,"system",unsafe().allocateInstance(FakeSystem.class));
        set(m,"connection",transport(new MemoryConnection(state)));set(m,"connected",true);return m;
    }
    private static boolean nullIoFixed()throws Exception {
        try{Class.forName("compat.RejectionRecovery").getMethod("nullMessage");return true;}
        catch(ClassNotFoundException absent){return false;}catch(NoSuchMethodException absent){return false;}
    }
    private static void nullMessage()throws Exception {
        if(nullIoFixed()){
            fixedNull(new IOException(),"base",false);
            emit("io null-message terminal=-102; callbacks=1; failed_sends=1; "+(sessionContainment()?"next_distinct=-102; session-stopped":"next_distinct=0; worker-survives"));return;
        }
        final State state=new State();state.nullDrops=1;final CommunicationsManager m=ioManager(state);
        final int[] callbacks={0};final Throwable[] escaped={null};final Object context=new Object();
        CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object seen){callbacks[0]++;m.shutdown();}};
        m.postMessageAsync(handler,new AcpxMessageFactory().newGetStatusRequest(),context);
        Thread worker=new Thread(new Runnable(){public void run(){m.run();}},"io-null-fixture");
        worker.setDaemon(true);worker.setUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler(){public void uncaughtException(Thread thread,Throwable failure){escaped[0]=failure;}});
        try {
            worker.start();worker.join(2000);
            check(!worker.isAlive() && escaped[0] instanceof NullPointerException,"Null IO did not escape worker");
            StackTraceElement first=escaped[0].getStackTrace()[0];
            check(first.getClassName().equals("com.apple.xsr.net.CommunicationsManager")&&first.getMethodName().equals("run"),"Unexpected null IO throw site");
            check(callbacks[0]==0 && state.sent.size()==1 && !m.isStopped() && m.isConnected(),"Unexpected lost transaction state");
            Field q=CommunicationsManager.class.getDeclaredField("queue");q.setAccessible(true);
            check(((LinkedList)q.get(m)).isEmpty(),"Failed transaction still queued");
            m.postMessageAsync(handler,new AcpxMessageFactory().newGetTimeRequest(),new Object());
            check(((LinkedList)q.get(m)).size()==1 && !worker.isAlive() && callbacks[0]==0,"Later post did not remain queued");
            emit("io null-message worker-escaped=NPE; callbacks=0; sends=1; stopped=false; connected=true; later_queue=1");
        }finally{m.shutdown();worker.interrupt();worker.join(2000);check(!worker.isAlive(),"Fixture worker did not end");}
    }
    private static final class ChangingMessage extends IOException {
        final boolean firstNull;int calls;
        ChangingMessage(boolean value){firstNull=value;}
        @Override public String getMessage(){return calls++==0?(firstNull?null:"synthetic retry"):firstNull?"synthetic retry":null;}
    }
    private static boolean sessionContainment()throws Exception {
        try{return Class.forName("compat.RejectionRecovery").getField("STOPS_REJECTED_SESSIONS").getBoolean(null);}
        catch(ClassNotFoundException absent){return false;}catch(NoSuchFieldException absent){return false;}
    }
    private static void fixedNull(IOException failure,String label,boolean print)throws Exception {
        State state=new State();state.injectedFailure=failure;fixedFailure(state,label,print,1);
    }
    private static void fixedFailure(final State state,String label,boolean print,final int sentCount)throws Exception {
        final boolean containment=sessionContainment();final CommunicationsManager m=ioManager(state);
        final Object[] contexts={new Object(),new Object()};final int[] callbacks={0},connects={0};final Throwable[] escaped={null};
        CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object seen){
            try {
                if(response.getType()==Response.TYPE_CONNECT){check(callbacks[0]==1&&connects[0]++==0&&response.getResultCode()==-101,"Unexpected fresh reconnect");set(m,"connection",transport(new MemoryConnection(state)));set(m,"connected",true);return;}
                int i=callbacks[0]++;check(i<2&&seen==contexts[i]&&response.getResultCode()==(i==0||containment?-102:0),"Null IO callback differs");
                if(i==0){Exception e=response.getException();state.unsafeFailureObserved=e==null||!e.getClass().getName().equals("compat.UntrustedResponseException")||!m.isStopped()||m.isConnected();check(e!=null&&e.getClass().getName().equals("compat.UntrustedResponseException")&&"Response transport failed; outcome is unconfirmed".equals(e.getMessage())&&e.getCause()==null&&!m.isConnected()&&m.isStopped()==containment&&state.sent.size()==sentCount,"Null IO terminal state differs");}
                else m.shutdown();
            }catch(Exception e){throw new AssertionError("Null IO injection failed");}
        }};
        AcpxMessageFactory f=new AcpxMessageFactory();m.postMessageAsync(handler,containment?f.newSetTimeRequest(new Date(0)):f.newGetStatusRequest(),contexts[0]);m.postMessageAsync(handler,containment?f.newRestartSystemRequest():f.newGetTimeRequest(),contexts[1]);
        Thread worker=new Thread(new Runnable(){public void run(){m.run();}},"fixture-null-fixed");worker.setDaemon(true);worker.setUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler(){public void uncaughtException(Thread t,Throwable e){escaped[0]=e;}});
        try{worker.start();worker.join(5000);check(!worker.isAlive()&&escaped[0]==null&&callbacks[0]==2&&connects[0]==(containment?0:1)&&state.sent.size()==(containment?sentCount:2)&&(containment||!Arrays.equals(state.sent.get(0),state.sent.get(1))),"Null IO recovery differs");}
        finally{m.shutdown();worker.interrupt();worker.join(2000);check(!worker.isAlive(),"Null IO cleanup differs");}
        if(containment){
            int sent=state.sent.size();m.postMessageAsync(handler,f.newRestartSystemRequest(),new Object());
            Field queue=CommunicationsManager.class.getDeclaredField("queue");queue.setAccessible(true);
            check(((LinkedList)queue.get(m)).size()==1&&state.sent.size()==sent&&!worker.isAlive(),"Late async send escaped containment");
            try{m.postMessage(f.newRestartSystemRequest());throw new AssertionError("Stopped sync accepted");}
            catch(CommShutdownException expected){}
            check(state.sent.size()==sent,"Stopped sync send escaped containment");
        }
        if(print)emit("null_io "+label+" terminal=-102; fixed-no-cause; failed_sends=1; "+(containment?"next_distinct=-102; session-stopped":"next_distinct=0; worker-survives"));
    }
    private static Object queueValue(CommunicationsManager m)throws Exception{Field field=CommunicationsManager.class.getDeclaredField("queue");field.setAccessible(true);return field.get(m);}
    private static boolean operationFailureStop()throws Exception {
        try{return Class.forName("compat.RejectionRecovery").getField("STOPS_OPERATION_FAILURES").getBoolean(null);}
        catch(ClassNotFoundException absent){return false;}catch(NoSuchFieldException absent){return false;}
    }
    private static void operationFailures()throws Exception {operationFailures(new String[]{"prefix","shim","generic","before-request-creation"});}
    private static void operationFailures(String[] labels)throws Exception {
        org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        final boolean stopped=operationFailureStop();
        for(final String label:labels){
            final State state=new State();state.clearOutstandingBeforeFailure=true;final Exception failure;
            if(label.equals("prefix")){failure=new IOException("PropertyListException synthetic");state.injectedFailure=(IOException)failure;}
            else if(label.equals("shim")){failure=new sun.io.MalformedInputException();state.injectedFailure=(IOException)failure;}
            else {failure=new IllegalStateException("DO_NOT_RENDER_OPERATION_FAILURE");if(!label.equals("before-request-creation"))state.injectedRuntime=(RuntimeException)failure;}
            final CommunicationsManager m=ioManager(state);final Object[] contexts={new Object(),new Object()};final int[] count={0};
            final AcpxMessageFactory f=new AcpxMessageFactory();RequestMessage first=f.newSetTimeRequest(new Date(0));
            if(label.equals("before-request-creation")){
                final RequestMessage base=first;
                first=(RequestMessage)java.lang.reflect.Proxy.newProxyInstance(RequestMessage.class.getClassLoader(),new Class[]{RequestMessage.class},new java.lang.reflect.InvocationHandler(){public Object invoke(Object proxy,java.lang.reflect.Method method,Object[] args)throws Throwable{
                    if(method.getName().equals("clone"))return proxy;
                    if(method.getName().equals("getPath")){state.preRequestFaultCalls++;throw failure;}
                    try{return method.invoke(base,args);}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}
                }});
            }
            CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object seen){try{
                int i=count[0]++;check(i<2&&response.getType()!=Response.TYPE_CONNECT&&seen==contexts[i],"Operation callback order differs");
                check(response.getResultCode()==(i==0?(label.equals("prefix")?-103:-102):(stopped?-102:0)),"Operation result differs");
                if(i==0){unsafeWorkerFailureObserved=stopped&&!m.isStopped();check(state.closes==(stopped?1:0),"Worker fault close count differs");check(response.getException()==failure&&m.isStopped()==stopped&&m.isConnected()!=stopped,"Operation exception/stop state differs");if(stopped){int size=((LinkedList)queueValue(m)).size();try{m.postMessage(f.newRestartSystemRequest());throw new AssertionError("Stopped callback sync accepted");}catch(CommShutdownException expected){}check(((LinkedList)queueValue(m)).size()==size,"Stopped callback sync enqueued");}}
                else {if(stopped)check(response.getException() instanceof CommShutdownException,"Queued operation not shutdown");m.shutdown();}
            }catch(Exception e){throw new AssertionError("Operation fixture failed");}}};
            m.postMessageAsync(handler,first,contexts[0]);m.postMessageAsync(handler,f.newRestartSystemRequest(),contexts[1]);m.run();
            int firstAttempts=label.equals("before-request-creation")?0:1;
            check(count[0]==2&&state.attempts==firstAttempts+(stopped?0:1)&&state.sent.size()==firstAttempts+(stopped?0:1)&&state.preRequestFaultCalls==(label.equals("before-request-creation")?1:0)&&state.closes==1,"Operation send/close counts differ");
            if(!stopped)check(matchesBody(state.sent.get(state.sent.size()-1),f.newRestartSystemRequest()),"Follow-up bytes are not restart");
            emit("operation_failure "+label+" first="+(label.equals("prefix")?-103:-102)+" exception_identity=true stop_before_callback="+stopped+" attempts="+state.attempts+" response_entries="+state.sent.size()+" queued_restart="+(stopped?"blocked":"sent"));
        }
        OfflineGuard.assertUntouched();emit("PASS operation failure characterization; guarded_operations=0");
    }
    private static boolean matchesBody(byte[] wire,RequestMessage request)throws Exception {
        ByteArrayOutputStream body=new ByteArrayOutputStream();request.writeTo(body);
        for(int i=0;i+3<wire.length;i++)if(wire[i]==13&&wire[i+1]==10&&wire[i+2]==13&&wire[i+3]==10)return Arrays.equals(Arrays.copyOfRange(wire,i+4,wire.length),body.toByteArray());
        return false;
    }
    private static void workerFailureExtras()throws Exception {
        check(operationFailureStop(),"Worker-fault policy missing");
        for(final boolean throwConnect:new boolean[]{false,true}){
            final State state=new State();final CommunicationsManager m=ioManager(state);set(m,"connected",false);set(m,"connection",null);final int[] commands={0},connects={0};final RuntimeException thrown=new IllegalStateException("DO_NOT_RENDER_CONNECT_CALLBACK");
            CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){
                if(response.getType()==Response.TYPE_CONNECT){check(++connects[0]==1&&response.getResultCode()==-101&&!m.isStopped(),"Invalid-address seam differs");if(throwConnect)throw thrown;return;}
                int i=commands[0]++;check(i<2&&response.getResultCode()==-102&&m.isStopped()&&!m.isConnected(),"Connection worker fault not stopped");
                if(i==0)check(throwConnect?response.getException()==thrown:response.getException() instanceof NullPointerException,"Connection fault identity/type differs");else check(response.getException() instanceof CommShutdownException,"Connection follow-up not rejected");
            }};
            AcpxMessageFactory f=new AcpxMessageFactory();m.postMessageAsync(handler,f.newSetTimeRequest(new Date(0)));m.postMessageAsync(handler,f.newRestartSystemRequest());m.run();check(commands[0]==2&&connects[0]==1&&state.attempts==0&&state.sent.size()==0&&state.closes==0,"Connection worker fault wrote bytes");emit("worker_failure "+(throwConnect?"throwing-connect-callback":"null-connection")+" attempts=0 stopped=true queued_restart_blocked=true");
        }
        final State nul=new State();nul.injectedFailure=new IOException("PropertyListException synthetic");nul.clearOutstandingBeforeFailure=true;final CommunicationsManager nm=ioManager(nul);final int[] callback={0};AcpxMessageFactory f=new AcpxMessageFactory();
        nm.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){check(response.getResultCode()==-103&&nm.isStopped()&&!nm.isConnected(),"Null-handler prerequisite not stopped");callback[0]++;}},f.newSetTimeRequest(new Date(0)));nm.postMessageAsync(null,f.newRestartSystemRequest());nm.run();check(callback[0]==1&&nul.attempts==1&&nul.sent.size()==1&&nul.closes==1,"Null-handler queued write escaped");emit("worker_failure null-handler-restart attempts=1 callbacks=1 stopped=true queued_restart_blocked=true");
        final State healthy=new State();byte[] negative="<plist version=\"1.0\"><dict><key>status</key><integer>-27</integer></dict></plist>".getBytes("UTF-8");healthy.rawResponse=reply("HTTP/1.1 200 Fixture","Content-Length: "+negative.length+"\r\n",negative);final CommunicationsManager hm=ioManager(healthy);final int[] hc={0};
        CommunicationHandler good=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){check(!hm.isStopped()&&response.getResultCode()==(hc[0]==0?-27:0),"Healthy negative result stopped continuation");if(++hc[0]==2)hm.shutdown();}};hm.postMessageAsync(good,f.newGetStatusRequest());hm.postMessageAsync(good,f.newGetTimeRequest());hm.run();check(hc[0]==2&&healthy.attempts==2&&healthy.sent.size()==2,"Healthy follow-up missing");emit("worker_failure healthy-negative-reply callbacks=2 attempts=2 continued=true");
        final State sync=new State();sync.injectedFailure=new IOException("PropertyListException synthetic");final CommunicationsManager sm=ioManager(sync);final Throwable[] escaped={null};Thread worker=new Thread(new Runnable(){public void run(){sm.run();}},"fixture-worker-fault-sync");worker.setDaemon(true);worker.setUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler(){public void uncaughtException(Thread t,Throwable e){escaped[0]=e;}});
        try{worker.start();try{sm.postMessage(f.newSetTimeRequest(new Date(0)));throw new AssertionError("Faulted sync post accepted");}catch(IOException expected){check(expected.getClass()==IOException.class&&"PropertyListException synthetic".equals(expected.getMessage())&&expected.getCause()==null,"Faulted sync exception changed");}int size=((LinkedList)queueValue(sm)).size();try{sm.postMessage(f.newRestartSystemRequest());throw new AssertionError("Stopped next sync accepted");}catch(CommShutdownException expected){}check(((LinkedList)queueValue(sm)).size()==size&&sm.isStopped()&&!sm.isConnected(),"Next sync enqueued");worker.join(5000);check(!worker.isAlive()&&escaped[0]==null&&sync.attempts==1&&sync.sent.size()==1&&sync.closes==1,"Sync fault worker did not exit");}
        finally{sm.shutdown();worker.interrupt();worker.join(5000);check(!worker.isAlive(),"Sync fault cleanup did not exit");}
        emit("worker_failure sync same_call=plain-IOException next_call=CommShutdownException no-enqueue=true attempts=1");OfflineGuard.assertUntouched();emit("PASS worker failure policy; guarded_operations=0");
    }
    private static void terminalIoFaults()throws Exception {
        check(terminalIoPolicy()&&sessionContainment(),"Terminal IO policy missing");
        org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        IOException[] faults={new IOException("DO_NOT_RENDER_RESPONSE"),new IOException(""),new java.net.SocketTimeoutException("DO_NOT_RENDER_TIMEOUT"),new EOFException("DO_NOT_RENDER_EOF")};
        String[] labels={"response-loss","empty-message","timeout","eof"};
        for(int i=0;i<faults.length;i++){State state=new State();state.injectedFailure=faults[i];fixedFailure(state,labels[i],false,1);check(state.attempts==1&&state.closes==1,"Response fault replayed or cleanup differs");emit("terminal_io "+labels[i]+" attempts=1 response_entries=1 stopped=true queued_restart_blocked=true");}
        for(int count:new int[]{0,8}){State state=new State();state.writeFault=count;fixedFailure(state,"partial-write",false,0);check(state.attempts==1&&state.partialBytes==count&&state.closes==2,"Partial write replayed");emit("terminal_io write-after-"+count+" attempts=1 response_entries=0 stopped=true queued_restart_blocked=true");}
        State body=new State();body.bodyWriteFault=true;fixedFailure(body,"body-write",false,0);check(body.attempts==1&&body.bodyFaultReached&&body.closes==2,"Body failure replayed or missed");emit("terminal_io write-body-before-first-byte attempts=1 response_entries=0 stopped=true queued_restart_blocked=true");
        State prewrite=new State();prewrite.prewriteFailure=true;fixedFailure(prewrite,"prewrite-seam",false,0);check(prewrite.attempts==1&&prewrite.closes==2,"Prewrite failure replayed or cleanup differs");emit("terminal_io prewrite-seam attempts=1 response_entries=0 stopped=true queued_restart_blocked=true");
        State cleanup=new State();cleanup.nonpersistent=true;cleanup.closeFailures=1;fixedFailure(cleanup,"cleanup-after-reply",false,1);check(cleanup.attempts==1&&cleanup.closeFailures==0&&cleanup.closes==2,"Cleanup failure replayed");emit("terminal_io cleanup-after-reply attempts=1 response_entries=1 stopped=true queued_restart_blocked=true");
        State codecWrite=new State();codecWrite.legacyBodyCodec=true;codecWrite.bodyWriteFault=true;fixedFailure(codecWrite,"codec-body-write",false,0);check(codecWrite.attempts==1&&codecWrite.bodyFaultReached&&codecWrite.closes==2,"Codec close replayed body write");emit("terminal_io legacy-codec-body-write attempts=1 response_entries=0 stopped=true queued_restart_blocked=true");
        final State idle=new State();idle.failureAfter=2;idle.injectedFailure=new EOFException("DO_NOT_RENDER_IDLE");final CommunicationsManager m=ioManager(idle);final int[] callbacks={0};final Object[] contexts={new Object(),new Object(),new Object()};
        CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object seen){int i=callbacks[0]++;check(i<3&&response.getType()!=Response.TYPE_CONNECT&&seen==contexts[i]&&response.getResultCode()==(i==0?0:-102),"Idle sequence differs");check(m.isStopped()==(i>0),"Idle stop timing differs");if(i==1){Exception e=response.getException();check(e!=null&&e.getClass().getName().equals("compat.UntrustedResponseException")&&e.getCause()==null&&"Response transport failed; outcome is unconfirmed".equals(e.getMessage()),"Idle failure not sanitized");}if(i==2)m.shutdown();}};
        AcpxMessageFactory f=new AcpxMessageFactory();m.postMessageAsync(handler,f.newGetStatusRequest(),contexts[0]);m.postMessageAsync(handler,f.newSetTimeRequest(new Date(0)),contexts[1]);m.postMessageAsync(handler,f.newRestartSystemRequest(),contexts[2]);m.run();check(callbacks[0]==3&&idle.attempts==2&&idle.sent.size()==2&&idle.closes==1,"Idle sequence replayed");emit("terminal_io idle-close-after-success attempts=2 response_entries=2 stopped=true queued_restart_blocked=true");
        OfflineGuard.assertUntouched();emit("PASS terminal IO faults; guarded_operations=0");
    }
    private static void nullIoPolicy()throws Exception {
        check(nullIoFixed(),"Null IO policy missing");org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        fixedNull(new EOFException(),"eof",true);
        IOException cause=new IOException();cause.initCause(new IOException("DO_NOT_RENDER_NULL_IO_CAUSE"));fixedNull(cause,"cause",true);
        ChangingMessage firstNull=new ChangingMessage(true);fixedNull(firstNull,"changing-first-null",true);check(firstNull.calls==1,"Null getMessage evaluated twice");
        ChangingMessage firstText=new ChangingMessage(false);
        if(terminalIoPolicy()){fixedNull(firstText,"changing-first-text",false);check(firstText.calls==1,"Nonnull getMessage evaluated twice");emit("null_io changing-first-text terminal=-102; fixed-no-cause; getMessage_calls=1; sends=1");}
        else {
        State state=new State();state.injectedFailure=firstText;
        final CommunicationsManager m=ioManager(state);final int[] commands={0},connects={0};
        m.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){try{if(response.getType()==Response.TYPE_CONNECT){check(connects[0]++==0,"Unexpected repeated retry");set(m,"connection",transport(new MemoryConnection(state)));set(m,"connected",true);}else{check(response.getResultCode()==0,"Nonnull retry failed");commands[0]++;m.shutdown();}}catch(Exception e){throw new AssertionError("Retry injection failed");}}},new AcpxMessageFactory().newGetStatusRequest());
        m.run();check(firstText.calls==1&&commands[0]==1&&connects[0]==1&&state.sent.size()==2&&Arrays.equals(state.sent.get(0),state.sent.get(1)),"Nonnull IO delegation differs");
        emit("null_io changing-first-text ordinary-retry; getMessage_calls=1; sends=2");
        }
        State sync=new State();sync.injectedFailure=new EOFException();final CommunicationsManager sm=ioManager(sync);final Throwable[] escaped={null};Thread worker=new Thread(new Runnable(){public void run(){sm.run();}},"null-sync-fixture");worker.setDaemon(true);worker.setUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler(){public void uncaughtException(Thread t,Throwable e){escaped[0]=e;}});
        try{worker.start();try{sm.postMessage(new AcpxMessageFactory().newGetStatusRequest());throw new AssertionError("Null sync accepted");}catch(IOException e){check("Response transport failed; outcome is unconfirmed".equals(e.getMessage())&&e.getCause()==null,"Null sync message differs");}check(sync.sent.size()==1&&!sm.isConnected(),"Null sync state differs");}
        finally{sm.shutdown();worker.interrupt();worker.join(2000);check(!worker.isAlive()&&escaped[0]==null,"Null sync cleanup differs");}
        emit("null_io sync fixed-IOException; no-peer-or-cause; sends=1");OfflineGuard.assertUntouched();emit("PASS null IO policy; guarded_operations=0");
    }
    private static void shallowProperty()throws Exception {
        final State state=new State();final CommunicationsManager m=ioManager(state);final int[] callbacks={0};final Object context=new Object();
        RequestMessage request=new AcpxMessageFactory().newGetStatusRequest();request.setRequestProperty("X-Fixture","before");
        m.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object seen){check(seen==context&&response.getType()==Response.TYPE_COMMAND&&response.getResultCode()==0,"Shallow fixture response differs");callbacks[0]++;m.shutdown();}},request,context);
        request.setRequestProperty("X-Fixture","after");m.run();
        check(callbacks[0]==1 && state.sent.size()==1,"Shallow fixture send count differs");
        String wire=new String(state.sent.get(0),"UTF-8");
        check(wire.contains("X-Fixture: after\r\n")&&!wire.contains("X-Fixture: before\r\n"),"Queued property not shared");
        emit("io shallow-clone property-changed-after-post; wire=after; sends=1; callbacks=1");
    }
    private static void synchronousInvalidHeader(byte[] invalid)throws Exception {
        State state=new State();state.rawResponse=invalid;
        final CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);
        set(manager,"queue",new LinkedList<Object>());set(manager,"system",unsafe().allocateInstance(FakeSystem.class));
        set(manager,"connection",transport(new MemoryConnection(state)));set(manager,"connected",true);
        final Throwable[] escaped={null};Thread worker=new Thread(new Runnable(){public void run(){manager.run();}},"fixture-sync-worker");
        worker.setDaemon(true);worker.setUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler(){public void uncaughtException(Thread t,Throwable e){escaped[0]=e;}});
        worker.start();
        try {
            try{manager.postMessage(new AcpxMessageFactory().newGetStatusRequest());throw new AssertionError("Sync malformed header accepted");}
            catch(IOException failed){check("Response header is invalid".equals(failed.getMessage())&&failed.getCause()==null,"Sync fixed message differs");}
            check(state.sent.size()==1&&!manager.isConnected(),"Sync rejection state differs");
        } finally {manager.shutdown();worker.interrupt();worker.join(2000);check(!worker.isAlive()&&escaped[0]==null,"Sync worker cleanup differs");}
        emit("io sync invalid-header fixed-IOException; no-peer-or-cause; sends=1");
    }
    private static void ioCharacterization()throws Exception {
        org.apache.log4j.Logger.getRootLogger().setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        AcpxMessageFactory factory=new AcpxMessageFactory();
        byte[] invalid=reply("HTTP/1.1 200 Fixture","DO_NOT_RENDER_PROTOCOL_HEADER\r\n",XML);
        State direct=new State();direct.rawResponse=invalid;
        boolean fixed=invalidHeaderPolicy();AcpxConnection directAcp=transport(new MemoryConnection(direct));
        try{directAcp.send(factory.newGetStatusRequest());throw new AssertionError("Bad header accepted");}
        catch(java.net.ProtocolException failed){check(!fixed&&failed.getMessage()!=null&&failed.getMessage().contains("DO_NOT_RENDER_PROTOCOL_HEADER"),"Peer line not retained");}
        catch(IllegalArgumentException failed){check(fixed&&failed.getClass().getName().equals("compat.UntrustedResponseException")&&"Response header is invalid".equals(failed.getMessage())&&failed.getCause()==null&&directAcp.connection==null,"Invalid header rejection differs");}
        check(direct.sent.size()==1,"Direct bad-header sends differ");
        emit("io invalid-header message_has_peer_line="+(!fixed)+"; direct_sends=1");
        dispatch(factory.newGetStatusRequest(),0,false,invalid,fixed?-102:0,fixed?0:1,fixed?"invalid-header-read-terminal":"invalid-header-read-retry");
        dispatch(factory.newSetTimeRequest(new Date(0)),0,false,invalid,fixed?-102:0,fixed?0:1,fixed?"invalid-header-mutation-terminal":"invalid-header-mutation-retry");
        RequestMessage restart=factory.newRestartSystemRequest();
        check(restart.getShutdownConnection() && restart.getRestartConnection()==-1,"Unexpected restart fixture flags");
        dispatch(restart,1,false);emit("io synthetic-restart lost-response; "+(terminalIoPolicy()?"no-replay":"same-command-replayed")+"; shutdown_flag=true; memory-only");
        nullMessage();shallowProperty();if(fixed)synchronousInvalidHeader(invalid);OfflineGuard.assertUntouched();
        emit("PASS IO characterization; guarded_operations=0");
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
    private static RequestMessage countedRequest(final RequestMessage delegate,final int[] clones){
        return (RequestMessage)java.lang.reflect.Proxy.newProxyInstance(RequestMessage.class.getClassLoader(),new Class[]{RequestMessage.class},new java.lang.reflect.InvocationHandler(){
            public Object invoke(Object proxy,java.lang.reflect.Method method,Object[] args)throws Throwable{
                if(method.getName().equals("clone")){clones[0]++;return proxy;}
                try{return method.invoke(delegate,args);}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}
            }
        });
    }
    public static final class ImmediateManager extends CommunicationsManager {
        Response supplied;
        private ImmediateManager(){super(null);throw new AssertionError("Constructor must not run");}
        @Override public void postMessageAsync(CommunicationHandler handler,RequestMessage request){handler.handleResponse(null,supplied,null);}
    }
    private static void syncPreenqueue(final boolean fixed)throws Exception {
        org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        final State state=new State();final CommunicationsManager m=ioManager(state);set(m,"thread",Thread.currentThread());state.stopOnSecondResponse=m;final int[] callbacks={0};final int[] clones={0};final AcpxMessageFactory f=new AcpxMessageFactory();
        final RequestMessage forbidden=countedRequest(f.newRestartSystemRequest(),clones);
        m.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem system,Response response,Object context){
            check(response.getResultCode()==0&&!m.isStopped(),"Callback prerequisite differs");callbacks[0]++;
            int before=((LinkedList)uncheckedQueue(m)).size();
            try{m.postMessage(forbidden);throw new AssertionError("Synchronous callback accepted");}
            catch(IllegalStateException expected){check(expected.getClass()==IllegalStateException.class&&"Attempt to post message synchronously from handler callback".equals(expected.getMessage())&&expected.getCause()==null,"Callback exception changed");}
            catch(IOException e){throw new AssertionError("Unexpected callback IO");}
            int added=((LinkedList)uncheckedQueue(m)).size()-before;unsafeSyncEnqueueObserved=added!=0;
            check(added==(fixed?0:1)&&clones[0]==(fixed?1:2),"Forbidden callback command enqueued");
            m.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem sy,Response r,Object c){check(r.getResultCode()==(fixed?0:-102),"Follow-up failed");callbacks[0]++;m.shutdown();}},f.newGetTimeRequest());
        }},f.newGetStatusRequest());
        m.run();check(callbacks[0]==2&&state.attempts==2&&state.sent.size()==state.attempts,"Callback sequence differs");
        check(Arrays.equals(requestBody(state.sent.get(1)),serialized(fixed?f.newGetTimeRequest():f.newRestartSystemRequest())),"Second operation bytes differ");
        emit("sync callback fixed_exception=true second_clone="+(!fixed)+" queued="+(fixed?0:1)+" request_attempts="+state.attempts+" forbidden_restart="+(fixed?"blocked":"sent"));
        final State normal=new State();final CommunicationsManager nm=ioManager(normal);final Response[] returned={null};final Throwable[] errors={null};final int[] normalClones={0};
        Thread worker=new Thread(new Runnable(){public void run(){try{nm.run();}catch(Throwable e){errors[0]=e;}}},"fixture-normal-sync-worker");worker.setDaemon(true);set(nm,"thread",worker);
        Thread caller=new Thread(new Runnable(){public void run(){try{returned[0]=nm.postMessage(countedRequest(f.newGetStatusRequest(),normalClones));}catch(Throwable e){errors[0]=e;}}},"fixture-normal-sync-caller");caller.setDaemon(true);
        caller.start();long end=System.nanoTime()+5000000000L;Object handler=null;
        while(handler==null&&System.nanoTime()<end){LinkedList q=(LinkedList)queueValue(nm);synchronized(q){if(q.size()==1){Object transaction=q.getFirst();Field hf=transaction.getClass().getDeclaredField("handler");hf.setAccessible(true);handler=hf.get(transaction);}}if(handler==null)Thread.sleep(5);}
        while(caller.getState()!=Thread.State.WAITING&&caller.isAlive()&&System.nanoTime()<end)Thread.sleep(5);
        try{check(handler!=null&&caller.getState()==Thread.State.WAITING,"Normal synchronous wait not established");worker.start();caller.join(5000);check(!caller.isAlive()&&errors[0]==null&&returned[0]!=null&&returned[0].getResultCode()==0,"Normal synchronous call failed");Field rf=handler.getClass().getDeclaredField("response");rf.setAccessible(true);check(rf.get(handler)==returned[0]&&normalClones[0]==2&&normal.attempts==1,"Normal response identity or clone count changed");}
        finally{nm.shutdown();worker.interrupt();caller.interrupt();worker.join(2000);caller.join(2000);check(!worker.isAlive()&&!caller.isAlive(),"Normal sync cleanup failed");}
        emit("sync normal clones=2 attempts=1 waited=true response_identity=true");
        ImmediateManager immediate=(ImmediateManager)unsafe().allocateInstance(ImmediateManager.class);immediate.supplied=new BasicResponse(Response.TYPE_COMMAND,null,0,null);Response fast=immediate.postMessage(f.newGetStatusRequest());check(fast==immediate.supplied,"Immediate response identity changed");emit("sync immediate-before-wait response_identity=true");
        final CommunicationsManager stopped=ioManager(new State());stopped.shutdown();int[] stoppedClones={0};try{stopped.postMessage(countedRequest(f.newRestartSystemRequest(),stoppedClones));throw new AssertionError("Stopped sync accepted");}catch(CommShutdownException expected){}check(stoppedClones[0]==0&&((LinkedList)queueValue(stopped)).isEmpty(),"Stopped sync enqueued");stopped.run();emit("sync stopped before_clone=true queue=0");
        final CommunicationsManager interrupted=ioManager(new State());Thread.currentThread().interrupt();try{interrupted.postMessage(f.newRestartSystemRequest());throw new AssertionError("Interrupted sync accepted");}catch(IOException expected){check(expected.getClass()==IOException.class&&"communications shutdown".equals(expected.getMessage()),"Interrupted result changed");}finally{Thread.interrupted();}check(!interrupted.isStopped()&&((LinkedList)queueValue(interrupted)).size()==1,"Interrupted residual changed");interrupted.shutdown();interrupted.run();emit("sync interrupted residual_queue=1 stopped=false cancellation=unfixed");
        OfflineGuard.assertUntouched();emit("PASS sync preenqueue observations; guarded_operations=0");
    }
    private static Object uncheckedQueue(CommunicationsManager m){try{return queueValue(m);}catch(Exception e){throw new AssertionError("Queue unavailable");}}
    private static byte[] requestBody(byte[] wire){for(int i=0;i+3<wire.length;i++)if(wire[i]==13&&wire[i+1]==10&&wire[i+2]==13&&wire[i+3]==10)return Arrays.copyOfRange(wire,i+4,wire.length);throw new AssertionError("Request body missing");}
    private static byte[] serialized(RequestMessage request)throws Exception{ByteArrayOutputStream out=new ByteArrayOutputStream();request.writeTo(out);return out.toByteArray();}

}
