package compat;
import java.io.IOException;
import java.net.Socket;
import java.net.SocketException;
import fixture.OfflineGuard;

/** Direct setup failure controls; no native sockets, DNS or caller callbacks. */
public final class ConfigurationObservation {
    static void check(boolean value) { if(!value)throw new AssertionError("Configuration assertion"); }
    static final class HostileSocket extends SocketException {
        @Override public String getMessage(){throw new AssertionError("Cause rendered");}
        @Override public String toString(){throw new AssertionError("Cause rendered");}
    }
    static final class Fake extends Socket {
        int timeout, closes, fault;
        Throwable raised;
        @Override public void setSoTimeout(int value) throws SocketException {
            timeout=value;
            if(fault==1 || fault==8 || fault==9 || fault==10)throw new HostileSocket();
            if(raised instanceof RuntimeException)throw (RuntimeException)raised;
            if(raised instanceof Error)throw (Error)raised;
        }
        @Override public int getSoTimeout() throws SocketException {
            if(fault==2)return 0;
            if(fault==3)throw new HostileSocket();
            return timeout;
        }
        @Override public void close() throws IOException {
            closes++; if(fault==9)throw new IllegalStateException(); if(fault==10)throw new AssertionError();
            if(fault==8)throw new IOException(){
                @Override public String getMessage(){throw new AssertionError("Close rendered");}
                @Override public String toString(){throw new AssertionError("Close rendered");}
            };
        }
    }
    static void fixed(IOException error) {
        check("Connection setup failed".equals(error.getMessage()));
        check(error.getCause()==null && error.getSuppressed().length==0);
    }
    public static void main(String[] args)throws Exception {
        OfflineGuard.install();int cases=0;
        for(int timeout:new int[]{30000,7301}) {
            Fake socket=new Fake();check(SocketConfiguration.configure(socket,timeout)==socket);
            check(socket.timeout==timeout && socket.closes==0);cases++;
        }
        for(int fault:new int[]{1,2,3,8}) {
            Fake socket=new Fake();socket.fault=fault;
            Thread.currentThread().interrupt();
            try { SocketConfiguration.configure(socket,30000);throw new AssertionError("Setup failure ignored"); }
            catch(IOException error) { fixed(error);check(error.getClass()==(fault==2?IOException.class:SocketException.class));check(Thread.currentThread().isInterrupted()); }
            finally { Thread.interrupted(); }
            check(socket.closes==1);cases++;
        }
        for(int timeout:new int[]{0,-1}) {
            Fake socket=new Fake();
            try { SocketConfiguration.configure(socket,timeout);throw new AssertionError("Infinite read accepted"); }
            catch(IOException error){fixed(error);}
            check(socket.closes==1 && socket.timeout==0);
            try { SocketConfiguration.open("must.not.resolve.invalid",timeout);throw new AssertionError("Validation missing"); }
            catch(IOException error){fixed(error);}cases++;
        }
        for(Throwable raised:new Throwable[]{new SecurityException(),new IllegalArgumentException(),new AssertionError(),new ThreadDeath()}) {
            Fake socket=new Fake();socket.raised=raised;
            try { SocketConfiguration.configure(socket,30000);throw new AssertionError("Failure ignored"); }
            catch(Throwable error) {
                if(raised instanceof SecurityException || raised instanceof Error)check(error==raised);
                else { check(error instanceof IOException);fixed((IOException)error); }
            }
            check(socket.closes==1);cases++;
        }
        for(int fault:new int[]{9,10}) {
            Fake socket=new Fake();socket.fault=fault;
            try { SocketConfiguration.configure(socket,30000);throw new AssertionError("Setup failure ignored"); }
            catch(Throwable failure) { check(failure.getClass()==SocketException.class);fixed((IOException)failure); }
            check(socket.closes==1);cases++;
        }
        OfflineGuard.assertUntouched();check(cases==14);
        System.out.println("PASS direct configuration prototype; cases=14; guarded_operations=0");
    }
}
