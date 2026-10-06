package com.apple.xsr.net;
import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.lang.reflect.*;
import java.util.LinkedList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import sun.misc.Unsafe;
/** Development characterization only: stop after claim and before request serialization completes. */
public final class StopActiveObservation {
 private static void check(boolean v,String message){if(!v)throw new AssertionError(message);}
 private static Object get(Object o,String n)throws Exception{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);return f.get(o);}
 private static void set(Object o,String n,Object v)throws Exception{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);f.set(o,v);}
 public static void main(String[] args)throws Exception{
  boolean synchronous=args[0].equals("sync");AtomicReference<Thread> callbackThread=new AtomicReference<Thread>();final int[] callbacks={0};
  OfflineGuard.install();fixture.FixtureIdentity.verify();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);compat.WorkerExit.prepare();
  Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);Unsafe u=(Unsafe)f.get(null);
  CommunicationsManager manager=(CommunicationsManager)u.allocateInstance(CommunicationsManager.class);LinkedList<Object> queue=new LinkedList<Object>();set(manager,"queue",queue);set(manager,"system",u.allocateInstance(RaidSystem.class));set(manager,"connected",true);set(manager,"thread",new Thread());set(manager,"connection",new AcpxConnection("192.0.2.1"));
  CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);RequestMessage original=new AcpxMessageFactory().newGetTimeRequest();java.io.ByteArrayOutputStream expectedBody=new java.io.ByteArrayOutputStream();original.writeTo(expectedBody);final int[] clones={0},writes={0};AtomicReference<AssertionError> serializationAssertion=new AtomicReference<AssertionError>();
  RequestMessage request=(RequestMessage)Proxy.newProxyInstance(RequestMessage.class.getClassLoader(),new Class[]{RequestMessage.class},(proxy,method,values)->{
   if(method.getName().equals("clone")){clones[0]++;return proxy;}
   if(method.getName().equals("writeTo")){writes[0]++;entered.countDown();try{check(release.await(5,TimeUnit.SECONDS),"Serialization release absent");}catch(AssertionError failure){serializationAssertion.compareAndSet(null,failure);throw failure;}}
   try{return method.invoke(original,values);}catch(InvocationTargetException failure){throw failure.getCause();}
  });
  AtomicReference<Response> answer=new AtomicReference<Response>();AtomicReference<Throwable> callerError=new AtomicReference<Throwable>(),workerError=new AtomicReference<Throwable>();
  Thread caller=new Thread(()->{try{if(synchronous)answer.set(manager.postMessage(request));else manager.postMessageAsync((system,response,context)->{try{check(callbacks[0]++==0,"Duplicate active callback");callbackThread.set(Thread.currentThread());answer.set(response);}catch(AssertionError failure){serializationAssertion.compareAndSet(null,failure);throw failure;}},request);}catch(Throwable e){callerError.set(e);}},"fixture-stop-active-caller");caller.setDaemon(true);caller.start();
  Object sender=null;long end=System.nanoTime()+5000000000L;
  while(sender==null&&System.nanoTime()<end){synchronized(queue){if(queue.size()==1&&(!synchronous||caller.getState()==Thread.State.WAITING))sender=get(queue.getFirst(),"handler");}if(sender==null)Thread.sleep(2);}
  check(sender!=null,"Sender wait absent");
  Thread worker=new Thread(()->{try{manager.run();}catch(Throwable e){workerError.set(e);}},"fixture-stop-active-worker");worker.setDaemon(true);set(manager,"thread",worker);worker.start();
  check(entered.await(5,TimeUnit.SECONDS)&&(!synchronous||(Boolean)get(sender,"claimed"))&&AcpxConnection.requests.isEmpty()&&AcpxConnection.bodies.isEmpty(),"Active serialization claim absent");
  check((Boolean)get(manager,"workerActiveStarted")&&get(manager,"workerActiveTxn")!=null&&get(get(manager,"workerActiveTxn"),"handler")==sender,"Active exposure identity absent");
  manager.shutdown();check(manager.isStopped()&&worker.isAlive()&&(!synchronous||caller.getState()==Thread.State.WAITING)&&AcpxConnection.requests.isEmpty(),"Stop-before-release absent");release.countDown();worker.join(5000);caller.join(5000);
  if(serializationAssertion.get()!=null)throw serializationAssertion.get();
  check(!worker.isAlive()&&!caller.isAlive()&&callerError.get()==null&&workerError.get()==null&&manager.isStopped()&&!manager.isConnected()&&queue.isEmpty(),"Active completion differs");
  check(answer.get()!=null&&answer.get().getResultCode()==0&&(!synchronous||answer.get()==get(sender,"response"))&&clones[0]==(synchronous?2:1)&&writes[0]==1&&AcpxConnection.sends==1&&AcpxConnection.requests.size()==1&&AcpxConnection.bodies.size()==1&&java.util.Arrays.equals(expectedBody.toByteArray(),AcpxConnection.bodies.get(0)),"Active result/replay differs");if(!synchronous)check(callbacks[0]==1&&callbackThread.get()==worker,"Active async callback thread differs");OfflineGuard.assertUntouched();
  System.out.println("PASS stop-active "+args[0]+" characterization; claimed_before_serialization_completes=true stop_before_release=true attempts=1 real_reply_preserved=true no_replay=true forbidden_attempts=0");
 }
}
