package uiprobe;
import fixture.OfflineGuard;
import com.apple.xsr.DriveSelectionPanel;
import java.awt.Component;
import java.awt.image.BufferedImage;
import java.beans.PropertyChangeListener;
import java.lang.reflect.*;
import java.util.*;
import javax.swing.*;

/** Headless numeric snapshot and fault containment; no app Main, real profiles or controller. */
public final class ObserverObservation {
 static class RejectLabel extends JLabel {boolean armed;public void addPropertyChangeListener(String name,PropertyChangeListener listener){if(armed&&"icon".equals(name))throw new IllegalStateException("synthetic bind fault");super.addPropertyChangeListener(name,listener);}}
 static DriveSelectionPanel panel;static JLabel[] icons;static Object binding;
 static Field f(Class<?> c,String name)throws Exception{Field f=c.getDeclaredField(name);f.setAccessible(true);return f;}
 static void put(String name,Object value)throws Exception{f(DriveSelectionPanel.class,name).set(panel,value);}
 static void check(boolean ok,String code){if(!ok)throw new AssertionError(code);}
 static void invoke(String name,Class<?>[] types,Object...args)throws Exception{Method m=SelectionObserver.class.getDeclaredMethod(name,types);m.setAccessible(true);m.invoke(null,args);}
 static ImageIcon icon(int rgb){BufferedImage image=new BufferedImage(18,68,BufferedImage.TYPE_INT_RGB);java.awt.Graphics g=image.getGraphics();g.setColor(new java.awt.Color(rgb));g.fillRect(0,0,18,68);g.dispose();return new ImageIcon(image);}
 public static void main(String[]args)throws Exception{
  OfflineGuard.install();com.apple.xsr.Resources.load();
  sun.misc.Unsafe unsafe=(sun.misc.Unsafe)f(sun.misc.Unsafe.class,"theUnsafe").get(null);panel=(DriveSelectionPanel)unsafe.allocateInstance(DriveSelectionPanel.class);f(Component.class,"objectLock").set(panel,new Object());
  final int[] states=new int[14],members=new int[14];Arrays.fill(states,-2);for(int n=0;n<14;n++)members[n]=n<7?1:2;
  icons=new JLabel[14];for(int n=0;n<14;n++)icons[n]=new JLabel(icon(0x808080));
  put("driveStates",states);put("driveArrays",members);put("driveIcon",icons);put("selectionMode",4);put("arrayIndex",-10);put("driveIndex",3);
  final Throwable[] failure=new Throwable[1];SwingUtilities.invokeAndWait(new Runnable(){public void run(){try{
   invoke("bind",new Class<?>[]{Component.class},panel);put("arrayIndex",1);
   for(int n=0;n<14;n++)icons[n].setIcon(icon(n<7?0x3366ff:0x808080));
  }catch(Throwable x){failure[0]=x;}}});SwingUtilities.invokeAndWait(new Runnable(){public void run(){}});check(failure[0]==null,"setup");
  java.util.List<?> lines=(java.util.List<?>)f(SelectionObserver.class,"lines").get(null);String last=lines.get(lines.size()-1).toString();
  check(last.contains("expected_mask=127")&&last.contains("ready_mask=16383")&&last.contains("generations=1,1,1,1,1,1,1,1,1,1,1,1,1,1,")&&last.contains("off_edt=0,0,0,0,0,0,0,0,0,0,0,0,0,0,"),"numeric-snapshot");
  java.util.List<?> bindings=(java.util.List<?>)f(SelectionObserver.class,"bindings").get(null);binding=bindings.get(0);f(binding.getClass(),"generations").set(binding,null);
  final int[] updates={0};SwingUtilities.invokeAndWait(new Runnable(){public void run(){for(int n=0;n<14;n++){icons[n].setIcon(icon(0x123456));updates[0]++;}}});
  check(updates[0]==14,"probe-fault-contained");check(((java.util.concurrent.atomic.AtomicBoolean)f(SelectionObserver.class,"failed").get(null)).get(),"fault-recorded");
  SwingUtilities.invokeAndWait(new Runnable(){public void run(){try{invoke("remove",new Class<?>[]{});}catch(Throwable x){failure[0]=x;}}});
  check(failure[0]==null,"remove-no-throw");
  for(JLabel label:icons)check(label.getPropertyChangeListeners("icon").length==0,"listener-cleanup");check(bindings.isEmpty(),"bindings-cleanup");
  ((java.util.concurrent.atomic.AtomicBoolean)f(SelectionObserver.class,"active").get(null)).set(true);
  JLabel saved=icons[4];icons[4]=null;invoke("bind",new Class<?>[]{Component.class},panel);check(bindings.isEmpty(),"null-label-prevalidation");for(JLabel label:icons)if(label!=null)check(label.getPropertyChangeListeners("icon").length==0,"null-bind-cleanup");
  RejectLabel reject=new RejectLabel();reject.armed=true;icons[4]=reject;invoke("bind",new Class<?>[]{Component.class},panel);check(bindings.size()==1,"partial-bind-tracked");invoke("remove",new Class<?>[]{});for(JLabel label:icons)check(label.getPropertyChangeListeners("icon").length==0,"partial-bind-cleanup");check(bindings.isEmpty(),"partial-binding-cleared");icons[4]=saved;
  Method record=SelectionObserver.class.getDeclaredMethod("record",String.class);record.setAccessible(true);for(int n=0;n<4200;n++)record.invoke(null,"SYNTHETIC n="+n);invoke("remove",new Class<?>[]{});check(lines.size()==4096,"buffer-limit");String end=(String)f(SelectionObserver.class,"endLine").get(null);check(end.startsWith("END failed=1 dropped=")&&end.endsWith("remaining_listeners=0"),"end-retained");
  final PropertyChangeListener throwing=new PropertyChangeListener(){public void propertyChange(java.beans.PropertyChangeEvent e){throw new IllegalStateException("synthetic negative");}};icons[0].addPropertyChangeListener("icon",throwing);
  int changed=0;try{for(int n=0;n<14;n++){icons[n].setIcon(icon(0xabcdef));changed++;}}catch(IllegalStateException expected){}finally{icons[0].removePropertyChangeListener("icon",throwing);}
  check(changed==0,"negative-control");check(Arrays.equals(states,new int[]{-2,-2,-2,-2,-2,-2,-2,-2,-2,-2,-2,-2,-2,-2})&&members[0]==1&&members[13]==2,"model-unchanged");OfflineGuard.assertUntouched();
  System.out.println("PASS numeric UI snapshot; observer fault preserves14updates; throwing-listener negative fails; null/partial-bind observers removed; forbidden_operations=0");
 }
}
