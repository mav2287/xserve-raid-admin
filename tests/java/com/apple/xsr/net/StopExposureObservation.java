package com.apple.xsr.net;
import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.lang.reflect.*;
import java.util.LinkedList;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import sun.misc.Unsafe;
/** Memory-only forced stop between original stop read and exposure. */
public final class StopExposureObservation {
 public static final CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
 public static final java.util.concurrent.atomic.AtomicInteger reads=new java.util.concurrent.atomic.AtomicInteger();
 public static final AtomicReference<AssertionError> assertions=new AtomicReference<AssertionError>();
 public static void pause(CommunicationsManager manager)throws InterruptedException{
  boolean stopped=manager.isStopped();
  try{check(reads.incrementAndGet()==1,"Duplicate seam read");check(!stopped,"Premature stop");entered.countDown();check(release.await(5,TimeUnit.SECONDS),"Seam release absent");}catch(AssertionError failure){assertions.compareAndSet(null,failure);throw failure;}
 }
 private static void check(boolean v,String message){if(!v)throw new AssertionError(message);}
 private static Object get(Object o,String n)throws Exception{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);return f.get(o);}
 private static void set(Object o,String n,Object v)throws Exception{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);f.set(o,v);}
 public static void main(String[] args)throws Exception{
  boolean synchronous=args[0].startsWith("sync"),guarded=args[1].equals("guarded");
  OfflineGuard.install();fixture.FixtureIdentity.verify();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);compat.WorkerExit.prepare();
  Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);Unsafe u=(Unsafe)f.get(null);
  CommunicationsManager manager=(CommunicationsManager)u.allocateInstance(CommunicationsManager.class);LinkedList<Object> queue=new LinkedList<Object>();set(manager,"queue",queue);set(manager,"system",u.allocateInstance(RaidSystem.class));set(manager,"connected",true);set(manager,"thread",new Thread());set(manager,"connection",new AcpxConnection("192.0.2.1"));
  RequestMessage request=args[0].endsWith("mutating")?new AcpxMessageFactory().newSetTimeRequest(new java.util.Date(0)):new AcpxMessageFactory().newGetTimeRequest();
  AtomicReference<Response> answer=new AtomicReference<Response>();AtomicReference<Throwable> callerError=new AtomicReference<Throwable>(),workerError=new AtomicReference<Throwable>();
  AtomicReference<Thread> callbackThread=new AtomicReference<Thread>();final int[] callbacks={0};
  Thread caller=new Thread(()->{try{
   if(synchronous)answer.set(manager.postMessage(request));
   else manager.postMessageAsync((system,response,context)->{try{check(callbacks[0]++==0,"Duplicate callback");callbackThread.set(Thread.currentThread());answer.set(response);}catch(AssertionError failure){assertions.compareAndSet(null,failure);throw failure;}},request,null);
  }catch(Throwable failure){callerError.set(failure);}},"fixture-stop-admission-caller");caller.setDaemon(true);caller.start();
  long end=System.nanoTime()+5000000000L;boolean queued=false;
  while(!queued&&System.nanoTime()<end){synchronized(queue){queued=queue.size()==1&&(!synchronous||caller.getState()==Thread.State.WAITING);}if(!queued)Thread.sleep(2);}
  check(queued,"Queued wait absent");
  Thread worker=new Thread(()->{try{manager.run();}catch(Throwable failure){workerError.set(failure);}},"fixture-stop-admission-worker");worker.setDaemon(true);set(manager,"thread",worker);worker.start();
  check(entered.await(5,TimeUnit.SECONDS),"Original stop-read seam absent");Object txn=get(manager,"workerActiveTxn");check(txn!=null&&!(Boolean)get(manager,"workerActiveStarted")&&AcpxConnection.requests.isEmpty(),"Unstarted transaction absent");
  if(synchronous)check((Boolean)get(get(txn,"handler"),"claimed"),"Claim-before-pause absent");
  final java.util.concurrent.atomic.AtomicInteger queuedCallbacks=new java.util.concurrent.atomic.AtomicInteger();
  if(args[0].endsWith("queue"))for(int n=0;n<2;n++)manager.postMessageAsync((system,r,context)->{try{check(r.getResultCode()==-102&&r.getException() instanceof CommShutdownException&&Thread.currentThread()==worker,"Queued shutdown differs");queuedCallbacks.incrementAndGet();}catch(AssertionError failure){assertions.compareAndSet(null,failure);throw failure;}},new AcpxMessageFactory().newGetTimeRequest());
  if(args[0].equals("sync-interrupted")){caller.interrupt();long until=System.nanoTime()+5000000000L;while((caller.isInterrupted()||caller.getState()!=Thread.State.WAITING)&&System.nanoTime()<until)Thread.sleep(2);check(!caller.isInterrupted()&&caller.getState()==Thread.State.WAITING,"Claimed interrupted caller did not resume wait");}
  if(args[0].endsWith("flag"))set(manager,"connectionFailureSent",true);
  manager.shutdown();check(manager.isStopped(),"Stop absent");release.countDown();worker.join(5000);caller.join(5000);
  if(assertions.get()!=null)throw assertions.get();
  check(!worker.isAlive()&&!caller.isAlive()&&(callerError.get()==null||(synchronous&&guarded&&callerError.get() instanceof CommShutdownException))&&workerError.get()==null&&queue.isEmpty()&&!manager.isConnected(),"Completion differs");
  check(reads.get()==1,"Stop read count differs");
  Response response=synchronous?(Response)get(get(txn,"handler"),"response"):answer.get();check(response!=null,"Response absent");
  if(guarded){check(response.getException().getStackTrace()[0].getClassName().equals("com.apple.xsr.net.CommunicationsManager")&&response.getException().getStackTrace()[0].getMethodName().equals("dispatchLoop"),"Terminal wrapper false positive");if(synchronous)check((Boolean)get(get(txn,"handler"),"claimed")&&(Boolean)get(get(txn,"handler"),"handled"),"Sender claim/handling absent");}
  if(guarded)check((!synchronous||callerError.get()==response.getException())&&response.getResultCode()==-102&&response.getException() instanceof CommShutdownException&&AcpxConnection.sends==0&&AcpxConnection.requests.isEmpty()&&AcpxConnection.bodies.isEmpty(),"Guard failed to prevent send");
  else check(response.getResultCode()==0&&AcpxConnection.sends==1&&AcpxConnection.requests.size()==1&&AcpxConnection.bodies.size()==1,"Legacy unsafe control absent");
  if(!synchronous)check(callbacks[0]==1&&callbackThread.get()==worker,"Original callback thread differs");
  check(queuedCallbacks.get()==(args[0].endsWith("queue")?2:0),"Queued callback count differs");
  OfflineGuard.assertUntouched();System.out.println("PASS stop-exposure "+args[0]+" "+args[1]+" attempts="+AcpxConnection.requests.size()+" memory only; forbidden_attempts=0");
 }
}
