package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.awt.EventQueue;
import java.lang.reflect.Field;
import java.lang.reflect.Proxy;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import javax.swing.SwingUtilities;
import sun.misc.Unsafe;

/** Real admission/worker/sender, memory only, no Manager constructor or transport. */
public final class StoppedPostObservation {
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    private static Unsafe unsafe()throws Exception{Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);return (Unsafe)f.get(null);}
    private static void set(CommunicationsManager m,String name,Object value)throws Exception{Field f=CommunicationsManager.class.getDeclaredField(name);f.setAccessible(true);f.set(m,value);}
    private static Object get(Object m,String name)throws Exception{Field f=m.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(m);}
    private static CommunicationsManager manager()throws Exception{
        CommunicationsManager m=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);
        set(m,"queue",new LinkedList<Object>());set(m,"thread",new Thread());
        set(m,"system",unsafe().allocateInstance(RaidSystem.class));return m;
    }
    private static RequestMessage request(final AtomicInteger clones,final Runnable onClone){
        final RequestMessage delegate=new AcpxMessageFactory().newGetStatusRequest();
        return (RequestMessage)Proxy.newProxyInstance(RequestMessage.class.getClassLoader(),new Class[]{RequestMessage.class},(proxy,method,args)->{
            if(method.getName().equals("clone")){clones.incrementAndGet();if(onClone!=null)onClone.run();return proxy;}
            try{return method.invoke(delegate,args);}catch(java.lang.reflect.InvocationTargetException e){throw e.getCause();}
        });
    }
    private static void await(CountDownLatch latch)throws Exception{check(latch.await(5,TimeUnit.SECONDS),"Fixture callback missing");}
    private static void response(CommunicationsManager m,Object q,RaidSystem system,Response response,Object seen,Object wanted,boolean edt)throws Exception{
        check(system==get(m,"system")&&seen==wanted&&response.getType()==Response.TYPE_COMMAND&&response.getContent()==null&&response.getResultCode()==-102&&response.getException().getClass()==CommShutdownException.class,"Refused response identity/fields differ");
        check(!Thread.holdsLock(q)&&SwingUtilities.isEventDispatchThread()==edt,"Callback thread/queue ownership differs");
        synchronized(q){} // Callback can acquire the actual queue monitor.
    }
    private static void async(boolean fixed)throws Exception{
        final CommunicationsManager m=manager();m.shutdown();m.run();final LinkedList<?> q=(LinkedList<?>)get(m,"queue");
        final AtomicInteger clones=new AtomicInteger(),calls=new AtomicInteger();final Object context=new Object();final CountDownLatch done=new CountDownLatch(1);final AtomicReference<Throwable> errors=new AtomicReference<Throwable>();
        final Thread poster=Thread.currentThread();CommunicationHandler handler=(system,r,seen)->{try{check(Thread.currentThread()!=poster,"Inline callback");response(m,q,system,r,seen,context,true);calls.incrementAndGet();}catch(Throwable e){errors.set(e);}finally{done.countDown();}};
        m.postMessageAsync(handler,request(clones,null),context);
        if(fixed){await(done);check(errors.get()==null&&calls.get()==1&&q.isEmpty(),"Stopped async refusal failed");}
        else check(q.size()==1&&calls.get()==0&&clones.get()==1,"Original stranded queue not positively observed");
        check(clones.get()==1,"Clone count changed");
        System.out.println("stopped_post async fixed="+fixed+" queue="+(fixed?0:1)+" callbacks="+(fixed?1:0)+" clones=1");
    }
    private static void sync(boolean fixed)throws Exception{
        final CommunicationsManager m=manager();final AtomicInteger clones=new AtomicInteger();final AtomicReference<Throwable> error=new AtomicReference<Throwable>();final LinkedList<?> q=(LinkedList<?>)get(m,"queue");
        RequestMessage r=request(clones,()->{if(clones.get()==1)m.shutdown();});
        Thread caller=new Thread(()->{try{m.postMessage(r);error.set(new AssertionError("Stopped race returned success"));}catch(Throwable e){error.set(e);}},"fixture-stopped-sync");caller.setDaemon(true);caller.start();
        if(fixed){caller.join(5000);check(!caller.isAlive()&&error.get()!=null&&error.get().getClass()==CommShutdownException.class&&q.isEmpty()&&clones.get()==2,"Precheck race not refused");for(Thread t:Thread.getAllStackTraces().keySet())check(!t.getName().startsWith("AWT-EventQueue"),"Sync refusal used EDT");}
        else{
            long end=System.nanoTime()+5000000000L;boolean witnessed=false;
            while(System.nanoTime()<end&&!witnessed){synchronized(q){if(q.size()==1){Object handler=get(q.getFirst(),"handler");witnessed=caller.getState()==Thread.State.WAITING&&!(Boolean)get(handler,"handled");}}if(!witnessed)Thread.sleep(2);}
            check(witnessed&&error.get()==null&&clones.get()==2,"Original pending sender not positively observed");caller.interrupt();caller.join(5000);check(!caller.isAlive()&&error.get() instanceof java.io.IOException,"Control cleanup failed");
        }
        System.out.println("stopped_post sync fixed="+fixed+" clones=2 outcome="+(fixed?"CommShutdownException":"pending-sender-observed"));
    }
    private static void worker()throws Exception{
        final CommunicationsManager m=manager();final LinkedList<?> q=(LinkedList<?>)get(m,"queue");set(m,"thread",Thread.currentThread());m.shutdown();final AtomicInteger calls=new AtomicInteger(),clones=new AtomicInteger();final Object context=new Object();
        CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem system,Response r,Object seen){try{response(m,q,system,r,seen,context,false);int n=calls.incrementAndGet();if(n<3)m.postMessageAsync(this,request(clones,null),context);}catch(Exception e){throw new AssertionError("Worker callback failed");}}};
        m.postMessageAsync(handler,request(clones,null),context);check(q.size()==1&&calls.get()==0,"Worker post not enqueued");m.run();check(q.isEmpty()&&calls.get()==3&&clones.get()==3,"Worker drain/reposts differ");
        System.out.println("stopped_post worker callbacks=3 clones=3 queue=0 original_thread=true");
    }
    private static void concurrency()throws Exception{
        final CommunicationsManager m=manager();m.shutdown();final LinkedList<?> q=(LinkedList<?>)get(m,"queue");final AtomicInteger clones=new AtomicInteger(),calls=new AtomicInteger();final CountDownLatch done=new CountDownLatch(32);final AtomicReference<Throwable> error=new AtomicReference<Throwable>();final Object[] contexts=new Object[32];final boolean[] seen=new boolean[32];Thread[] posters=new Thread[32];
        for(int i=0;i<32;i++){final int index=i;contexts[i]=new Object();posters[i]=new Thread(()->{try{m.postMessageAsync((system,r,context)->{try{response(m,q,system,r,context,contexts[index],true);check(!seen[index],"Duplicate callback");seen[index]=true;calls.incrementAndGet();}catch(Throwable e){error.set(e);}finally{done.countDown();}},request(clones,null),contexts[index]);}catch(Throwable e){error.set(e);}},"fixture-stopped-poster");posters[i].setDaemon(true);posters[i].start();}
        for(Thread poster:posters){poster.join(5000);check(!poster.isAlive(),"Poster stalled");}await(done);SwingUtilities.invokeAndWait(()->{});check(error.get()==null&&calls.get()==32&&clones.get()==32&&q.isEmpty(),"Concurrent refusal differs");for(boolean value:seen)check(value,"Missing context");
        System.out.println("stopped_post concurrent contexts=32 callbacks=32 clones=32 queue=0");
    }
    private static void edt()throws Exception{
        final CommunicationsManager m=manager();m.shutdown();final LinkedList<?> q=(LinkedList<?>)get(m,"queue");final Object callerLock=new Object(),context=new Object();final AtomicInteger clones=new AtomicInteger();final CountDownLatch done=new CountDownLatch(1);final AtomicReference<Throwable> error=new AtomicReference<Throwable>();final boolean[] returned={false};
        SwingUtilities.invokeAndWait(()->{synchronized(callerLock){m.postMessageAsync((system,r,seen)->{try{check(returned[0]&&!Thread.holdsLock(callerLock),"EDT refusal inline or caller-locked");response(m,q,system,r,seen,context,true);synchronized(callerLock){}}catch(Throwable e){error.set(e);}finally{done.countDown();}},request(clones,null),context);returned[0]=true;}});
        await(done);check(error.get()==null&&q.isEmpty()&&clones.get()==1,"EDT refusal failed");System.out.println("stopped_post edt deferred=true caller_lock_released=true queue=0");
    }
    private static void nullAndClone()throws Exception{
        for(Thread t:Thread.getAllStackTraces().keySet())check(!t.getName().startsWith("AWT-EventQueue"),"EDT already started in null fixture");
        CommunicationsManager m=manager();m.shutdown();LinkedList<?> q=(LinkedList<?>)get(m,"queue");AtomicInteger clones=new AtomicInteger();m.postMessageAsync(null,request(clones,null));check(clones.get()==1&&q.isEmpty(),"Null post queued");
        final RuntimeException failure=new RuntimeException("synthetic clone failure");try{m.postMessageAsync(null,request(clones,()->{throw failure;}));throw new AssertionError("Clone failure hidden");}catch(RuntimeException e){check(e==failure,"Clone exception identity changed");}
        final CountDownLatch acquired=new CountDownLatch(1);Thread probe=new Thread(()->{synchronized(q){acquired.countDown();}});probe.setDaemon(true);probe.start();await(acquired);probe.join(5000);check(q.isEmpty()&&clones.get()==2,"Clone failure queued");
        for(Thread t:Thread.getAllStackTraces().keySet())check(!t.getName().startsWith("AWT-EventQueue"),"Null refusal started EDT");
        System.out.println("stopped_post null clones=1 queue=0 edt_started=false; clone_failure identity=true monitor_released=true");
    }
    private static void throwing()throws Exception{
        final CommunicationsManager m=manager();m.shutdown();final AtomicInteger rendered=new AtomicInteger(),signals=new AtomicInteger();final AtomicReference<Throwable> error=new AtomicReference<Throwable>();
        org.apache.log4j.Logger logger=org.apache.log4j.Logger.getLogger(CommunicationsManager.class);logger.setLevel(org.apache.log4j.Level.ERROR);logger.setAdditivity(false);logger.addAppender(new org.apache.log4j.AppenderSkeleton(){protected void append(org.apache.log4j.spi.LoggingEvent event){try{check(event.getMessage().equals("RAID_ADMIN_STOPPED_CALLBACK_FAILED")&&event.getThrowableInformation()==null,"Unsafe callback failure log");signals.incrementAndGet();}catch(Throwable e){error.set(e);}}public void close(){}public boolean requiresLayout(){return false;}});
        RuntimeException hostile=new RuntimeException(){public String getMessage(){rendered.incrementAndGet();throw new AssertionError("Rendered");}public String toString(){rendered.incrementAndGet();throw new AssertionError("Rendered");}};
        m.postMessageAsync((system,r,ctx)->{throw hostile;},request(new AtomicInteger(),null));SwingUtilities.invokeAndWait(()->{});check(rendered.get()==0&&signals.get()==1&&error.get()==null,"Unsafe exception rendering");
        System.out.println("stopped_post throwing fixed_log_only=true render_calls=0 callback_exception_contained=true");
    }
    private static void boundary(boolean unsafe)throws Exception{
        final CommunicationsManager m=manager();m.shutdown();final AtomicInteger signals=new AtomicInteger(),escaped=new AtomicInteger();final AtomicReference<Throwable> observed=new AtomicReference<Throwable>(),unexpected=new AtomicReference<Throwable>();final AtomicInteger loggerEscapes=new AtomicInteger();final RuntimeException appenderFailure=new RuntimeException("synthetic appender failure");
        final Error fatal=new Error("synthetic fatal callback");final CountDownLatch done=new CountDownLatch(1);Thread.UncaughtExceptionHandler previous=Thread.getDefaultUncaughtExceptionHandler();
        org.apache.log4j.Logger logger=org.apache.log4j.Logger.getLogger(CommunicationsManager.class);logger.setLevel(org.apache.log4j.Level.ERROR);logger.setAdditivity(false);logger.addAppender(new org.apache.log4j.AppenderSkeleton(){
            @Override public void doAppend(org.apache.log4j.spi.LoggingEvent event){check(event.getMessage().equals("RAID_ADMIN_STOPPED_CALLBACK_FAILED")&&event.getThrowableInformation()==null,"Boundary log not fixed");signals.incrementAndGet();throw appenderFailure;}
            protected void append(org.apache.log4j.spi.LoggingEvent event){}public void close(){}public boolean requiresLayout(){return false;}
        });
        try{Thread.setDefaultUncaughtExceptionHandler((thread,error)->{if(error==fatal&&thread.getName().startsWith("AWT-EventQueue")){observed.set(error);escaped.incrementAndGet();done.countDown();}else if(unsafe&&error==appenderFailure)loggerEscapes.incrementAndGet();else unexpected.set(error);});
            m.postMessageAsync((system,r,ctx)->{throw new RuntimeException("synthetic callback failure");},request(new AtomicInteger(),null));SwingUtilities.invokeAndWait(()->{});
            m.postMessageAsync((system,r,ctx)->{throw new LinkageError("synthetic linkage failure");},request(new AtomicInteger(),null));SwingUtilities.invokeAndWait(()->{});check(signals.get()==2&&unexpected.get()==null&&loggerEscapes.get()==(unsafe?2:0),"Nonfatal boundary escaped or not signaled");
            m.postMessageAsync((system,r,ctx)->{throw fatal;},request(new AtomicInteger(),null));await(done);SwingUtilities.invokeAndWait(()->{});check(observed.get()==fatal&&escaped.get()==1&&signals.get()==2&&unexpected.get()==null,"Fatal callback swallowed or unexpected escape");
        }finally{Thread.setDefaultUncaughtExceptionHandler(previous);}
        System.out.println(unsafe?"stopped_post boundary negative_control exact_appender_escapes=2 fatal_identity=true":"stopped_post boundary logger_failure_contained=true linkage_contained=true nonLinkage_Error_escaped=true fixed_signals=2");
    }
    private static void missingHelper()throws Exception{
        CommunicationsManager m=manager();m.shutdown();LinkedList<?> q=(LinkedList<?>)get(m,"queue");AtomicInteger clones=new AtomicInteger();
        try{m.postMessageAsync((s,r,c)->{throw new AssertionError("Missing helper callback");},request(clones,null));throw new AssertionError("Missing helper accepted");}catch(NoClassDefFoundError expected){}
        final CountDownLatch acquired=new CountDownLatch(1);Thread probe=new Thread(()->{synchronized(q){acquired.countDown();}});probe.setDaemon(true);probe.start();await(acquired);probe.join(5000);check(q.isEmpty()&&clones.get()==1,"Missing helper queued or hid clone");
        System.out.println("stopped_post missing_helper NoClassDefFoundError=true monitor_released=true queue=0");
    }
    public static void main(String[] args)throws Exception{
        check(args.length==4&&Arrays.asList("async","sync","worker","concurrent","edt","null-clone","throwing","boundary","boundary-unsafe","missing-helper").contains(args[0]),"Unknown fixture mode");OfflineGuard.install();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.ERROR);
        check(new java.io.File(CommunicationsManager.class.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile().equals(new java.io.File(args[2]).getCanonicalFile()),"Manager CodeSource differs");
        java.io.InputStream in=CommunicationsManager.class.getResourceAsStream("/com/apple/xsr/net/CommunicationsManager.class");java.security.MessageDigest hash=java.security.MessageDigest.getInstance("SHA-256");try{byte[] bytes=new byte[4096];for(int n;(n=in.read(bytes))!=-1;)hash.update(bytes,0,n);}finally{in.close();}StringBuilder hex=new StringBuilder();for(byte b:hash.digest())hex.append(String.format(java.util.Locale.ROOT,"%02x",b&255));check(hex.toString().equals(args[3]),"Manager class hash differs");
        boolean fixed=args[1].equals("fixed");check(fixed||args[1].equals("legacy"),"Unknown policy");
        switch(args[0]){case "async":async(fixed);break;case "sync":sync(fixed);break;case "worker":worker();break;case "concurrent":concurrency();break;case "edt":edt();break;case "null-clone":nullAndClone();break;case "throwing":throwing();break;case "boundary":boundary(false);break;case "boundary-unsafe":boundary(true);break;case "missing-helper":missingHelper();break;default:throw new AssertionError("Mode");}
        OfflineGuard.assertUntouched();System.out.println("PASS stopped post observation; guarded_operations=0; no transport, profiles or production volumes");
    }
}
