package com.apple.xsr.net;

import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.io.ByteArrayOutputStream;
import java.lang.reflect.Field;
import java.net.ConnectException;
import java.util.Arrays;
import java.util.LinkedList;
import sun.misc.Unsafe;

/** Source characterization only: real Manager, test-only constructor/transport stub. */
public final class ConnectFailureObservation {
    public static final class FakeSystem extends RaidSystem {
        boolean dual;
        boolean noHost;
        volatile int enabled;
        private FakeSystem(){super("fixture");throw new AssertionError("Constructor must not run");}
        @Override public String getPrimaryHostAddress(){return noHost?null:"192.0.2.1";}
        @Override public String getSecondaryHostAddress(){return dual?"192.0.2.2":null;}
        @Override public String getName(){return "fixture";}
        @Override public void setHostAddress(String address){}
        @Override public void setPollingEnabled(boolean value){if(value)enabled++;}
        @Override public void setUserMessageIndex(int value){}
    }
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    private static Unsafe unsafe()throws Exception {Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);return (Unsafe)f.get(null);}
    private static void set(CommunicationsManager manager,String name,Object value)throws Exception {Field f=CommunicationsManager.class.getDeclaredField(name);f.setAccessible(true);f.set(manager,value);}
    private static java.io.File source(Class<?> cls)throws Exception{return new java.io.File(cls.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile();}
    private static String classHash(Class<?> cls)throws Exception {
        java.security.MessageDigest digest=java.security.MessageDigest.getInstance("SHA-256");
        java.io.InputStream in=cls.getResourceAsStream("/"+cls.getName().replace('.','/')+".class");check(in!=null,"Class resource missing");
        try{byte[] bytes=new byte[4096];for(int n;(n=in.read(bytes))!=-1;)digest.update(bytes,0,n);}finally{in.close();}
        StringBuilder hex=new StringBuilder();for(byte value:digest.digest())hex.append(String.format(java.util.Locale.ROOT,"%02x",value&255));return hex.toString();
    }
    public static void main(String[] args)throws Exception {
        check(args.length==6&&Arrays.asList("single","dual","nohost","nohost-null","nohost-throw","single-null","verify-nohost","single-async","dual-async","single-async-throw").contains(args[0]),"Unknown fixture mode");check(Arrays.asList("legacy","terminal","late-stop").contains(args[5]),"Unknown policy mode");final boolean terminal=args[5].equals("terminal");OfflineGuard.install();
        org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        check(source(AcpxConnection.class).equals(new java.io.File(args[1]).getCanonicalFile()),"Stub CodeSource differs");
        check(source(CommunicationsManager.class).equals(new java.io.File(args[2]).getCanonicalFile()),"Manager CodeSource differs");
        check(classHash(CommunicationsManager.class).equals(args[3]),"Manager resource hash differs");
        if(!args[4].equals("-")){Class<?> recovery=Class.forName("compat.RejectionRecovery");check(source(recovery).equals(new java.io.File(args[2]).getCanonicalFile())&&classHash(recovery).equals(args[4]),"Recovery CodeSource/resource differs");}
        if(args[0].contains("-async")){async(args[0],args[5]);return;}
        if(args[0].equals("verify-nohost")){verifyNoHost();return;}
        if(args[0].startsWith("nohost")||args[0].equals("single-null")){extra(args[0],terminal);return;}
        FakeSystem system=(FakeSystem)unsafe().allocateInstance(FakeSystem.class);system.dual=args[0].equals("dual");
        CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);set(manager,"queue",new LinkedList<Object>());set(manager,"system",system);
        AcpxConnection.failures=system.dual?2:1;AcpxConnection.constructors=0;AcpxConnection.closes=0;AcpxConnection.lastFailure=null;AcpxConnection.onSend=new Runnable(){public void run(){manager.shutdown();}};AcpxConnection.bodies.clear();AcpxConnection.requests.clear();final Throwable[] escaped={null};
        Thread worker=new Thread(new Runnable(){public void run(){try{manager.run();}catch(Throwable error){escaped[0]=error;}}},"fixture-connect-failure-worker");worker.setDaemon(true);set(manager,"thread",worker);
        final RequestMessage request=new AcpxMessageFactory().newRestartSystemRequest();final ConnectException[] reported={null};final Throwable[] callerError={null};
        Thread caller=new Thread(new Runnable(){public void run(){try{manager.postMessage(request);callerError[0]=new AssertionError("Initial connection failure not reported");}catch(ConnectException expected){reported[0]=expected;}catch(Throwable error){callerError[0]=error;}}},"fixture-connect-failure-caller");caller.setDaemon(true);
        caller.start();RequestMessage held=null;long queueEnd=System.nanoTime()+5000000000L;
        Field qf=CommunicationsManager.class.getDeclaredField("queue");qf.setAccessible(true);LinkedList queue=(LinkedList)qf.get(manager);
        while(held==null&&System.nanoTime()<queueEnd){synchronized(queue){if(queue.size()==1){Object transaction=queue.getFirst();for(Field field:transaction.getClass().getDeclaredFields())if(field.getType()==RequestMessage.class){check(held==null,"Multiple request fields");field.setAccessible(true);held=(RequestMessage)field.get(transaction);}}}if(held==null)Thread.sleep(5);}
        try{
            check(held!=null,"Held transaction not captured");worker.start();caller.join(15000);
            check(!caller.isAlive()&&callerError[0]==null&&reported[0]!=null,"Initial connection failure not reported");
            ConnectException expected=reported[0];check(expected.getClass()==ConnectException.class&&"Synthetic connection failure".equals(expected.getMessage())&&expected.getCause()==null&&expected!=AcpxConnection.lastFailure,"Connection exception changed");
            check(manager.isStopped()==terminal,"Reported connection failure stop policy differs");
            long end=System.nanoTime()+30000000000L;
            while(!terminal&&AcpxConnection.bodies.isEmpty()&&worker.isAlive()&&System.nanoTime()<end)Thread.sleep(5);
        }finally{worker.join(2000);caller.join(2000);check(!worker.isAlive()&&!caller.isAlive(),"Fixture worker cleanup failed");OfflineGuard.assertUntouched();}
        check(escaped[0]==null&&AcpxConnection.constructors==AcpxConnection.failures+(terminal?0:1)&&AcpxConnection.bodies.size()==(terminal?0:1),"Original failed-call continuation missing");
        if(!terminal)check(AcpxConnection.requests.size()==1&&AcpxConnection.requests.get(0)==held,"Held request identity changed");
        else check(AcpxConnection.requests.isEmpty()&&AcpxConnection.closes==0,"Stopped initial connect sent or closed a nonexistent connection");
        if(!terminal){ByteArrayOutputStream body=new ByteArrayOutputStream();request.writeTo(body);check(Arrays.equals(body.toByteArray(),AcpxConnection.bodies.get(0)),"Held request body changed");}
        check(system.enabled==(terminal?0:1),"Polling enable count differs");
        System.out.println("connect_failure "+args[0]+" reported=ConnectException then_sent="+(terminal?0:1)+" constructors="+AcpxConnection.constructors+" "+(terminal?"stopped=true polling_enable_calls=0":"held_request_identity=true held_body_equal=true polling_enable_calls=1"));
        System.out.println("PASS constructor-stub characterization; guarded_operations=0; production_transport=unqualified");
    }
    private static void extra(final String mode,boolean terminal)throws Exception {
        check(terminal,"Additional cases require terminal policy");
        FakeSystem system=(FakeSystem)unsafe().allocateInstance(FakeSystem.class);system.noHost=mode.startsWith("nohost");
        final CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);set(manager,"queue",new LinkedList<Object>());set(manager,"system",system);set(manager,"thread",Thread.currentThread());
        AcpxConnection.failures=system.noHost?0:1;AcpxConnection.constructors=0;AcpxConnection.closes=0;AcpxConnection.bodies.clear();AcpxConnection.requests.clear();AcpxConnection.onSend=new Runnable(){public void run(){manager.shutdown();}};
        final int[] connects={0},commands={0};final Object context=new Object();final IllegalStateException callbackFailure=new IllegalStateException("Synthetic callback failure");
        CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem sy,Response response,Object seen){
            if(response.getType()==Response.TYPE_CONNECT){
                check(connects[0]++==0&&response.getResultCode()==-101&&manager.isStopped()&&!manager.isConnected()&&seen==null,"Connect notice not stopped before callback");
                try{manager.postMessage(new AcpxMessageFactory().newRestartSystemRequest());throw new AssertionError("Stopped callback sync accepted");}catch(CommShutdownException expected){}catch(java.io.IOException unexpected){throw new AssertionError("Wrong stopped sync exception");}
                if(mode.equals("nohost-throw"))throw callbackFailure;
            }else{check(response.getResultCode()==-102&&manager.isStopped(),"Queued response not stopped");if(seen==context)check(response.getException()==callbackFailure,"Callback exception identity changed");else check(response.getException() instanceof CommShutdownException,"Queued error changed");commands[0]++;}
        }};
        AcpxMessageFactory factory=new AcpxMessageFactory();
        manager.postMessageAsync(mode.equals("nohost-null")||mode.equals("single-null")?null:handler,factory.newGetStatusRequest(),context);
        if(!mode.equals("single-null")){manager.postMessageAsync(handler,factory.newRestartSystemRequest(),new Object());manager.postMessageAsync(null,factory.newRestartSystemRequest());}
        manager.run();
        if(mode.equals("single-null")){
            check(connects[0]==0&&commands[0]==0&&AcpxConnection.constructors==2&&AcpxConnection.bodies.size()==1&&system.enabled==1,"Null-handler retry changed");
            System.out.println("connect_failure single-null unpublished_failure=true constructors=2 sends=1 retry_preserved=true");
        }else{
            check(manager.isStopped()&&AcpxConnection.constructors==0&&AcpxConnection.bodies.isEmpty()&&AcpxConnection.closes==0&&connects[0]==(mode.equals("nohost-null")?0:1)&&commands[0]==(mode.equals("nohost-throw")?2:1),"No-host continuation escaped");
            manager.postMessageAsync(handler,factory.newRestartSystemRequest());Field q=CommunicationsManager.class.getDeclaredField("queue");q.setAccessible(true);check(((LinkedList)q.get(manager)).size()==1,"Late async residual changed");
            System.out.println("connect_failure "+mode+" constructors=0 sends=0 connects="+connects[0]+" commands="+commands[0]+" stopped=true late_async_stranded=1");
        }
        OfflineGuard.assertUntouched();System.out.println("PASS constructor-stub terminal extras; guarded_operations=0; production_transport=unqualified");
    }

    private static void verifyNoHost()throws Exception {
        FakeSystem system=(FakeSystem)unsafe().allocateInstance(FakeSystem.class);system.noHost=true;
        final CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);set(manager,"queue",new LinkedList<Object>());set(manager,"system",system);set(manager,"thread",Thread.currentThread());
        final int[] noticed={0};AcpxConnection.constructors=0;
        manager.postMessageAsync(new CommunicationHandler(){public void handleResponse(RaidSystem sy,Response response,Object context){if(response.getType()==Response.TYPE_CONNECT){check(response.getResultCode()==-101&&!manager.isStopped(),"Bypass not observed before callback");noticed[0]++;manager.shutdown();}else check(noticed[0]==1&&response.getResultCode()==-102&&manager.isStopped(),"Bypass local cleanup response differs");}},new AcpxMessageFactory().newRestartSystemRequest());
        manager.run();check(noticed[0]==1&&manager.isStopped()&&AcpxConnection.constructors==0,"No-host semantic negative control differs");OfflineGuard.assertUntouched();
        System.out.println("PASS verified no-host bypass reports before stop; guarded_operations=0");
    }

    private static void async(final String mode,final String policy)throws Exception {
        final boolean late=policy.equals("late-stop"),throwsCallback=mode.endsWith("-throw");check(late||policy.equals("terminal"),"Unknown async policy");
        FakeSystem system=(FakeSystem)unsafe().allocateInstance(FakeSystem.class);system.dual=mode.startsWith("dual-");
        final CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);set(manager,"queue",new LinkedList<Object>());set(manager,"system",system);set(manager,"thread",Thread.currentThread());
        AcpxConnection.failures=system.dual?2:1;AcpxConnection.constructors=0;AcpxConnection.closes=0;AcpxConnection.bodies.clear();AcpxConnection.requests.clear();AcpxConnection.onSend=null;
        final int[] connects={0},commands={0};final Object context=new Object();final IllegalStateException failure=new IllegalStateException("Synthetic reported callback failure");
        CommunicationHandler handler=new CommunicationHandler(){public void handleResponse(RaidSystem sy,Response response,Object seen){
            if(response.getType()==Response.TYPE_CONNECT){
                check(connects[0]++==0&&response.getResultCode()==-101&&seen==null&&!manager.isConnected()&&manager.isStopped()==!late,"Reported callback stop ordering differs");
                Exception reported=response.getException();check(reported!=AcpxConnection.lastFailure&&reported.getClass()==ConnectException.class&&"Synthetic connection failure".equals(reported.getMessage())&&reported.getCause()==null,"Async connect exception changed");
                if(!late)try{manager.postMessage(new AcpxMessageFactory().newRestartSystemRequest());throw new AssertionError("Stopped async callback sync accepted");}catch(CommShutdownException expected){}catch(java.io.IOException unexpected){throw new AssertionError("Wrong stopped async callback error");}
                if(throwsCallback)throw failure;
            }else{
                check(manager.isStopped()&&response.getResultCode()==-102,"Async queued operation not stopped");
                if(seen==context)check(throwsCallback&&response.getException()==failure,"Reported callback exception identity changed");else check(response.getException() instanceof CommShutdownException,"Async queued shutdown changed");commands[0]++;
            }
        }};
        AcpxMessageFactory factory=new AcpxMessageFactory();manager.postMessageAsync(handler,factory.newRestartSystemRequest(),context);manager.postMessageAsync(handler,factory.newRestartSystemRequest(),new Object());manager.postMessageAsync(null,factory.newRestartSystemRequest());manager.run();
        check(manager.isStopped()&&connects[0]==1&&commands[0]==(throwsCallback?2:1)&&AcpxConnection.constructors==AcpxConnection.failures&&AcpxConnection.bodies.isEmpty()&&AcpxConnection.requests.isEmpty()&&AcpxConnection.closes==0&&system.enabled==0,"Reported callback continuation escaped");OfflineGuard.assertUntouched();
        System.out.println("connect_failure "+mode+" stop_inside_callback="+!late+" constructors="+AcpxConnection.constructors+" sends=0 commands="+commands[0]+" exception_identity=true");
        System.out.println("PASS constructor-stub async ordering; guarded_operations=0; production_transport=unqualified");
    }

}
