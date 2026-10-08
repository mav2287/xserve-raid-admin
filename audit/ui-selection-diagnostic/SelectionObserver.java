package uiprobe;

import java.awt.*;
import java.awt.event.*;
import java.awt.image.BufferedImage;
import java.beans.*;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.Field;
import java.nio.file.*;
import java.nio.channels.FileChannel;
import java.nio.ByteBuffer;
import java.nio.file.attribute.*;
import java.util.*;
import java.util.concurrent.atomic.*;
import javax.swing.*;

/** Temporary numeric-only observation. No transformers, app commands, profile fields or UI actions. */
public final class SelectionObserver {
 private static final String VIEW="com.apple.xsr.SystemInfoPane", PANEL="com.apple.xsr.DriveSelectionPanel";
 private static final String[] FIELDS={"selectionMode","driveIndex","arrayIndex","driveArrays","driveStates","driveIcon","inDragSelect","selecting"};
 private static final AtomicBoolean installed=new AtomicBoolean(),failed=new AtomicBoolean(),queued=new AtomicBoolean(),active=new AtomicBoolean(true);
 private static final AtomicLong sequence=new AtomicLong(),firstClick=new AtomicLong();
 private static final java.util.List<String> lines=new ArrayList<String>();
 private static final java.util.List<Binding> bindings=new ArrayList<Binding>();
 private static volatile int dropped;
 private static volatile String endLine;
 private static AWTEventListener mouseListener;
 private static Path output;
 private static Object fileKey;
 private static FileChannel channel;
 private static int pendingSize;
 private static long started;
 private static class Binding {
  Component panel;JLabel[] icons;Field[] fields;PropertyChangeListener[] listeners;AtomicIntegerArray generations=new AtomicIntegerArray(14);AtomicIntegerArray offEdt=new AtomicIntegerArray(14);
 }
 private static void record(String value){try{synchronized(lines){if(lines.size()<4096)lines.add(sequence.incrementAndGet()+" "+System.currentTimeMillis()+" "+System.nanoTime()+" "+value);else dropped++;}}catch(Throwable ignored){failed.set(true);}}
 private static boolean inView(Component c){for(Component p=c;p!=null;p=p.getParent())if(VIEW.equals(p.getClass().getName()))return true;return false;}
 private static void find(Component c){if(PANEL.equals(c.getClass().getName())&&inView(c))bind(c);if(c instanceof Container)for(Component child:((Container)c).getComponents())find(child);}
 private static void bind(final Component panel){try{synchronized(bindings){if(!active.get())return;
  final Binding b=new Binding();b.panel=panel;b.fields=new Field[FIELDS.length];
  for(int n=0;n<FIELDS.length;n++){b.fields[n]=panel.getClass().getDeclaredField(FIELDS[n]);b.fields[n].setAccessible(true);}
  b.icons=((JLabel[])b.fields[5].get(panel)).clone();if(b.icons.length!=14)throw new IllegalArgumentException();
  b.listeners=new PropertyChangeListener[14];
  for(JLabel icon:b.icons)if(icon==null)throw new IllegalArgumentException();
  bindings.add(b);
  for(int n=0;n<14;n++){final int index=n;b.listeners[n]=new PropertyChangeListener(){public void propertyChange(PropertyChangeEvent e){try{
   if(!active.get())return;b.generations.incrementAndGet(index);if(!SwingUtilities.isEventDispatchThread())b.offEdt.incrementAndGet(index);schedule();
  }catch(Throwable ignored){failed.set(true);}}};b.icons[n].addPropertyChangeListener("icon",b.listeners[n]);}
  record("BIND panel="+System.identityHashCode(panel));snapshot(b);
 }}catch(Throwable ignored){failed.set(true);}}
 private static void schedule(){try{if(active.get()&&!failed.get()&&queued.compareAndSet(false,true))SwingUtilities.invokeLater(new Runnable(){public void run(){try{queued.set(false);if(active.get()){java.util.List<Binding> copy;synchronized(bindings){copy=new ArrayList<Binding>(bindings);}for(Binding b:copy)snapshot(b);}}catch(Throwable ignored){failed.set(true);}}});}catch(Throwable ignored){failed.set(true);}}
 private static void snapshot(Binding b){try{
  if(!active.get())return;JLabel[] current=(JLabel[])b.fields[5].get(b.panel);if(current.length!=14)throw new IllegalArgumentException();for(int n=0;n<14;n++)if(current[n]!=b.icons[n]){record("REPLACED panel="+System.identityHashCode(b.panel));failed.set(true);return;}
  int mode=b.fields[0].getInt(b.panel),drive=b.fields[1].getInt(b.panel),array=b.fields[2].getInt(b.panel);
  int[] members=((int[])b.fields[3].get(b.panel)).clone(),states=((int[])b.fields[4].get(b.panel)).clone();
  if(members.length!=14||states.length!=14)throw new IllegalArgumentException();
  int mask=0;for(int n=0;n<14;n++)if((mode==3&&n==drive)||(mode==4&&members[n]==array))mask|=1<<n;
  StringBuilder s=new StringBuilder("STATE panel=").append(System.identityHashCode(b.panel)).append(" mode=").append(mode).append(" drive=").append(drive).append(" array=").append(array).append(" expected_mask=").append(mask).append(" drag=").append(b.fields[6].getBoolean(b.panel)?1:0).append(" selecting=").append(b.fields[7].getBoolean(b.panel)?1:0);
  s.append(" members=");for(int n:members)s.append(n).append(',');s.append(" statuses=");for(int n:states)s.append(n).append(',');
  int ready=0;s.append(" pixels=");for(int n=0;n<14;n++){Icon value=b.icons[n].getIcon();int pixel=0;
   if(value instanceof ImageIcon){Image image=((ImageIcon)value).getImage();if(image instanceof BufferedImage){BufferedImage pixels=(BufferedImage)image;if(pixels.getWidth()>3&&pixels.getHeight()>3){pixel=pixels.getRGB(3,3);ready|=1<<n;}}}s.append(pixel).append(',');}s.append(" ready_mask=").append(ready);
  s.append(" generations=");for(int n=0;n<14;n++)s.append(b.generations.get(n)).append(',');s.append(" off_edt=");for(int n=0;n<14;n++)s.append(b.offEdt.get(n)).append(',');record(s.toString());
 }catch(Throwable ignored){failed.set(true);}}
 private static void install(){try{synchronized(bindings){if(!active.get())return;
  for(Window w:Window.getWindows())find(w);record("PANELS count="+bindings.size());
  mouseListener=new AWTEventListener(){public void eventDispatched(AWTEvent e){try{
   if(!active.get()||!(e instanceof MouseEvent)||!(e.getSource() instanceof Component))return;
   MouseEvent m=(MouseEvent)e;Component source=(Component)e.getSource();if(!inView(source))return;
   if(m.getID()==MouseEvent.MOUSE_PRESSED)firstClick.compareAndSet(0,System.nanoTime());
   java.util.List<Binding> current;synchronized(bindings){current=new ArrayList<Binding>(bindings);}
   if(current.isEmpty()){Component root=source;while(root!=null&&!VIEW.equals(root.getClass().getName()))root=root.getParent();if(root!=null)find(root);record("PANELS count="+bindings.size());}
   int slot=-1,panelIdentity=0,x=m.getX(),y=m.getY();
   synchronized(bindings){current=new ArrayList<Binding>(bindings);}
   for(Binding b:current){for(int n=0;n<14;n++)if(source==b.icons[n])slot=n;
    if(source==b.panel||SwingUtilities.isDescendingFrom(source,b.panel)){Point p=SwingUtilities.convertPoint(source,m.getPoint(),b.panel);x=p.x;y=p.y;panelIdentity=System.identityHashCode(b.panel);break;}}
   record("MOUSE id="+m.getID()+" source="+System.identityHashCode(source)+" panel="+panelIdentity+" slot="+slot+" x="+x+" y="+y+" modifiers="+m.getModifiersEx()+" button="+m.getButton()+" edt="+(SwingUtilities.isEventDispatchThread()?1:0));
  }catch(Throwable ignored){failed.set(true);}}};Toolkit.getDefaultToolkit().addAWTEventListener(mouseListener,AWTEvent.MOUSE_EVENT_MASK);
 }}catch(Throwable ignored){failed.set(true);}}
 private static void remove(){
  int remaining=0;java.util.List<Binding> copy;synchronized(bindings){active.set(false);
  try{if(mouseListener!=null)Toolkit.getDefaultToolkit().removeAWTEventListener(mouseListener);}catch(Throwable ignored){failed.set(true);remaining++;}finally{mouseListener=null;}
  copy=new ArrayList<Binding>(bindings);bindings.clear();}
  for(Binding b:copy)for(int n=0;n<14;n++)if(b.listeners[n]!=null){
   try{b.icons[n].removePropertyChangeListener("icon",b.listeners[n]);for(PropertyChangeListener listener:b.icons[n].getPropertyChangeListeners("icon"))if(listener==b.listeners[n])remaining++;}
   catch(Throwable ignored){failed.set(true);remaining++;}finally{b.listeners[n]=null;}
  }
  endLine="END failed="+(failed.get()?1:0)+" dropped="+dropped+" remaining_listeners="+remaining;
 }
 private static FileChannel validateSink(Path sink)throws Exception{
  Path jar=Paths.get(SelectionObserver.class.getProtectionDomain().getCodeSource().getLocation().toURI()).toAbsolutePath().normalize();
  Path parent=sink.getParent();
  if(!parent.getParent().equals(jar.getParent())||!parent.getFileName().toString().matches("live-[0-9a-f]{16}")||!sink.getFileName().toString().equals("ui-selection.log"))throw new IllegalArgumentException();
  java.nio.file.attribute.UserPrincipal user=sink.getFileSystem().getUserPrincipalLookupService().lookupPrincipalByName(System.getProperty("user.name"));
  BasicFileAttributes dir=Files.readAttributes(parent,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
  if(!dir.isDirectory()||!Files.getOwner(parent,LinkOption.NOFOLLOW_LINKS).equals(user)||!Files.getPosixFilePermissions(parent,LinkOption.NOFOLLOW_LINKS).equals(PosixFilePermissions.fromString("rwx------"))||!Files.getOwner(jar,LinkOption.NOFOLLOW_LINKS).equals(user))throw new IllegalArgumentException();
  BasicFileAttributes a=Files.readAttributes(sink,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
  if(!a.isRegularFile()||a.size()!=0||!Files.getOwner(sink,LinkOption.NOFOLLOW_LINKS).equals(user)||!Files.getPosixFilePermissions(sink,LinkOption.NOFOLLOW_LINKS).equals(PosixFilePermissions.fromString("rw-------"))||((Number)Files.getAttribute(sink,"unix:nlink",LinkOption.NOFOLLOW_LINKS)).intValue()!=1)throw new IllegalArgumentException();
  FileChannel result=FileChannel.open(sink,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);
  try{BasicFileAttributes after=Files.readAttributes(sink,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(!Objects.equals(a.fileKey(),after.fileKey())||result.size()!=0)throw new IllegalArgumentException();fileKey=a.fileKey();return result;}catch(Throwable x){result.close();throw x;}
 }
 public static void agentmain(String option,Instrumentation unused){try{
  if(!installed.compareAndSet(false,true))return;
  output=Paths.get(option).toAbsolutePath().normalize();channel=validateSink(output);
  byte[] pending="NUMERIC_UI_TRACE_PENDING_V1\n".getBytes(java.nio.charset.StandardCharsets.US_ASCII);pendingSize=pending.length;ByteBuffer header=ByteBuffer.wrap(pending);while(header.hasRemaining())channel.write(header);
  started=System.nanoTime();SwingUtilities.invokeLater(new Runnable(){public void run(){install();}});
  Thread worker=new Thread(new Runnable(){public void run(){try{
   while(!failed.get()&&System.nanoTime()-started<90000000000L){long click=firstClick.get();if(click!=0&&System.nanoTime()-click>30000000000L)break;Thread.sleep(100);}
   remove();
   BasicFileAttributes now=Files.readAttributes(output,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
   if(!now.isRegularFile()||!Objects.equals(fileKey,now.fileKey())||channel.size()!=pendingSize||((Number)Files.getAttribute(output,"unix:nlink",LinkOption.NOFOLLOW_LINKS)).intValue()!=1||!Files.getPosixFilePermissions(output,LinkOption.NOFOLLOW_LINKS).equals(PosixFilePermissions.fromString("rw-------")))return;
   StringBuilder text=new StringBuilder("NUMERIC_UI_TRACE_V1\n");synchronized(lines){for(String line:lines)text.append(line).append('\n');lines.clear();}
   channel.position(0);channel.truncate(0);ByteBuffer bytes=ByteBuffer.wrap(text.toString().getBytes(java.nio.charset.StandardCharsets.US_ASCII));while(bytes.hasRemaining())channel.write(bytes);channel.force(true);ByteBuffer trailer=ByteBuffer.wrap((endLine+"\n").getBytes(java.nio.charset.StandardCharsets.US_ASCII));while(trailer.hasRemaining())channel.write(trailer);channel.force(true);
  }catch(Throwable ignored){failed.set(true);remove();}finally{try{if(channel!=null)channel.close();}catch(Throwable ignored){}}}},"Numeric UI observation");worker.setDaemon(true);worker.start();
 }catch(Throwable ignored){failed.set(true);remove();try{if(channel!=null)channel.close();}catch(Throwable ignoredAgain){}}}
}
