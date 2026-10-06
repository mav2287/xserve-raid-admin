package com.apple.xsr.net;

import com.apple.util.plist.PropertyList;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.Field;
import java.net.SocketTimeoutException;
import java.util.Map;
import java.util.Arrays;
import sun.misc.Unsafe;

/** Bounded persistent-stream association fixture. No sockets, UI or controller. */
public final class SharedResponseObservation {
    private static void check(boolean value) { if (!value) throw new AssertionError("Shared stream assertion failed"); }
    private static byte[] bytes(String text) throws Exception { return text.getBytes("UTF-8"); }
    private static byte[] xml(String role) throws Exception {
        return bytes("<plist><dict><key>fixture</key><string>"+role+"</string></dict></plist>");
    }
    private static byte[] reply(String headers, byte[] body) throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        out.write(bytes("HTTP/1.1 200 Fixture\r\n"+headers+"\r\n"));out.write(body);
        check(out.size()<=8192);return out.toByteArray();
    }
    private static byte[] reply(String role) throws Exception {
        byte[] body=xml(role);return reply("Content-Length: "+body.length+"\r\n",body);
    }
    private static final class Source extends InputStream {
        private byte[] data=new byte[0];private int position;
        int reads,closes;boolean closed;
        int remaining() { return data.length-position; }
        void append(byte[] next) {
            check(!closed && remaining()+next.length<=16384);
            byte[] joined=new byte[remaining()+next.length];
            System.arraycopy(data,position,joined,0,remaining());
            System.arraycopy(next,0,joined,remaining(),next.length);data=joined;position=0;
        }
        @Override public int read() throws IOException {
            check(++reads<=16384);
            if(closed)throw new IOException("Closed synthetic stream");
            if(remaining()==0)throw new SocketTimeoutException("Idle synthetic stream");
            return data[position++]&255;
        }
        @Override public int available() throws IOException { if(closed)throw new IOException("Closed synthetic stream");return remaining(); }
        @Override public void close() { closes++;closed=true; }
    }
    private static final class Memory extends HttpConnection {
        final Source source=new Source();final byte[][] replies;
        final int expectedBeforeSecond;int outputs,inputs,disconnects;ByteArrayOutputStream pending;byte[] firstRequest;
        Memory(byte[] first,byte[] second,int expected) throws IOException {
            super("127.0.0.1");setPersistent(true);replies=new byte[][]{first,second};expectedBeforeSecond=expected;
        }
        @Override OutputStream getOutputStream() throws IOException {
            check(!source.closed && pending==null && outputs==inputs && outputs<2);
            outputs++;pending=new ByteArrayOutputStream();return pending;
        }
        @Override InputStream getInputStream() throws IOException {
            check(!source.closed && pending!=null && outputs==inputs+1 && pending.size()>0 && pending.size()<=8192);
            check(source.remaining()==(inputs==0?0:expectedBeforeSecond));
            byte[] request=pending.toByteArray();
            if(inputs==0)firstRequest=request;else check(!Arrays.equals(firstRequest,request));
            pending=null;source.append(replies[inputs++]);return source;
        }
        @Override public void connect() { throw new AssertionError("Connect forbidden"); }
        @Override public void disconnect() { disconnects++;source.close(); }
        @Override public void setTimeout(int timeout) { }
    }
    private static AcpxConnection acp(Memory memory) throws Exception {
        Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);
        AcpxConnection value=(AcpxConnection)((Unsafe)f.get(null)).allocateInstance(AcpxConnection.class);
        value.host="127.0.0.1";value.persistent=true;value.connection=memory;return value;
    }
    private static String role(PropertyList plist) {
        if(plist==null)return "empty";
        Object root=plist.getRootElement();check(root instanceof Map);
        Object result=((Map)root).get("fixture");
        check("first".equals(result)||"second".equals(result)||"prior-body".equals(result));return (String)result;
    }
    private static void observe(PrintStream out,String label,byte[] first,int residual,boolean canonical,boolean chunked) throws Exception {
        byte[] legitimate=reply("second");Memory memory=new Memory(first,legitimate,residual);
        AcpxConnection transport=acp(memory);AcpxMessageFactory factory=new AcpxMessageFactory();
        try {
            String firstRole=role(transport.send(factory.newGetStatusRequest()));
            check(firstRole.equals(canonical?"first":"empty"));
            check(transport.connection==memory && memory.source.remaining()==residual);
            check(memory.source.closes==0 && memory.disconnects==0 && memory.inputs==1 && memory.outputs==1);
            String secondRole;
            try { secondRole=role(transport.send(factory.newGetTimeRequest()));check(!chunked); }
            catch(java.net.ProtocolException expected) { check(chunked);secondRole="protocol-error"; }
            check(secondRole.equals(chunked?"protocol-error":canonical?"second":"prior-body"));
            check(memory.source.remaining()==(chunked?legitimate.length+5:canonical?0:legitimate.length));
            if(chunked) {
                Field outstanding=HttpConnection.class.getDeclaredField("requestOutstanding");outstanding.setAccessible(true);
                check(outstanding.getBoolean(memory));
                try{transport.send(factory.newGetStatusRequest());throw new AssertionError();}
                catch(IllegalStateException expected){}
                check(outstanding.getBoolean(memory));
            }
            check(memory.inputs==2 && memory.outputs==2 && memory.disconnects==0 && memory.source.closes==0);
            out.println("shared "+label+" first="+firstRole+" second="+secondRole+" pending_before_second="+residual+" pending_after_second="+memory.source.remaining()+" reads="+memory.source.reads+" sends=2 closes=0"+(chunked?" follow_on=blocked":""));
        } finally { memory.disconnect();check(memory.source.closed && memory.source.closes==1 && memory.disconnects==1); }
    }
    private static void sourceControls(PrintStream out) throws Exception {
        Source source=new Source();source.append(new byte[]{1});check(source.read()==1);
        try{source.read();throw new AssertionError();}catch(SocketTimeoutException expected){}
        source.close();try{source.read();throw new AssertionError();}catch(SocketTimeoutException wrong){throw new AssertionError();}catch(IOException expected){}
        check(source.closes==1);out.println("shared source-controls idle-timeout; terminal-close PASS");
    }
    private static void rejected(PrintStream out,String label,String headers,String message) throws Exception {
        byte[] prior=reply("prior-body");Memory memory=new Memory(reply(headers,prior),reply("second"),0);
        AcpxConnection transport=acp(memory);
        try {
            try{transport.send(new AcpxMessageFactory().newGetStatusRequest());throw new AssertionError();}
            catch(IllegalArgumentException failed){check(failed.getClass().getName().equals("compat.UntrustedResponseException")&&message.equals(failed.getMessage())&&failed.getCause()==null);}
            check(transport.connection==null && memory.source.closed && memory.source.closes==1 && memory.disconnects==1 && memory.inputs==1 && memory.outputs==1);
            out.println("framing "+label+" fixed-marker; retired; sends=1; no-cause");
        } finally { if(!memory.source.closed)memory.disconnect(); }
    }
    private static void accepted(PrintStream out,String label,String headers,byte[] body,String expected) throws Exception {
        Memory memory=new Memory(reply(headers,body),reply("second"),0);AcpxConnection transport=acp(memory);
        try {
            AcpxMessageFactory f=new AcpxMessageFactory();check(role(transport.send(f.newGetStatusRequest())).equals(expected));
            check(memory.source.remaining()==0 && memory.source.closes==0 && transport.connection==memory);
            check(role(transport.send(f.newGetTimeRequest())).equals("second"));
            check(memory.source.remaining()==0 && memory.source.closes==0 && memory.disconnects==0 && memory.outputs==2 && memory.inputs==2);
            out.println("framing "+label+" first="+expected+" second=second; sends=2; pending=0; closes=0");
        } finally {memory.disconnect();check(memory.source.closes==1);}
    }
    private static void closeResponse(PrintStream out) throws Exception {
        byte[] body=xml("first");Memory memory=new Memory(reply("Content-Length: "+body.length+"\r\nConnection: close\r\n",body),reply("second"),0);
        AcpxConnection transport=acp(memory);
        try {
            check(role(transport.send(new AcpxMessageFactory().newGetStatusRequest())).equals("first"));
            check(memory.inputs==1 && memory.outputs==1 && memory.source.remaining()==0 && memory.source.closed && memory.source.closes==1 && memory.disconnects==0);
            Field f=HttpConnection.class.getDeclaredField("requestOutstanding");f.setAccessible(true);check(!f.getBoolean(memory));
            out.println("framing connection-close original-source-close; sends=1; pending=0; closes=1");
        } finally {if(!memory.source.closed)memory.disconnect();}
    }
    private static void policy(PrintStream out) throws Exception {
        Class.forName("compat.ResponseFraming");byte[] body=xml("first");
        accepted(out,"canonical","Content-Length: "+body.length+"\r\n",body,"first");
        accepted(out,"lowercase","content-length: "+body.length+"\r\n",body,"first");
        accepted(out,"zero","Content-Length: 0\r\n",new byte[0],"empty");
        rejected(out,"missing","","Response length is missing");
        rejected(out,"duplicate-identical","Content-Length: 0\r\nContent-Length: 0\r\n","Response length is ambiguous");
        rejected(out,"duplicate-mixed-case","Content-Length: 0\r\ncOnTeNt-LeNgTh: 0\r\n","Response length is ambiguous");
        rejected(out,"duplicate-last-zero","Content-Length: "+reply("prior-body").length+"\r\nContent-Length: 0\r\n","Response length is ambiguous");
        rejected(out,"transfer-encoding","Transfer-Encoding: chunked\r\n","Response transfer encoding is unsupported");
        java.util.Locale previous=java.util.Locale.getDefault();
        try{java.util.Locale.setDefault(new java.util.Locale("tr","TR"));
            accepted(out,"uppercase-turkish","CONTENT-LENGTH: "+body.length+"\r\n",body,"first");
            rejected(out,"transfer-encoding-turkish","Content-Length: 0\r\nTRANSFER-ENCODING: identity\r\n","Response transfer encoding is unsupported");
        }finally{java.util.Locale.setDefault(previous);}
        closeResponse(out);byte[] forged=reply("prior-body");
        observe(out,"declared-zero",reply("Content-Length: 0\r\n",forged),forged.length,false,false);
    }
    public static void main(String[] args) throws Exception {
        check(args.length==0 || (args.length==1 && args[0].equals("framing-policy")));OfflineGuard.install();
        PrintStream out=System.out,err=System.err;ByteArrayOutputStream suppressed=new ByteArrayOutputStream();
        try {
            System.setOut(new PrintStream(suppressed));System.setErr(new PrintStream(suppressed));
            org.apache.log4j.Logger.getRootLogger().setLevel(org.apache.log4j.Level.OFF);
            sourceControls(out);
            if(args.length==1)policy(out);
            else {
            byte[] forged=reply("prior-body");
            observe(out,"canonical",reply("first"),0,true,false);
            observe(out,"missing-length",reply("",forged),forged.length,false,false);
            observe(out,"lowercase-length",reply("content-length: "+forged.length+"\r\n",forged),forged.length,false,false);
            observe(out,"duplicate-last-zero",reply("Content-Length: "+forged.length+"\r\nContent-Length: 0\r\n",forged),forged.length,false,false);
            observe(out,"declared-zero",reply("Content-Length: 0\r\n",forged),forged.length,false,false);
            byte[] chunks=bytes("3\r\nabc\r\n0\r\n\r\n");
            observe(out,"chunked",reply("Transfer-Encoding: chunked\r\n",chunks),chunks.length,false,true);
            }
            check(suppressed.size()==0);OfflineGuard.assertUntouched();
            out.println(args.length==0?"PASS shared-stream association; guarded_operations=0":"PASS framing policy; guarded_operations=0");
        } finally { System.setOut(out);System.setErr(err); }
    }
}
