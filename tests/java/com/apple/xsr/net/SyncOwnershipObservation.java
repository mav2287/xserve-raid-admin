package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.io.ByteArrayOutputStream;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import sun.misc.Unsafe;

/** Original Manager/Sender, explicit memory transport shadow, no production data. */
public final class SyncOwnershipObservation {
    private static final AtomicInteger loggedErrors=new AtomicInteger();
    private static void check(boolean v,String message){if(!v)throw new AssertionError(message);}
    private static Unsafe unsafe()throws Exception{Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);return (Unsafe)f.get(null);}
    private static void set(Object o,String name,Object value)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);f.set(o,value);}
    private static Object get(Object o,String name)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
    private static void await(CountDownLatch l)throws Exception{check(l.await(5,TimeUnit.SECONDS),"Fixture barrier absent");}
    private static CommunicationsManager manager()throws Exception{
        CommunicationsManager m=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);set(m,"queue",new LinkedList<Object>());set(m,"system",unsafe().allocateInstance(RaidSystem.class));set(m,"thread",new Thread());set(m,"connected",true);set(m,"connection",new AcpxConnection("192.0.2.1"));return m;
    }
    private static Object waitingSender(CommunicationsManager m,Thread caller)throws Exception{
        LinkedList<?> queue=(LinkedList<?>)get(m,"queue");long end=System.nanoTime()+5000000000L;
        while(System.nanoTime()<end){synchronized(queue){if(queue.size()==1&&caller.getState()==Thread.State.WAITING){Object sender=get(queue.getFirst(),"handler");ThreadInfo info=ManagementFactory.getThreadMXBean().getThreadInfo(caller.getId(),0);if(info==null||info.getLockInfo()==null||info.getLockInfo().getIdentityHashCode()!=System.identityHashCode(sender))continue;check(!(Boolean)get(sender,"handled"),"Sender already answered");return sender;}}Thread.sleep(2);}
        throw new AssertionError("Actual sender wait not observed");
    }
    private static void cleanup(CommunicationsManager m,Thread...threads)throws Exception{m.shutdown();for(Thread t:threads){t.interrupt();t.join(5000);check(!t.isAlive(),"Fixture thread did not exit");}}
    private static void queued(boolean fixed)throws Exception{
        final CommunicationsManager m=manager();final AtomicReference<Throwable> error=new AtomicReference<Throwable>();final RequestMessage cancelled=new AcpxMessageFactory().newRestartSystemRequest();
        Thread caller=new Thread(()->{try{m.postMessage(cancelled);error.set(new AssertionError("Cancelled caller succeeded"));}catch(Throwable e){error.set(e);}},"fixture-queued-caller");caller.setDaemon(true);caller.start();Object sender=waitingSender(m,caller);caller.interrupt();caller.join(5000);check(!caller.isAlive()&&error.get()!=null&&error.get().getClass()==java.io.IOException.class&&"communications shutdown".equals(error.get().getMessage())&&(Boolean)get(sender,"handled"),"Queued cancellation response differs");
        final int[] follow={0};m.postMessageAsync((system,r,context)->{check(r.getResultCode()==0,"Healthy follow-on failed");follow[0]++;m.shutdown();},new AcpxMessageFactory().newGetTimeRequest());set(m,"thread",Thread.currentThread());m.run();
        check(AcpxConnection.requests.size()==(fixed?1:2)&&follow[0]==1,"Cancelled request send ownership differs");ByteArrayOutputStream expected=new ByteArrayOutputStream();new AcpxMessageFactory().newGetTimeRequest().writeTo(expected);check(Arrays.equals(AcpxConnection.bodies.get(AcpxConnection.bodies.size()-1),expected.toByteArray()),"Follow-on body changed");if(!fixed){ByteArrayOutputStream cancelledBody=new ByteArrayOutputStream();cancelled.writeTo(cancelledBody);check(Arrays.equals(AcpxConnection.bodies.get(0),cancelledBody.toByteArray()),"Legacy cancelled body differs");}
        System.out.println("sync_ownership queued fixed="+fixed+" cancelled_send="+(fixed?0:1)+" healthy_follow_on=1 caller=legacy-IOException");
    }
    private static void active(boolean fixed)throws Exception{
        final CommunicationsManager m=manager();final AtomicReference<Throwable> error=new AtomicReference<Throwable>(),workerError=new AtomicReference<Throwable>();final AtomicReference<Response> returned=new AtomicReference<Response>();final AtomicBoolean returnedInterrupted=new AtomicBoolean(true);final CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
        AcpxConnection.onSend=()->{entered.countDown();try{check(release.await(8,TimeUnit.SECONDS),"Release missing");}catch(InterruptedException e){throw new AssertionError("Worker interrupted");}};
        Thread caller=new Thread(()->{try{returned.set(m.postMessage(new AcpxMessageFactory().newGetStatusRequest()));returnedInterrupted.set(Thread.currentThread().isInterrupted());}catch(Throwable e){error.set(e);}},"fixture-active-caller");caller.setDaemon(true);caller.start();final Object sender=waitingSender(m,caller);
        Thread worker=new Thread(()->{try{m.run();}catch(Throwable e){workerError.set(e);}},"fixture-active-worker");worker.setDaemon(true);set(m,"thread",worker);worker.start();await(entered);
        long waits=ManagementFactory.getThreadMXBean().getThreadInfo(caller.getId(),0).getWaitedCount();caller.interrupt();
        try{
            if(fixed){long end=System.nanoTime()+5000000000L;boolean witnessed=false;while(System.nanoTime()<end&&!witnessed){ThreadInfo info=ManagementFactory.getThreadMXBean().getThreadInfo(caller.getId(),0);witnessed=info!=null&&info.getThreadState()==Thread.State.WAITING&&info.getWaitedCount()>waits&&info.getLockInfo()!=null&&info.getLockInfo().getIdentityHashCode()==System.identityHashCode(sender);if(!witnessed)Thread.sleep(2);}check(witnessed&&error.get()==null&&returned.get()==null&&(Boolean)get(sender,"claimed")&&!(Boolean)get(sender,"handled"),"Active interrupt did not wait real reply");}
            else{caller.join(5000);check(!caller.isAlive()&&error.get()!=null&&error.get().getClass()==java.io.IOException.class&&"communications shutdown".equals(error.get().getMessage())&&(Boolean)get(sender,"handled")&&returned.get()==null,"Legacy active failure not observed");}
            release.countDown();if(fixed){caller.join(5000);check(!caller.isAlive()&&error.get()==null&&returned.get()!=null&&returned.get().getResultCode()==0&&returned.get()==get(sender,"response")&&!returnedInterrupted.get(),"Active real response or consumed interrupt lost");}m.shutdown();worker.join(5000);check(!worker.isAlive()&&workerError.get()==null&&AcpxConnection.requests.size()==1,"Active send replayed or worker failed");
        }finally{release.countDown();cleanup(m,caller,worker);}
        ByteArrayOutputStream expectedBody=new ByteArrayOutputStream();new AcpxMessageFactory().newGetStatusRequest().writeTo(expectedBody);check(Arrays.equals(AcpxConnection.bodies.get(0),expectedBody.toByteArray()),"Active serialized body differs");
        System.out.println("sync_ownership active fixed="+fixed+" sends=1 outcome="+(fixed?"real-response-identity":"failure-before-reply"));
    }
    private static void notifyRace(boolean fixed)throws Exception{
        final CommunicationsManager m=manager();final AtomicReference<Throwable> error=new AtomicReference<Throwable>();final AtomicReference<Response> returned=new AtomicReference<Response>();final AtomicBoolean returnedInterrupted=new AtomicBoolean(true);Thread caller=new Thread(()->{try{returned.set(m.postMessage(new AcpxMessageFactory().newGetStatusRequest()));returnedInterrupted.set(Thread.currentThread().isInterrupted());}catch(Throwable e){error.set(e);}},"fixture-notify-race");caller.setDaemon(true);caller.start();Object sender=waitingSender(m,caller);final Response answer=new BasicResponse(Response.TYPE_COMMAND,null,0,null);
        synchronized(sender){caller.interrupt();long end=System.nanoTime()+5000000000L;boolean blocked=false;while(System.nanoTime()<end&&!blocked){ThreadInfo info=ManagementFactory.getThreadMXBean().getThreadInfo(caller.getId(),0);blocked=info!=null&&info.getThreadState()==Thread.State.BLOCKED&&info.getLockOwnerId()==Thread.currentThread().getId()&&info.getLockInfo()!=null&&info.getLockInfo().getIdentityHashCode()==System.identityHashCode(sender);if(!blocked)Thread.sleep(2);}check(blocked,"Interrupted caller monitor reacquisition not witnessed");((CommunicationHandler)sender).handleResponse((RaidSystem)get(m,"system"),answer,null);}
        caller.join(5000);check(!caller.isAlive(),"Notify race caller stalled");if(fixed)check(returned.get()==answer&&error.get()==null&&!returnedInterrupted.get(),"Real reply or consumed interrupt overwritten");else check(returned.get()==null&&error.get()!=null&&error.get().getClass()==java.io.IOException.class,"Legacy overwrite not observed");m.shutdown();set(m,"thread",Thread.currentThread());m.run();check(AcpxConnection.requests.isEmpty(),"Notify-race stopped drain sent request");
        System.out.println("sync_ownership notify_race fixed="+fixed+" result="+(fixed?"real-response-identity":"interrupt-overwrote-reply"));
    }
    private static void firstReply(boolean fixed)throws Exception{
        Class<?> cls=Class.forName("com.apple.xsr.net.CommunicationsManager$SyncSender");Object sender=unsafe().allocateInstance(cls);Response first=new BasicResponse(Response.TYPE_COMMAND,null,0,null),second=new BasicResponse(Response.TYPE_COMMAND,null,-102,new CommShutdownException());
        ((CommunicationHandler)sender).handleResponse(null,first,null);((CommunicationHandler)sender).handleResponse(null,second,null);check(get(sender,"response")== (fixed?first:second),"Late response policy differs");if(fixed){Method claim=cls.getDeclaredMethod("claim");claim.setAccessible(true);check(!(Boolean)claim.invoke(sender),"Answered sender claimed");Object fresh=unsafe().allocateInstance(cls);check((Boolean)claim.invoke(fresh)&&!(Boolean)claim.invoke(fresh),"Claim-once invariant differs");}else{try{cls.getDeclaredMethod("claim");throw new AssertionError("Legacy claim unexpectedly exists");}catch(NoSuchMethodException expected){}}
        System.out.println("sync_ownership first_reply fixed="+fixed+" retained="+(fixed?"first":"last")+" claim_once="+fixed);
    }
    private static void resource(Class<?> cls,String expected)throws Exception{java.io.InputStream in=cls.getResourceAsStream("/"+cls.getName().replace('.','/')+".class");check(in!=null,"Class resource missing");java.security.MessageDigest hash=java.security.MessageDigest.getInstance("SHA-256");try{byte[] bytes=new byte[4096];for(int n;(n=in.read(bytes))!=-1;)hash.update(bytes,0,n);}finally{in.close();}StringBuilder hex=new StringBuilder();for(byte b:hash.digest())hex.append(String.format(java.util.Locale.ROOT,"%02x",b&255));check(hex.toString().equals(expected),"Class resource identity differs");}
    private static java.io.File source(Class<?> cls)throws Exception{return new java.io.File(cls.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile();}
    public static void main(String[] args)throws Exception{
        check(args.length==12&&Arrays.asList("queued","active","notify-race","first-reply").contains(args[0])&&Arrays.asList("fixed","legacy").contains(args[1]),"Unknown fixture mode");OfflineGuard.install();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.ALL);org.apache.log4j.Logger root=org.apache.log4j.Logger.getRootLogger();root.setLevel(org.apache.log4j.Level.WARN);root.removeAllAppenders();root.addAppender(new org.apache.log4j.AppenderSkeleton(){protected void append(org.apache.log4j.spi.LoggingEvent event){if(event.getLevel().isGreaterOrEqual(org.apache.log4j.Level.WARN))loggedErrors.incrementAndGet();}public void close(){}public boolean requiresLayout(){return false;}});root.warn("SYNTHETIC_CAPTURE_PROBE");check(loggedErrors.get()==1,"Warning capture not active");loggedErrors.set(0);
        check(source(CommunicationsManager.class).equals(new java.io.File(args[2]).getCanonicalFile())&&source(AcpxConnection.class).equals(new java.io.File(args[3]).getCanonicalFile()),"Application/shadow CodeSource differs");resource(CommunicationsManager.class,args[4]);Class<?> senderClass=Class.forName("com.apple.xsr.net.CommunicationsManager$SyncSender");check(source(senderClass).equals(new java.io.File(args[2]).getCanonicalFile()),"Sender CodeSource differs");resource(senderClass,args[5]);resource(AcpxConnection.class,args[6]);java.io.File fixtures=new java.io.File(args[7]).getCanonicalFile();check(source(SyncOwnershipObservation.class).equals(fixtures)&&source(OfflineGuard.class).equals(fixtures),"Fixture CodeSource differs");resource(SyncOwnershipObservation.class,args[8]);resource(OfflineGuard.class,args[9]);Class<?> capture=Class.forName("com.apple.xsr.net.SyncOwnershipObservation$1"),buffer=Class.forName("com.apple.xsr.net.AcpxConnection$1");check(source(capture).equals(fixtures)&&source(buffer).equals(new java.io.File(args[3]).getCanonicalFile()),"Nested class CodeSource differs");resource(capture,args[10]);resource(buffer,args[11]);AcpxConnection.failures=0;AcpxConnection.constructors=0;AcpxConnection.closes=0;AcpxConnection.onSend=null;AcpxConnection.requests.clear();AcpxConnection.bodies.clear();boolean fixed=args[1].equals("fixed");
        switch(args[0]){case "queued":queued(fixed);break;case "active":active(fixed);break;case "notify-race":notifyRace(fixed);break;case "first-reply":firstReply(fixed);break;default:throw new AssertionError("Mode");}
        check(AcpxConnection.constructors==(args[0].equals("first-reply")?0:1),"Unexpected memory reconnect");check(loggedErrors.get()==0,"Caught application warning/error observed");OfflineGuard.assertUntouched();System.out.println("PASS memory transport ownership; guarded_operations=0; production transport unqualified");
    }
}
