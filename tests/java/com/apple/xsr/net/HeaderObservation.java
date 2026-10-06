package com.apple.xsr.net;
import fixture.OfflineGuard;
import java.io.*;
import java.util.*;
import java.security.MessageDigest;

/** Original constructors and body reads; bounded, synthetic, memory-only input. */
public final class HeaderObservation {
    private static void check(boolean ok) {if(!ok)throw new AssertionError("Header fixture failed");}
    private static final class Source extends ByteArrayInputStream {
        int reads;boolean closed;
        Source(byte[] bytes){super(bytes);}
        @Override public synchronized int read(){reads++;return super.read();}
        @Override public void close(){closed=true;}
        int consumed(){return pos;}
    }
    private static final class Memory extends HttpConnection {
        final Source source;
        Memory(Source source)throws IOException{super("127.0.0.1");setPersistent(true);this.source=source;}
        @Override InputStream getInputStream(){return source;}
        @Override public void connect(){throw new AssertionError("Connection prohibited");}
        @Override public void disconnect(){}
    }
    private static String hash(byte[] data)throws Exception{return hex(MessageDigest.getInstance("SHA-256").digest(data));}
    private static String hex(byte[] data){
        StringBuilder b=new StringBuilder();for(byte v:data)b.append(String.format("%02x",v&255));return b.toString();
    }
    private static String repeat(String s,int n){StringBuilder b=new StringBuilder();for(int i=0;i<n;i++)b.append(s);return b.toString();}
    private static byte[] bytes(String s)throws Exception{return s.getBytes("US-ASCII");}
    private static boolean fixed,invalidHeaderFixed;
    private static java.lang.reflect.Method wrap,parse,line;
    private static java.lang.reflect.Field input,phase,budget,lineCount,characters,newline;
    private static sun.misc.Unsafe unsafe;
    private static HttpResponse shell(InputStream stream)throws Exception {
        HttpResponse response=(HttpResponse)unsafe.allocateInstance(HttpResponse.class);
        response.headers=new HashMap();input.set(response,stream);return response;
    }
    private static String failureOutcome(Throwable failed) {
        if(failed.getClass().getName().equals("compat.UntrustedResponseException")) {
            check("Response header is invalid".equals(failed.getMessage())&&failed.getCause()==null);
            return "java.net.ProtocolException"; // deliberate type change; preserve parse/consumption oracle
        }
        check(failed instanceof IOException && !(invalidHeaderFixed && failed instanceof java.net.ProtocolException));return failed.getClass().getName();
    }
    private static void tracking(byte[] raw,String outcome,int consumed)throws Exception {
        Source source=new Source(raw);InputStream bounded=(InputStream)wrap.invoke(null,source);
        HttpResponse response=shell(bounded);String actual;
        try{parse.invoke(response);actual="accepted:"+new TreeMap(response.headers).toString();}
        catch(java.lang.reflect.InvocationTargetException failure){actual=failureOutcome(failure.getCause());}
        check(actual.equals(outcome)&&source.consumed()==consumed&&budget.getInt(bounded)==consumed&&phase.getBoolean(bounded)==outcome.startsWith("accepted:"));
        Source legacy=new Source(raw);HttpResponse oracle=shell(legacy);int calls=1;
        String status=(String)line.invoke(oracle);
        if(!status.equals(""))while(true){calls++;String value=(String)line.invoke(oracle);if(value.equals("")||value.indexOf(':')<=0)break;}
        check(legacy.consumed()==consumed&&lineCount.getInt(bounded)==calls&&characters.getInt(bounded)==0&&!newline.getBoolean(bounded));
    }
    private static String observation(byte[] raw)throws Exception{
        Source source=new Source(raw);String result;
        try {HttpResponse response=new HttpResponse(new Memory(source));result="accepted:"+new TreeMap(response.headers).toString();}
        catch(IOException failure){result=failureOutcome(failure);}
        catch(IllegalArgumentException failure){result=failureOutcome(failure);}
        if(fixed)tracking(raw,result,source.consumed());
        return result+":"+source.consumed();
    }
    private static void accepted(PrintStream out,String label,byte[] raw,byte[] expected)throws Exception{
        Source source=new Source(raw);HttpResponse response=new HttpResponse(new Memory(source));byte[] body=response.getBody();
        check(Arrays.equals(body,expected)&&source.consumed()==raw.length);
        out.println("accepted "+label+" body_sha256="+hash(body)+" headers_sha256="+hash(new TreeMap(response.headers).toString().getBytes("UTF-8"))+" consumed="+source.consumed());
    }
    static String totalHeader(int target)throws Exception{
        StringBuilder b=new StringBuilder("HTTP/1.1 200 X\r\nContent-Length: 0\r\n");
        for(int i=0;i<15;i++){String key="X"+i+": ";b.append(key).append(repeat("x",65536-key.length())).append("\r\n");}
        int remaining=target-b.length()-2;
        check(remaining>5&&remaining<65538);b.append("Y: ").append(repeat("x",remaining-5)).append("\r\n\r\n");
        check(b.length()==target);return b.toString();
    }
    private static void rejected(PrintStream out,String label,byte[] raw,int expectedConsumed)throws Exception{
        Source source=new Source(raw);
        try{new HttpResponse(new Memory(source));throw new AssertionError("Header limit not enforced");}
        catch(IllegalArgumentException expected){check("Response headers exceed limit".equals(expected.getMessage()));}
        Source second=new Source(raw);
        InputStream wrapper=(InputStream)Class.forName("compat.BoundedHeaderStream").getMethod("wrap",InputStream.class).invoke(null,second);
        try{while(wrapper.read()!=-1){}throw new AssertionError("Wrapper did not reject");}
        catch(IllegalArgumentException expected){check("Response headers exceed limit".equals(expected.getMessage()));}
        check(source.consumed()==expectedConsumed&&source.reads==expectedConsumed&&second.consumed()==expectedConsumed&&second.reads==expectedConsumed);int reads=second.reads;
        try{wrapper.read();throw new AssertionError("Rejection not sticky");}catch(IllegalArgumentException expected){}
        check(second.reads==reads);wrapper.close();check(second.closed);
        out.println("rejection "+label+" consumed="+source.consumed()+" sticky=true");
    }
    public static void main(String[] args)throws Exception{
        OfflineGuard.install();check(args.length==1&&(args[0].equals("true")||args[0].equals("false")));
        fixed=Boolean.parseBoolean(args[0]);PrintStream out=System.out,err=System.err;
        if(fixed){
            try{Class.forName("compat.ResponseFraming").getMethod("invalidHeader");invalidHeaderFixed=true;}catch(ClassNotFoundException absent){}catch(NoSuchMethodException absent){}
            Class<?> helper=Class.forName("compat.BoundedHeaderStream");wrap=helper.getMethod("wrap",InputStream.class);
            input=HttpResponse.class.getDeclaredField("inStream");input.setAccessible(true);
            parse=HttpResponse.class.getDeclaredMethod("parseHeaders");parse.setAccessible(true);
            line=HttpResponse.class.getDeclaredMethod("readLine");line.setAccessible(true);
            java.lang.reflect.Field u=sun.misc.Unsafe.class.getDeclaredField("theUnsafe");u.setAccessible(true);unsafe=(sun.misc.Unsafe)u.get(null);
            phase=helper.getDeclaredField("body");budget=helper.getDeclaredField("bytes");lineCount=helper.getDeclaredField("lines");characters=helper.getDeclaredField("characters");newline=helper.getDeclaredField("newline");
            for(java.lang.reflect.Field field:new java.lang.reflect.Field[]{phase,budget,lineCount,characters,newline})field.setAccessible(true);
        }
        ByteArrayOutputStream capture=new ByteArrayOutputStream(),errors=new ByteArrayOutputStream();
        try{
            System.setOut(new PrintStream(capture,true,"UTF-8"));System.setErr(new PrintStream(errors,true,"UTF-8"));
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
            MessageDigest digest=MessageDigest.getInstance("SHA-256");int cases=0;byte[] alphabet={13,10,'a',':'};
            for(int length=0;length<=8;length++){
                int count=1<<(2*length);
                for(int value=0;value<count;value++){
                    byte[] suffix=bytes("B: x\r\n\r\n");byte[] raw=new byte[length+suffix.length];int bits=value;
                    for(int i=0;i<length;i++){raw[i]=alphabet[bits&3];bits>>=2;}System.arraycopy(suffix,0,raw,length,suffix.length);
                    // Each generated short sequence is also tested ending directly at EOF.
                    digest.update((observation(raw)+"\n").getBytes("UTF-8"));
                    digest.update((observation(Arrays.copyOf(raw,length))+"\n").getBytes("UTF-8"));cases+=2;
                }
            }
            out.println("corpus cases="+cases+" sha256="+hex(digest.digest()));
            String start="HTTP/1.1 200 X\r\n";
            // Body-read budget controls carry one explicit zero length on both JARs.
            accepted(out,"line-65536",bytes(start+"Content-Length: 0\r\nX: "+repeat("x",65533)+"\r\n\r\n"),new byte[0]);
            accepted(out,"fields-128",bytes(start+"Content-Length: 0\r\n"+repeat("X: x\r\n",127)+"\r\n"),new byte[0]);
            accepted(out,"bytes-1048576",bytes(totalHeader(1048576)),new byte[0]);
            byte[] body=bytes(repeat("x",1048577)+repeat("\r\n",256));
            ByteArrayOutputStream raw=new ByteArrayOutputStream();raw.write(bytes(start+"Content-Length: "+body.length+"\r\n\r\n"));raw.write(body);
            accepted(out,"body-pass-through",raw.toByteArray(),body);
            byte[] one=bytes(start+"Content-Length: 0\r\n"+repeat("X: x\r\n",127)+"\r\n");
            ByteArrayOutputStream pair=new ByteArrayOutputStream();pair.write(one);pair.write(one);
            Source shared=new Source(pair.toByteArray());Memory connection=new Memory(shared);
            HttpResponse first=new HttpResponse(connection);check(first.getBody().length==0&&shared.consumed()==one.length);
            HttpResponse second=new HttpResponse(connection);check(second.getBody().length==0&&shared.consumed()==2*one.length&&first.headers.equals(second.headers));
            out.println("accepted fresh-response-budget headers_sha256="+hash(new TreeMap(second.headers).toString().getBytes("UTF-8"))+" consumed="+shared.consumed());
            if(fixed){
                rejected(out,"line-65537",bytes(start+"X: "+repeat("x",65534)+"\r\n\r\n"),start.length()+65537);
                rejected(out,"fields-129",bytes(start+repeat("X: x\r\n",129)+"\r\n"),start.length()+128*6+1);
                rejected(out,"bytes-1048577",bytes(totalHeader(1048577)),1048577);
                check(Class.forName("compat.BoundedHeaderStream").getMethod("wrap",InputStream.class).invoke(null,new Object[]{null})==null);
            }
            check(capture.size()==0&&errors.size()==0);
        }finally{System.setOut(out);System.setErr(err);OfflineGuard.assertUntouched();}
        out.println("PASS bounded header observations; guarded_operations=0");
    }
}
