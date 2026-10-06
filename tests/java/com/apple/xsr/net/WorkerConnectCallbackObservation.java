package com.apple.xsr.net;
import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.lang.reflect.Field;
import java.util.LinkedList;
import javax.swing.SwingUtilities;
import sun.misc.Unsafe;
public final class WorkerConnectCallbackObservation {
 private static final class HostileIOException extends java.io.IOException {
  HostileIOException(){}
  public String getMessage(){throw new AssertionError("Callback message rendered");}
  public String toString(){throw new AssertionError("Callback rendered");}
 }
 private static final class Capture extends org.apache.log4j.AppenderSkeleton {
  Capture(){}
  int probes,signals,nohost;boolean unexpected;
  protected void append(org.apache.log4j.spi.LoggingEvent event){
   if(!event.getLevel().isGreaterOrEqual(org.apache.log4j.Level.WARN))return;
   Object message=event.getMessage();
   if("FIXTURE_CONNECT_PROBE".equals(message))probes++;
   else if("RAID_ADMIN_WORKER_EXIT_FAILED".equals(message))signals++;
   else if("No valid host address for system \"fixture\"".equals(message))nohost++;
   else unexpected=true;
   if(event.getThrowableInformation()!=null)unexpected=true;
  }
  public boolean requiresLayout(){return false;}public void close(){}
 }
 public static final class FakeSystem extends RaidSystem {
  boolean noHost;int enabled;private FakeSystem(){super("fixture");throw new AssertionError("Must bypass constructor");}
  public String getPrimaryHostAddress(){return noHost?null:"192.0.2.1";}
  public String getSecondaryHostAddress(){return null;}
  public String getName(){return "fixture";}
  public void setHostAddress(String value){}
  public void setPollingEnabled(boolean value){if(value)enabled++;}
  public void setUserMessageIndex(int value){}
 }
 private static void check(boolean v,String message){if(!v)throw new AssertionError(message);}
 private static Unsafe unsafe()throws Exception{Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);return (Unsafe)f.get(null);}
 private static void set(Object o,String name,Object value)throws Exception{Field f=CommunicationsManager.class.getDeclaredField(name);f.setAccessible(true);f.set(o,value);}
 private static Object get(Object o,String name)throws Exception{Field f=CommunicationsManager.class.getDeclaredField(name);f.setAccessible(true);return f.get(o);}
 @SuppressWarnings("unchecked") private static <T extends Throwable>void sneaky(Throwable failure)throws T{throw (T)failure;}
 public static void main(String[] args)throws Exception{
  check(args.length==3,"Unknown connect callback mode");boolean fixed=args[0].equals("fixed"),nohost=args[1].equals("nohost"),fatal=args[2].equals("error");OfflineGuard.install();fixture.FixtureIdentity.verify();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.WARN);org.apache.log4j.Logger root=org.apache.log4j.Logger.getRootLogger();root.removeAllAppenders();root.setLevel(org.apache.log4j.Level.WARN);Capture capture=new Capture();root.addAppender(capture);root.warn("FIXTURE_CONNECT_PROBE");check(capture.probes==1&&!capture.unexpected,"Connect warning observer inactive");if(fixed)compat.WorkerExit.prepare();
  FakeSystem sys=(FakeSystem)unsafe().allocateInstance(FakeSystem.class);sys.noHost=nohost;CommunicationsManager m=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);set(m,"queue",new LinkedList<Object>());set(m,"system",sys);set(m,"thread",Thread.currentThread());AcpxConnection.failures=nohost?0:1;
  final Throwable failure=args[2].equals("hostile-io")?new HostileIOException():args[2].equals("interrupt")?new InterruptedException("Synthetic callback interruption"):args[2].equals("runtime")?new IllegalStateException("Synthetic callback failure"):args[2].equals("prefix-io")?new java.io.IOException("PropertyListException: synthetic callback failure"):args[2].equals("io")?new java.io.IOException("Synthetic callback failure"):args[2].equals("null-io")?new java.io.IOException((String)null):args[2].equals("malformed")?new sun.io.MalformedInputException():new AssertionError("Synthetic callback failure");
  final int[] connect={0},duplicate={0},follow={0};final Object first=new Object(),next=new Object();
  CommunicationHandler h=(system,response,context)->{if(response.getType()==Response.TYPE_CONNECT){check(m.isStopped()&&response.getResultCode()==-101&&context==null,"Connect callback stop ordering differs");connect[0]++;WorkerConnectCallbackObservation.<RuntimeException>sneaky(failure);}else if(context==first){duplicate[0]++;}else{check(context==next&&response.getResultCode()==-102&&response.getException().getClass()==CommShutdownException.class,"Follow-on shutdown differs");follow[0]++;}};
  m.postMessageAsync(h,new AcpxMessageFactory().newGetStatusRequest(),first);m.postMessageAsync(h,new AcpxMessageFactory().newGetTimeRequest(),next);Throwable escaped=null;try{m.run();}catch(Throwable error){escaped=error;}
  SwingUtilities.invokeAndWait(()->{});
  check(connect[0]==1&&duplicate[0]==(!fixed&&!fatal?1:0)&&follow[0]==(!fixed&&fatal?0:1),"Callback attempt ownership differs");check((fixed||!fatal)?escaped==null:escaped==failure,"Worker throwable policy differs");
  LinkedList<?> queue=(LinkedList<?>)get(m,"queue");synchronized(queue){check(queue.size()==(!fixed&&fatal?1:0),"Pending queue differs");}
  check(m.isStopped()&&AcpxConnection.constructors==(nohost?0:1)&&AcpxConnection.requests.isEmpty()&&AcpxConnection.bodies.isEmpty()&&sys.enabled==0,"Connect failure sent/reconnected/enabled polling");if(fixed)check(capture.probes==1&&capture.signals==1&&capture.nohost==(nohost?1:0)&&!capture.unexpected,"Connect callback logging boundary differs");OfflineGuard.assertUntouched();
  System.out.println("worker_connect "+args[1]+" "+args[2]+" fixed="+fixed+" connect_attempts=1 duplicate="+duplicate[0]+" follow="+follow[0]+" sends=0");System.out.println("PASS memory connection callback experiment; guarded_operations=0");
 }
}
