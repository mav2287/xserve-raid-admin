package com.apple.xsr.net;

import java.io.*;
import java.net.*;
import java.security.*;
import java.util.*;

/** Serializes read requests and replays synthetic HTTP in memory; no sockets allowed. */
public final class OfflineParity {
    private static final class MemoryConnection extends HttpConnection {
        final ByteArrayOutputStream sent = new ByteArrayOutputStream();
        InputStream reply;
        MemoryConnection() throws IOException { super("127.0.0.1"); setPersistent(true); }
        @Override OutputStream getOutputStream() { return sent; }
        @Override InputStream getInputStream() { return reply; }
        @Override public void connect() { throw new AssertionError("Network prohibited"); }
        @Override public void disconnect() { }
        @Override public void setTimeout(int timeout) { }
    }
    private static String digest(byte[] data) throws Exception {
        byte[] hash = MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder s = new StringBuilder();
        for (byte b : hash) s.append(String.format("%02x", b & 255));
        return s.toString();
    }
    public static void main(String[] args) throws Exception {
        System.setSecurityManager(new SecurityManager() {
            @Override public void checkPermission(Permission permission) {
                if (permission instanceof RuntimePermission &&
                    (permission.getName().equals("setSecurityManager") || permission.getName().equals("preferences")))
                    throw new SecurityException("Profile access and guard replacement prohibited");
            }
            @Override public void checkRead(String path) {
                String normalized = new File(path).getAbsolutePath();
                if (normalized.contains("/Library/Preferences/") || normalized.endsWith("/Library/Preferences"))
                    throw new SecurityException("Preference reads prohibited");
            }
            @Override public void checkWrite(String path) { throw new SecurityException("Writes prohibited"); }
            @Override public void checkDelete(String path) { throw new SecurityException("Deletes prohibited"); }
            @Override public void checkExec(String command) { throw new SecurityException("Subprocesses prohibited"); }
            @Override public void checkConnect(String host, int port) { throw new SecurityException("Network prohibited"); }
            @Override public void checkListen(int port) { throw new SecurityException("Network prohibited"); }
            @Override public void checkMulticast(InetAddress address) { throw new SecurityException("Network prohibited"); }
        });
        AcpxMessageFactory factory = new AcpxMessageFactory();
        RequestMessage[] requests = {
            factory.newNoOpRequest(), factory.newGetStatusRequest(), factory.newGetTimeRequest(),
            factory.newGetControllerPageRequest(Integer.valueOf(1)),
            factory.newGetEventLogRequest(new Date(0)), factory.newGetPowerStateRequest(),
            factory.newGetPostResultsRequest(), factory.newGetTemperatureRequest("emu"),
            factory.newGetDevicePropertiesRequest("emu", Integer.valueOf(0)),
            factory.newGetPropertyRequest("syNm")
        };
        for (int i = 0; i < requests.length; i++) {
            RequestMessage r = requests[i];
            MemoryConnection memory = new MemoryConnection();
            HttpRequest http = new HttpRequest(memory, new URL("http://127.0.0.1" + r.getPath()));
            OutputStream output = http.getOutputStream();
            r.writeTo(output);
            output.close();
            byte[] request = memory.sent.toByteArray();
            if (request.length == 0 || !new String(request, "UTF-8").startsWith("POST " + r.getPath() + " HTTP/1.1"))
                throw new AssertionError("Request serialization failure");
            memory.reply = new ByteArrayInputStream("HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK".getBytes("US-ASCII"));
            if (!Arrays.equals(new HttpResponse(memory).getBody(), new byte[]{'O', 'K'}))
                throw new AssertionError("Replay response failure");
            System.out.println(i + " " + digest(request));
        }
        // Verify the fixture cannot open a connection, even if transport code regresses.
        try { new Socket("127.0.0.1", 1); throw new AssertionError("Socket guard failed"); }
        catch (SecurityException expected) { }
        SecurityManager guard = System.getSecurityManager();
        try { guard.checkWrite("fixture"); throw new AssertionError("Write guard failed"); }
        catch (SecurityException expected) { }
        try { guard.checkRead("/synthetic/Library/Preferences/fixture.plist"); throw new AssertionError("Read guard failed"); }
        catch (SecurityException expected) { }
        try { guard.checkExec("fixture"); throw new AssertionError("Exec guard failed"); }
        catch (SecurityException expected) { }
        try { guard.checkPermission(new RuntimePermission("preferences")); throw new AssertionError("Preferences guard failed"); }
        catch (SecurityException expected) { }
        try { System.setSecurityManager(null); throw new AssertionError("Replacement guard failed"); }
        catch (SecurityException expected) { }
        System.out.println("PASS 10 request serializers, 10 HTTP replay responses, socket guard");
    }
}
