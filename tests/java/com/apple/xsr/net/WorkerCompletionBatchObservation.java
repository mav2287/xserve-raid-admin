package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.lang.reflect.Field;
import java.util.LinkedList;
import java.util.concurrent.atomic.AtomicReference;
import javax.swing.SwingUtilities;
import org.apache.log4j.AppenderSkeleton;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import org.apache.log4j.spi.LoggingEvent;
import sun.misc.Unsafe;

/** Terminal drain ordering and hostile callbacks; memory shadow, no transport. */
public final class WorkerCompletionBatchObservation {
 private static final class Fault extends Error {
  Fault(){}
  public String getMessage(){throw new AssertionError("Fault rendered");}
  public String toString(){throw new AssertionError("Fault rendered");}
 }
 private static final class Capture extends AppenderSkeleton {
  Capture(){}
  volatile int probes,signals;volatile boolean unexpected;
  protected void append(LoggingEvent event){
   if(!event.getLevel().isGreaterOrEqual(Level.WARN))return;
   Object message=event.getMessage();
   if("FIXTURE_WORKER_PROBE".equals(message))probes++;
   else if("RAID_ADMIN_WORKER_EXIT_FAILED".equals(message))signals++;
   else unexpected=true;
   if(event.getThrowableInformation()!=null)unexpected=true;
  }
  public boolean requiresLayout(){return false;}public void close(){}
 }
 private static void check(boolean v,String message){if(!v)throw new AssertionError(message);}
 private static Object get(Object o,String name)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
 private static void set(Object o,String name,Object value)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);f.set(o,value);}
 public static void main(String[] args)throws Exception{
  check(args.length==0,"Unexpected batch mode");OfflineGuard.install();fixture.FixtureIdentity.verify();compat.WorkerExit.prepare();
  org.apache.log4j.LogManager.getLoggerRepository().setThreshold(Level.WARN);Logger root=Logger.getRootLogger();root.removeAllAppenders();root.setLevel(Level.WARN);Capture capture=new Capture();root.addAppender(capture);root.warn("FIXTURE_WORKER_PROBE");check(capture.probes==1&&!capture.unexpected,"Warning observer inactive");
  Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);Unsafe unsafe=(Unsafe)f.get(null);
  CommunicationsManager manager=(CommunicationsManager)unsafe.allocateInstance(CommunicationsManager.class);final LinkedList<Object> queue=new LinkedList<Object>();set(manager,"queue",queue);set(manager,"system",unsafe.allocateInstance(RaidSystem.class));set(manager,"thread",new Thread());set(manager,"connected",true);set(manager,"connection",new AcpxConnection("192.0.2.1"));
  final int[] calls={0,0,0},attempts={0};final Fault fault=new Fault();final java.util.concurrent.CountDownLatch entered=new java.util.concurrent.CountDownLatch(1),release=new java.util.concurrent.CountDownLatch(1);AcpxConnection.onSend=()->{attempts[0]++;entered.countDown();try{check(release.await(5,java.util.concurrent.TimeUnit.SECONDS),"Send release absent");}catch(InterruptedException failure){throw new AssertionError("Unexpected memory send interrupt");}throw fault;};
  for(int i=0;i<3;i++){
   final int index=i;
   manager.postMessageAsync((s,r,c)->{
    check(SwingUtilities.isEventDispatchThread()&&!Thread.holdsLock(manager)&&!Thread.holdsLock(queue),"Callback thread/lock differs");
    check(c==Integer.valueOf(index)&&r.getResultCode()==-102&&r.getException().getClass()==(index==0?compat.UntrustedResponseException.class:CommShutdownException.class),"Batch outcome differs");
    calls[index]++;if(index==1)throw fault;
   },new AcpxMessageFactory().newGetStatusRequest(),Integer.valueOf(i));
  }
  AtomicReference<Throwable> callerError=new AtomicReference<Throwable>(),workerError=new AtomicReference<Throwable>();
  Thread worker=new Thread(()->{try{manager.run();}catch(Throwable error){workerError.set(error);}},"fixture-batch-worker");worker.setDaemon(true);set(manager,"thread",worker);worker.start();check(entered.await(5,java.util.concurrent.TimeUnit.SECONDS),"Active send not witnessed");
  Thread caller=new Thread(()->{synchronized(manager){try{manager.postMessage(new AcpxMessageFactory().newGetTimeRequest());callerError.set(new AssertionError("Queued caller succeeded"));}catch(Throwable error){callerError.set(error);}}},"fixture-monitor-caller");caller.setDaemon(true);caller.start();
  long end=System.nanoTime()+5000000000L;boolean queued=false;
  while(System.nanoTime()<end&&!queued){synchronized(queue){queued=queue.size()==3&&caller.getState()==Thread.State.WAITING;}if(!queued)Thread.sleep(2);}
  check(queued,"Caller wait not witnessed");release.countDown();worker.join(5000);caller.join(5000);SwingUtilities.invokeAndWait(()->{});
  check(!worker.isAlive()&&!caller.isAlive()&&workerError.get()==null&&callerError.get()!=null&&callerError.get().getClass()==CommShutdownException.class,"Synchronous release/monitor ordering differs");
  check(manager.isStopped()&&!manager.isConnected()&&queue.isEmpty()&&calls[0]==1&&calls[1]==1&&calls[2]==1&&attempts[0]==1&&AcpxConnection.requests.isEmpty()&&AcpxConnection.closes==1,"Batch completion/replay/close differs");
  check(capture.probes==1&&capture.signals==2&&!capture.unexpected,"Fixed logging boundary differs");OfflineGuard.assertUntouched();
  System.out.println("PASS worker completion batch; sync_before_manager_lock=true async_edt=true callback_error_contained=true no_replay=true fixed_signals=2 guarded_operations=0");
 }
}
