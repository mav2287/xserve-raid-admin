package com.apple.xsr.net;

import fixture.OfflineGuard;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.management.ThreadMXBean;
import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import sun.misc.Unsafe;

/** Real worker and shutdown, no Manager constructor, requests or transport. */
public final class StopLockObservation {
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    private static Unsafe unsafe()throws Exception {Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);return (Unsafe)f.get(null);}
    private static void set(CommunicationsManager m,String name,Object value)throws Exception {Field f=CommunicationsManager.class.getDeclaredField(name);f.setAccessible(true);f.set(m,value);}
    private static String classHash()throws Exception {
        java.security.MessageDigest digest=java.security.MessageDigest.getInstance("SHA-256");java.io.InputStream in=CommunicationsManager.class.getResourceAsStream("/com/apple/xsr/net/CommunicationsManager.class");check(in!=null,"Class resource missing");
        try{byte[] bytes=new byte[4096];for(int n;(n=in.read(bytes))!=-1;)digest.update(bytes,0,n);}finally{in.close();}
        StringBuilder hex=new StringBuilder();for(byte b:digest.digest())hex.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return hex.toString();
    }
    public static void main(String[] args)throws Exception {
        check(args.length==4&&Arrays.asList("pc18","pc45").contains(args[0])&&Arrays.asList("safe","deadlock").contains(args[1]),"Unknown fixture mode");final boolean preStopped=args[0].equals("pc45"),deadlock=args[1].equals("deadlock");OfflineGuard.install();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
        check(new java.io.File(CommunicationsManager.class.getProtectionDomain().getCodeSource().getLocation().toURI()).getCanonicalFile().equals(new java.io.File(args[2]).getCanonicalFile())&&classHash().equals(args[3]),"Worker CodeSource/hash differs");
        final CommunicationsManager manager=(CommunicationsManager)unsafe().allocateInstance(CommunicationsManager.class);final LinkedList<Object> queue=new LinkedList<Object>();set(manager,"queue",queue);
        final CountDownLatch locked=new CountDownLatch(1),release=new CountDownLatch(1);final AtomicReference<Throwable> escaped=new AtomicReference<Throwable>();
        Thread holder=new Thread(new Runnable(){public void run(){try{synchronized(manager){if(preStopped)manager.shutdown();locked.countDown();check(release.await(8,TimeUnit.SECONDS),"Holder release missing");manager.shutdown();}}catch(Throwable error){escaped.set(error);}}},"fixture-stop-lock-holder");holder.setDaemon(true);
        Thread worker=new Thread(new Runnable(){public void run(){try{manager.run();}catch(Throwable error){escaped.set(error);}}},"fixture-stop-lock-worker");worker.setDaemon(true);set(manager,"thread",worker);
        ThreadMXBean bean=ManagementFactory.getThreadMXBean();check(bean.isSynchronizerUsageSupported(),"Deadlock monitor unsupported");
        try{
            holder.start();check(locked.await(5,TimeUnit.SECONDS),"Manager lock not held");worker.start();long end=System.nanoTime()+5000000000L;boolean witnessed=false;
            while(System.nanoTime()<end&&!witnessed){
                ThreadInfo info=bean.getThreadInfo(worker.getId(),0);
                if(deadlock)witnessed=info!=null&&info.getThreadState()==Thread.State.BLOCKED&&info.getLockOwnerId()==holder.getId()&&info.getLockInfo()!=null&&info.getLockInfo().getIdentityHashCode()==System.identityHashCode(manager);
                else if(preStopped)witnessed=worker.getState()==Thread.State.TERMINATED;
                else witnessed=info!=null&&info.getThreadState()==Thread.State.WAITING&&info.getLockOwnerId()==-1&&info.getLockInfo()!=null&&info.getLockInfo().getIdentityHashCode()==System.identityHashCode(queue);
                if(!witnessed)Thread.sleep(2);
            }
            check(witnessed&&escaped.get()==null,"Expected worker lock state not observed");release.countDown();
            if(deadlock){
                long[] wanted={worker.getId(),holder.getId()};Arrays.sort(wanted);boolean pair=false;end=System.nanoTime()+5000000000L;
                while(System.nanoTime()<end&&!pair){long[] ids=bean.findDeadlockedThreads();if(ids!=null){Arrays.sort(ids);pair=Arrays.equals(ids,wanted);}if(!pair)Thread.sleep(2);}
                check(pair&&escaped.get()==null,"Exact deadlock pair not observed");
                ThreadInfo holderInfo=bean.getThreadInfo(holder.getId(),0),workerInfo=bean.getThreadInfo(worker.getId(),0);
                check(holderInfo!=null&&holderInfo.getThreadState()==Thread.State.BLOCKED&&holderInfo.getLockOwnerId()==worker.getId()&&holderInfo.getLockInfo()!=null&&holderInfo.getLockInfo().getIdentityHashCode()==System.identityHashCode(queue)&&workerInfo!=null&&workerInfo.getThreadState()==Thread.State.BLOCKED&&workerInfo.getLockOwnerId()==holder.getId()&&workerInfo.getLockInfo()!=null&&workerInfo.getLockInfo().getIdentityHashCode()==System.identityHashCode(manager),"Deadlock owners or monitor identities differ");
            }else{holder.join(5000);worker.join(5000);check(!holder.isAlive()&&!worker.isAlive()&&escaped.get()==null&&manager.isStopped()&&!manager.isConnected()&&queue.isEmpty(),"Safe shutdown did not complete");}
            OfflineGuard.assertUntouched();System.out.println("stop_lock "+args[0]+" outcome="+(deadlock?"exact-deadlock-pair":"completed")+" guarded_operations=0; requests=0");System.out.println("PASS stop lock observation; no profiles, sockets or production transport");
        }finally{release.countDown();}
    }
}
