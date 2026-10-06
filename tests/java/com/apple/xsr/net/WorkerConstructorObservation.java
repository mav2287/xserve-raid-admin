package com.apple.xsr.net;
import com.apple.xsr.som.RaidSystem;
import fixture.OfflineGuard;
import java.lang.reflect.Field;
import sun.misc.Unsafe;
public final class WorkerConstructorObservation {
 public static void main(String[] args)throws Exception{
  OfflineGuard.install();fixture.FixtureIdentity.verify();org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
  Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);Unsafe unsafe=(Unsafe)f.get(null);
  CommunicationsManager m=new CommunicationsManager((RaidSystem)unsafe.allocateInstance(RaidSystem.class));
  f=CommunicationsManager.class.getDeclaredField("thread");f.setAccessible(true);Thread t=(Thread)f.get(m);m.shutdown();t.join(5000);
  if(t.isAlive()||!m.isStopped()||m.isConnected())throw new AssertionError("Actual constructor worker termination differs");
  OfflineGuard.assertUntouched();System.out.println("PASS actual Manager constructor and local exit; guarded_operations=0");
 }
}
