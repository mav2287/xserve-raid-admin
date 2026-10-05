package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;

/** Real ACP/queue code, in-memory HTTP transport; no actual connect or controller. */
public final class TransportObservation {
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
        int drops;
        boolean malformed;
    }
    private static final class MemoryConnection extends HttpConnection {
        ByteArrayOutputStream pending;
        final State state;
        MemoryConnection(State state) throws IOException { super("127.0.0.1"); setPersistent(true); this.state = state; }
        @Override OutputStream getOutputStream() {
            pending = new ByteArrayOutputStream(); return pending;
        }
        @Override InputStream getInputStream() throws IOException {
            if (pending == null) throw new AssertionError("Response before request");
            state.sent.add(pending.toByteArray()); pending = null;
            if (state.drops-- > 0) throw new IOException("synthetic response loss");
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
    private static void dispatch(final RequestMessage request, int drops, boolean malformed) throws Exception {
        final State state = new State(); state.drops = drops; state.malformed = malformed;
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
                        check(response.getResultCode() == (state.malformed ? -103 : 0), "Unexpected terminal result");
                        callbacks[1]++; manager.shutdown();
                    }
                } catch (Exception e) { throw new AssertionError("Fixture injection failed"); }
            }
        }, request, context);
        manager.run();
        check(callbacks[1] == 1, "Terminal callback not exactly once");
        check(callbacks[0] == drops, "Unexpected retry count");
        check(state.sent.size() == drops + 1, "Unexpected send count");
        for (byte[] sent : state.sent) check(Arrays.equals(sent, state.sent.get(0)), "Retry wire differs");
        System.out.println("dispatch drops=" + drops + " malformed=" + malformed + " sends=" + state.sent.size() + " terminal_callbacks=" + callbacks[1]);
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
        System.out.println("synthetic firmware stream throws_after_close=" + throwsAfterClose + " memory_sends=" + state.sent.size());
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        org.apache.log4j.Logger.getRootLogger().setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.CommunicationsManager").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.AcpxConnection").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.HttpConnection").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.HttpRequest").setLevel(org.apache.log4j.Level.OFF);
        org.apache.log4j.Logger.getLogger("com.apple.xsr.net.HttpResponse").setLevel(org.apache.log4j.Level.OFF);
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
        System.out.println("ACP synthetic authentication/target/user-agent and plist parsing PASS; fixture prints no header values; application logging OFF");
        dispatch(factory.newGetStatusRequest(), 1, false);
        dispatch(factory.newSetTimeRequest(new Date(0)), 1, false);
        dispatch(factory.newSetTimeRequest(new Date(0)), 4, false);
        dispatch(factory.newGetStatusRequest(), 0, true);
        firmwareStream(false);
        firmwareStream(true);
        OfflineGuard.assertUntouched();
        System.out.println("PASS memory-only transport and queue observations; real reconnection/backoff excluded");
    }
}
