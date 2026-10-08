package uiprobe;
/** Disposable headless process: no Apple classes, profiles or network. */
public final class AttachTarget {
 public static void main(String[]args)throws Exception{
  long deadline=System.nanoTime()+20000000000L;
  while(System.nanoTime()<deadline){try{
   Class<?> c=Class.forName("uiprobe.SelectionObserver");java.lang.reflect.Field f=c.getDeclaredField("started");f.setAccessible(true);f.setLong(null,System.nanoTime()-91000000000L);Thread.sleep(700);
   f=c.getDeclaredField("active");f.setAccessible(true);if(((java.util.concurrent.atomic.AtomicBoolean)f.get(null)).get())throw new AssertionError("still active");
   f=c.getDeclaredField("bindings");f.setAccessible(true);if(!((java.util.List<?>)f.get(null)).isEmpty())throw new AssertionError("bindings retained");
   System.out.println("PASS attached observer completed and detached");return;
  }catch(ClassNotFoundException notYet){Thread.sleep(100);}}
  throw new AssertionError("attach timeout");
 }
}
