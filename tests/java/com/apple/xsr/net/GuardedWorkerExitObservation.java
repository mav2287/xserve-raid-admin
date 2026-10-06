package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.reflect.Field;
import java.util.LinkedList;
import java.util.concurrent.atomic.AtomicReference;
import sun.misc.Unsafe;

/** Exercises guarded worker exits with memory transport and synthetic failures only. */
public final class GuardedWorkerExitObservation {
    private static final class SyntheticFault extends Error {
        SyntheticFault() {}
        public String getMessage(){throw new AssertionError("Fault rendered");}
        public String toString(){throw new AssertionError("Fault rendered");}
    }
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    private static Unsafe unsafe()throws Exception{Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);return (Unsafe)f.get(null);}
    private static void set(Object o,String name,Object value)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);f.set(o,value);}
    private static Object get(Object o,String name)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
    private static void resource(Class<?> cls,String expected)throws Exception{java.io.InputStream in=cls.getResourceAsStream("/"+cls.getName().replace('.','/')+".class");check(in!=null,"Class resource missing");java.security.MessageDigest hash=java.security.MessageDigest.getInstance("SHA-256");try{byte[] bytes=new byte[4096];for(int n;(n=in.read(bytes))!=-1;)hash.update(bytes,0,n);}finally{in.close();}StringBuilder hex=new StringBuilder();for(byte b:hash.digest())hex.append(String.format(java.util.Locale.ROOT,"%02x",b&255));check(hex.toString().equals(expected),"Class resource identity differs");}
    private static java.io.File source(Class<?> cls)throws Exception{return new java.io.File(cls.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile();}
    private static Object queuedSender(CommunicationsManager manager,Thread caller,int count)throws Exception{
        LinkedList<?> queue=(LinkedList<?>)get(manager,"queue");long deadline=System.nanoTime()+5000000000L;
        while(System.nanoTime()<deadline){synchronized(queue){if(queue.size()==count&&caller.getState()==Thread.State.WAITING)return get(queue.getLast(),"handler");}Thread.sleep(2);}throw new AssertionError("Queued sender wait absent");
    }
    private static void waiting(Thread caller,Object sender)throws Exception{
        ThreadInfo info=ManagementFactory.getThreadMXBean().getThreadInfo(caller.getId(),0);check(info!=null&&info.getThreadState()==Thread.State.WAITING&&info.getLockInfo()!=null&&info.getLockInfo().getIdentityHashCode()==System.identityHashCode(sender)&&!(Boolean)get(sender,"handled"),"Stranded caller not positively witnessed");
    }
    public static void main(String[] args)throws Exception{
        check(args.length==12&&(args[0].equals("send-error")||args[0].equals("callback-error"))&&args[1].equals("workerfix"),"Unknown characterization mode");OfflineGuard.install();fixture.FixtureIdentity.verify();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        check(source(CommunicationsManager.class).equals(new java.io.File(args[2]).getCanonicalFile())&&source(AcpxConnection.class).equals(new java.io.File(args[3]).getCanonicalFile()),"Application or shadow source differs");
        resource(CommunicationsManager.class,args[4]);Class<?> senderClass=Class.forName("com.apple.xsr.net.CommunicationsManager$SyncSender");check(source(senderClass).equals(new java.io.File(args[2]).getCanonicalFile()),"Sender CodeSource differs");resource(senderClass,args[5]);resource(AcpxConnection.class,args[6]);java.io.File fixtures=new java.io.File(args[7]).getCanonicalFile();Class<?> faultClass=SyntheticFault.class,bufferClass=Class.forName("com.apple.xsr.net.AcpxConnection$1");check(source(GuardedWorkerExitObservation.class).equals(fixtures)&&source(OfflineGuard.class).equals(fixtures)&&source(faultClass).equals(fixtures)&&source(bufferClass).equals(new java.io.File(args[3]).getCanonicalFile()),"Fixture/nested shadow CodeSource differs");resource(GuardedWorkerExitObservation.class,args[8]);resource(OfflineGuard.class,args[9]);resource(faultClass,args[10]);resource(bufferClass,args[11]);
        compat.WorkerExit.prepare();
        CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);set(manager,"queue",new LinkedList<Object>());set(manager,"system",unsafe().allocateInstance(RaidSystem.class));set(manager,"thread",new Thread());set(manager,"connected",true);set(manager,"connection",new AcpxConnection("192.0.2.1"));
        final int[] attempts={0};final SyntheticFault fault=new SyntheticFault();boolean callback=args[0].equals("callback-error");if(callback)manager.postMessageAsync((s,r,c)->{attempts[0]++;throw fault;},new AcpxMessageFactory().newGetTimeRequest());else AcpxConnection.onSend=()->{throw fault;};
        AtomicReference<Throwable> callerError=new AtomicReference<Throwable>(),workerError=new AtomicReference<Throwable>();Thread caller=new Thread(()->{try{manager.postMessage(new AcpxMessageFactory().newGetStatusRequest());callerError.set(new AssertionError("Caller unexpectedly succeeded"));}catch(Throwable error){callerError.set(error);}},"fixture-exit-caller");caller.setDaemon(true);caller.start();Object sender=queuedSender(manager,caller,callback?2:1);waiting(caller,sender);
        Thread worker=new Thread(()->{try{manager.run();}catch(Throwable error){workerError.set(error);}},"fixture-exit-worker");worker.setDaemon(true);set(manager,"thread",worker);worker.start();worker.join(5000);check(!worker.isAlive()&&workerError.get()==null&&manager.isStopped()&&!manager.isConnected(),"Guarded exit did not retire");caller.join(5000);check(!caller.isAlive(),"Fixed caller remained stranded");check((Boolean)get(sender,"handled")&&(Boolean)get(sender,"claimed")==!callback,"Fixed completion ownership differs");
        Response answer=(Response)get(sender,"response");if(callback){check(callerError.get()!=null&&callerError.get().getClass()==CommShutdownException.class&&answer.getException().getClass()==CommShutdownException.class&&attempts[0]==1,"Unsent or callback-once result differs");}else{check(callerError.get()!=null&&callerError.get().getClass()==java.io.IOException.class&&"Worker stopped; operation outcome is unconfirmed".equals(callerError.get().getMessage())&&answer.getException().getClass()==compat.UntrustedResponseException.class,"Active unconfirmed result differs");}
        LinkedList<?> queue=(LinkedList<?>)get(manager,"queue");synchronized(queue){check(queue.isEmpty(),"Fixed queue not drained");}check(AcpxConnection.requests.size()==(callback?1:0),"Command replayed");OfflineGuard.assertUntouched();
        System.out.println("worker_exit "+args[0]+" actual_worker_dead=true stopped=true caller_completed=true queue=0 outcome="+(callback?"unsent-shutdown":"unconfirmed"));System.out.println("PASS guarded worker exit experiment; guarded_operations=0");
    }
}
