import com.apple.xsr.DriveSelectionPanel;
import fixture.OfflineGuard;
import java.awt.*;
import java.awt.event.*;
import java.awt.image.BufferedImage;
import java.lang.reflect.*;
import javax.swing.*;

/** Synthetic original native layout/renderer/input only; no Main, profiles or RaidSystem. */
public final class NativeDriveHeld {
 static String variant;static double paintScale;static int created;static String imageClass;static final java.util.IdentityHashMap<Image,Boolean> createdImages=new java.util.IdentityHashMap<Image,Boolean>();static final java.util.ArrayDeque<Image> recent=new java.util.ArrayDeque<Image>();
 static JLabel stepLabel;static long priorStep;static javax.swing.Timer timer;static JFrame frame;static Panel panel;static JLabel[] icons;static Track[] tracks;
 static int turn;static long began;static long maxPaintNs;static int paints, stale, mismatches;static Throwable failure;
 static int[] baseOracle=new int[14],selectedOracle=new int[14];static String failureCode="unexpected";static final java.util.concurrent.CountDownLatch done=new java.util.concurrent.CountDownLatch(1);
 static class Panel extends DriveSelectionPanel {
  Panel(){super(4,null,null,null,null);}
  static final String MODE=variant;
  @Override public Image createImage(int width,int height){
   Image image="C".equals(MODE)?new BufferedImage(width,height,BufferedImage.TYPE_INT_RGB):super.createImage(width,height);
   if(image!=null){if(!"A".equals(MODE))image.setAccelerationPriority(0f);created++;imageClass=image.getClass().getName();createdImages.put(image,Boolean.TRUE);recent.add(image);if(recent.size()>28)recent.remove();for(java.util.Iterator<Image> it=createdImages.keySet().iterator();it.hasNext();){Image candidate=it.next();boolean held=false;if(icons!=null)for(JLabel label:icons)if(label!=null&&label.getIcon() instanceof ImageIcon&&((ImageIcon)label.getIcon()).getImage()==candidate)held=true;if(!held&&!recent.contains(candidate))it.remove();}}return image;
  }
  @Override public void syncSummary(){} // Deliberately excludes model-dependent summaries.
 }
 static Field field(String n)throws Exception{Field f=DriveSelectionPanel.class.getDeclaredField(n);f.setAccessible(true);return f;}
 static class Track extends JLabel {
  int generation;int painted;long assignedAt;final int drive;
  Track(int i,Icon icon){super(icon);drive=i;}
  @Override public void setIcon(Icon icon){if(icon!=getIcon()){generation++;assignedAt=System.nanoTime();}super.setIcon(icon);}
  @Override protected void paintComponent(Graphics g){try{boolean changed=painted!=generation;if(g instanceof Graphics2D)paintScale=((Graphics2D)g).getTransform().getScaleX();super.paintComponent(g);painted=generation;paints++;if(turn>0&&changed)maxPaintNs=Math.max(maxPaintNs,System.nanoTime()-assignedAt);}catch(Throwable x){failure=x;done.countDown();}}
 }
 static void check(boolean ok,String code){if(!ok){failureCode=code;throw new AssertionError(code);}}
 static void setup()throws Exception{
  UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());com.apple.xsr.Resources.load();
  panel=new Panel();int[] membership=new int[14],states=new int[14];
  for(int i=0;i<14;i++){membership[i]=i<7?1:2;states[i]=-2;}
  panel.setDriveArrays(membership);panel.setDriveStates(states);
  icons=(JLabel[])field("driveIcon").get(panel);tracks=new Track[14];
  GridBagLayout layout=(GridBagLayout)panel.getLayout();
  for(int i=0;i<14;i++){
   JLabel old=icons[i];Track label=new Track(i,old.getIcon());GridBagConstraints constraint=layout.getConstraints(old);int order=panel.getComponentZOrder(old);
   label.setBorder(old.getBorder());label.setHorizontalAlignment(old.getHorizontalAlignment());label.setVerticalAlignment(old.getVerticalAlignment());
   label.setHorizontalTextPosition(old.getHorizontalTextPosition());label.setVerticalTextPosition(old.getVerticalTextPosition());label.setIconTextGap(old.getIconTextGap());label.setEnabled(old.isEnabled());
   check(label.getPreferredSize().equals(old.getPreferredSize()) && label.getMinimumSize().equals(old.getMinimumSize()) && label.getMaximumSize().equals(old.getMaximumSize()),"label-size");
   for(final MouseListener mouse:old.getMouseListeners())label.addMouseListener(new MouseListener(){
    public void mousePressed(MouseEvent e){if(e instanceof TaggedEvent)mouse.mousePressed(e);}public void mouseReleased(MouseEvent e){if(e instanceof TaggedEvent)mouse.mouseReleased(e);}
    public void mouseEntered(MouseEvent e){if(e instanceof TaggedEvent)mouse.mouseEntered(e);}public void mouseExited(MouseEvent e){if(e instanceof TaggedEvent)mouse.mouseExited(e);}
    public void mouseClicked(MouseEvent e){if(e instanceof TaggedEvent)mouse.mouseClicked(e);}});
   panel.remove(old);panel.add(label,constraint,order);icons[i]=label;tracks[i]=label;
  }
  frame=new JFrame("Offline RAID test: ONE TEST - selections held for 3 seconds \u2014 variant "+variant+" \u2014 synthetic drives only");frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
  JPanel content=new JPanel(new BorderLayout());content.add(new JLabel("Synthetic original renderer; no controller or saved profiles"),BorderLayout.NORTH);content.add(panel,BorderLayout.CENTER);stepLabel=new JLabel("Waiting 3 seconds before step 1");content.add(stepLabel,BorderLayout.SOUTH);frame.setContentPane(content);frame.pack();frame.setLocationByPlatform(true);frame.setVisible(true);
  check(panel.isShowing() && frame.isShowing(),"display");
  System.out.println("SETUP native_scale="+frame.getGraphicsConfiguration().getDefaultTransform().getScaleX()+"; labels=14; opaque="+panel.isOpaque());
  for(int i=0;i<14;i++){
   Rectangle b=icons[i].getBounds();System.out.println("BOUND drive="+(i+1)+" x="+b.x+" y="+b.y+" width="+b.width+" height="+b.height);
   Component c=SwingUtilities.getDeepestComponentAt(panel,b.x+b.width-1,b.y+b.height/2);check(c==icons[i],"inside-hit");
   Component beyond=SwingUtilities.getDeepestComponentAt(panel,b.x+b.width,b.y+b.height/2);check(beyond!=icons[i],"outside-hit");
  }
  panel.setArrayIndex(-10);panel.setSelectionMode(4);for(int i=0;i<14;i++)baseOracle[i]=hash(icons[i]);
  panel.setArrayIndex(1);for(int i=0;i<7;i++)selectedOracle[i]=hash(icons[i]);
  panel.setArrayIndex(2);for(int i=7;i<14;i++)selectedOracle[i]=hash(icons[i]);
  for(int i=0;i<14;i++)check(baseOracle[i]!=selectedOracle[i],"tint-oracle");
  timer=new javax.swing.Timer(3000,null);timer.setRepeats(false);timer.setInitialDelay(3000);
  timer.addActionListener(new ActionListener(){public void actionPerformed(ActionEvent e){try{
   if(turn>0)for(int i=0;i<14;i++)if(tracks[i].painted!=tracks[i].generation)stale++;
   if(turn++==12){timer.stop();frame.dispose();done.countDown();return;}
   long now=System.nanoTime();if(priorStep!=0)check(now-priorStep>=2900000000L,"minimum-three-second-hold");priorStep=now;stepLabel.setText("Step "+turn+" of 12 - next selection in 3 seconds");
   int phase=turn%6;began=System.nanoTime();
   if(phase==0){panel.setSelectionMode(3);mouse(3,MouseEvent.MOUSE_PRESSED,InputEvent.BUTTON1_DOWN_MASK,1);mouse(3,MouseEvent.MOUSE_RELEASED,0,1);}
   else if(phase==1){panel.setArrayIndex(1);panel.setSelectionMode(4);}
   else if(phase==2){panel.setArrayIndex(2);panel.setSelectionMode(4);}
   else if(phase==3){panel.setSelectionMode(3);mouse(5,MouseEvent.MOUSE_PRESSED,InputEvent.BUTTON1_DOWN_MASK,1);mouse(5,MouseEvent.MOUSE_RELEASED,0,1);}
   else {int drive=phase==4?5:10;panel.setSelectionMode(3);mouse(drive,MouseEvent.MOUSE_PRESSED,InputEvent.BUTTON1_DOWN_MASK|InputEvent.ALT_DOWN_MASK,1);mouse(drive,MouseEvent.MOUSE_RELEASED,InputEvent.ALT_DOWN_MASK,1);check(field("selectionMode").getInt(panel)==4,"alt-mode");}
   int mode=field("selectionMode").getInt(panel),selectedDrive=field("driveIndex").getInt(panel),array=panel.getArrayIndex();
   for(int i=0;i<14;i++){
    boolean highlighted=mode==3?i==selectedDrive:membership[i]==array;
    check(hash(icons[i])==(highlighted?selectedOracle[i]:baseOracle[i]),"image-hash");
   }
   timer.restart();
  }catch(Throwable x){failure=x;timer.stop();frame.dispose();done.countDown();}}});timer.start();
 }
 static void mouse(int drive,int id,int mask,int button){JLabel icon=icons[drive];MouseEvent e=new TaggedEvent(icon,id,mask,button);icon.dispatchEvent(e);}
 static class TaggedEvent extends MouseEvent {TaggedEvent(JLabel icon,int id,int mask,int button){super(icon,id,System.currentTimeMillis(),mask,icon.getWidth()-1,icon.getHeight()/2,1,false,button);}}
 static int hash(JLabel label){Image im=((ImageIcon)label.getIcon()).getImage();check(createdImages.containsKey(im),"override-used");if(!"A".equals(variant))check(im.getAccelerationPriority()==0f,"priority-zero");if("C".equals(variant))check(((BufferedImage)im).getType()==BufferedImage.TYPE_INT_RGB,"software-type");check(im instanceof BufferedImage,"native-image-kind");BufferedImage b=(BufferedImage)im;return java.util.Arrays.hashCode(b.getRGB(0,0,b.getWidth(),b.getHeight(),null,0,b.getWidth()));}
 public static void main(String[] args)throws Exception{
  variant=args[0];check(variant.matches("[ABC]"),"variant");
  check(!GraphicsEnvironment.isHeadless(),"native-required");OfflineGuard.install();
  Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler(){public void uncaughtException(Thread t,Throwable x){failure=x;done.countDown();}});
  SwingUtilities.invokeAndWait(new Runnable(){public void run(){try{setup();}catch(Throwable x){failure=x;if(frame!=null)frame.dispose();done.countDown();}}});
  try{check(done.await(60,java.util.concurrent.TimeUnit.SECONDS),"timeout");}finally{SwingUtilities.invokeAndWait(new Runnable(){public void run(){if(timer!=null)timer.stop();if(frame!=null)frame.dispose();}});}
  OfflineGuard.assertUntouched();
  if(failure!=null){System.out.println("FAIL_CODE "+failureCode);for(Throwable x=failure;x!=null;x=x.getCause()){System.out.println(x.getClass().getName());for(StackTraceElement e:x.getStackTrace())System.out.println(e.getClassName()+"."+e.getMethodName()+":"+e.getLineNumber());}throw new AssertionError("native-fixture-failed");}
  check(paints>0,"paint-inconclusive");
  System.out.println("PASS native variant="+variant+" paint_scale="+paintScale+" created="+created+" image_class="+imageClass+"; transitions=12; paints="+paints+" stale_generations_at_tick="+stale+" max_paint_after_event_ns="+maxPaintNs+" java_guard_prohibited_operations=0; native_OS_preferences_unmeasured; no_framebuffer_or_controller_qualification");
 }
}
