package com.apple.xsr.net;

import com.apple.util.plist.PropertyList;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.ConnectException;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.HashMap;
import java.util.List;

/** OWNERSHIP TEST ONLY. Explicit memory shadow; plist integers are Long. */
public class AcpxConnection {
    public static int failures;
    public static volatile int constructors;
    public static volatile int closes;
    public static volatile ConnectException lastFailure;
    public static volatile Runnable onSend;
    public static final List<byte[]> bodies=new CopyOnWriteArrayList<byte[]>();
    public static final List<RequestMessage> requests=new CopyOnWriteArrayList<RequestMessage>();
    private final String host;
    public AcpxConnection(String address)throws IOException {
        if(++constructors>4)throw new AssertionError("Fixture constructor bound exceeded");
        if(constructors<=failures){lastFailure=new ConnectException("Synthetic connection failure");throw lastFailure;}
        host=address;
    }
    public String getHostAddress(){return host;}
    public void close()throws IOException{closes++;}
    public void disconnect()throws IOException{closes++;}
    public PropertyList send(RequestMessage request)throws IOException {
        if(bodies.size()>=4)throw new AssertionError("Fixture send bound exceeded");
        ByteArrayOutputStream out=new ByteArrayOutputStream(){
            public synchronized void write(int value){if(count>=65536)throw new AssertionError("Fixture body bound exceeded");super.write(value);}
            public synchronized void write(byte[] value,int start,int length){if(length>65536-count)throw new AssertionError("Fixture body bound exceeded");super.write(value,start,length);}
        };
        request.writeTo(out);if(onSend!=null)onSend.run();requests.add(request);bodies.add(out.toByteArray());
        HashMap<String,Object> root=new HashMap<String,Object>();root.put("status",Long.valueOf(0));return new PropertyList(root);
    }
}
