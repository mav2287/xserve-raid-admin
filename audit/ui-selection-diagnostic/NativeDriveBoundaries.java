import com.apple.xsr.DriveSelectionPanel;
import fixture.OfflineGuard;
import java.awt.*;
import java.awt.event.*;
import java.awt.image.BufferedImage;
import java.lang.reflect.*;
import javax.swing.*;

/** Synthetic original native layout/renderer/input only; no Main, profiles or RaidSystem. */
public final class NativeDriveBoundaries {
 static String variant;static double paintScale;static int created;static String imageClass;static final java.util.IdentityHashMap<Image,Boolean> createdImages=new java.util.IdentityHashMap<Image,Boolean>();static final java.util.ArrayDeque<Image> recent=new java.util.ArrayDeque<Image>();
 static final java.util.List<Step> steps=new java.util.ArrayList<Step>();static int[] memberOracle,stateOracle;static Rectangle[] originalBounds;static Component hover,pressTarget;static JLabel stepLabel;static long priorStep;static javax.swing.Timer timer;static JFrame frame;static Panel panel;static JLabel[] icons;static Track[] tracks;
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
  frame=new JFrame("Offline RAID test: 1 SECOND - drive centers, boundaries, edges and drags \u2014 variant "+variant+" \u2014 synthetic drives only");frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
  JPanel content=new JPanel(new BorderLayout());content.add(new JLabel("Synthetic original renderer; no controller or saved profiles"),BorderLayout.NORTH);content.add(panel,BorderLayout.CENTER);stepLabel=new JLabel("One second between steps; synthetic input only");content.add(stepLabel,BorderLayout.SOUTH);stepLabel.setPreferredSize(new Dimension(780,26));frame.setContentPane(content);frame.pack();frame.setLocationByPlatform(true);frame.setVisible(true);
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
  memberOracle=membership.clone();stateOracle=states.clone();originalBounds=new Rectangle[14];for(int n=0;n<14;n++)originalBounds[n]=icons[n].getBounds();makeSteps();
  timer=new javax.swing.Timer(1000,null);timer.setRepeats(false);timer.setInitialDelay(1000);
  timer.addActionListener(new ActionListener(){public void actionPerformed(ActionEvent e){try{
   if(turn>0)for(int i=0;i<14;i++)if(tracks[i].painted!=tracks[i].generation)stale++;
   if(turn==steps.size()){timer.stop();frame.dispose();done.countDown();return;}
   long now=System.nanoTime();if(priorStep!=0)check(now-priorStep>=950000000L,"minimum-one-second-hold");priorStep=now;
   Step step=steps.get(turn++);runStep(step);stepLabel.setText("Step "+turn+"/"+steps.size()+" | "+step.name+" | hit drive "+(slot(hit(step.point))+1)+" | 1 second hold");
   int mode=field("selectionMode").getInt(panel),selectedDrive=field("driveIndex").getInt(panel),array=panel.getArrayIndex();
   int mask=0;for(int i=0;i<14;i++){boolean highlighted=mode==3?i==selectedDrive:memberOracle[i]==array;if(highlighted)mask|=1<<i;check(hash(icons[i])==(highlighted?selectedOracle[i]:baseOracle[i]),"image-hash");}
   check(java.util.Arrays.equals(memberOracle,(int[])field("driveArrays").get(panel))&&java.util.Arrays.equals(stateOracle,(int[])field("driveStates").get(panel)),"synthetic-model-unchanged");
   System.out.println("STEP "+turn+" kind="+step.name+" x="+step.point.x+" y="+step.point.y+" hit="+slot(hit(step.point))+" mode="+mode+" drive="+selectedDrive+" array="+array+" expected_mask="+mask+" drag="+field("inDragSelect").getBoolean(panel));
   timer.restart();
  }catch(Throwable x){failure=x;timer.stop();frame.dispose();done.countDown();}}});timer.start();
 }
 static class Step {final String name;final Point point;final int mode,action;Step(String n,Point p,int m,int a){name=n;point=p;mode=m;action=a;}}
 static Point center(int n){Rectangle r=icons[n].getBounds();return new Point(r.x+r.width/2,r.y+r.height/2);}
 static Component hit(Point p){return SwingUtilities.getDeepestComponentAt(panel,p.x,p.y);}
 static int slot(Component c){for(int n=0;n<14;n++)if(c==icons[n])return n;return -1;}
 static void add(String name,Point p,int mode,int action){steps.add(new Step(name,p,mode,action));}
 static void makeSteps(){
  for(int n=0;n<14;n++)add("center-drive-"+(n+1),center(n),n%2==0?3:4,0);
  for(int n:new int[]{0,4,5,6,12}){Rectangle r=icons[n].getBounds();for(int dx=-1;dx<=1;dx++)add("drive-"+(n+1)+"-right-boundary-"+dx,new Point(r.x+r.width+dx,r.y+r.height/2),dx==0?4:3,0);}
  for(int n:new int[]{5,6,7}){Rectangle r=icons[n].getBounds();add("drive-"+(n+1)+"-top-left",new Point(r.x,r.y),3,0);add("drive-"+(n+1)+"-top-right",new Point(r.x+r.width-1,r.y),4,0);add("drive-"+(n+1)+"-bottom-left",new Point(r.x,r.y+r.height-1),3,0);add("drive-"+(n+1)+"-bottom-right",new Point(r.x+r.width-1,r.y+r.height-1),4,0);}
  Rectangle six=icons[5].getBounds();add("above-drive-6",new Point(six.x+six.width/2,six.y-1),3,0);add("below-drive-6",new Point(six.x+six.width/2,six.y+six.height),4,0);
  Rectangle left=icons[6].getBounds(),right=icons[7].getBounds();add("divider-gap-midpoint",new Point((left.x+left.width+right.x)/2,left.y+left.height/2),3,0);
  for(int[] pair:new int[][]{{4,5},{5,6},{6,7},{13,12}}){int mode=pair[0]==6?4:3;add("drag-press-drive-"+(pair[0]+1),center(pair[0]),mode,1);add("drag-enter-drive-"+(pair[1]+1),center(pair[1]),mode,2);add("drag-release-captured",center(pair[1]),mode,3);add("hover-after-release",center(pair[0]),mode,4);}
  System.out.println("SCENARIOS count="+steps.size()+" tick_ms=1000; original image path only; no OS pointer injection");
 }
 static void send(Component source,Point point,int id,int mask,int button){if(source==null||slot(source)<0)return;Point local=SwingUtilities.convertPoint(panel,point,source);source.dispatchEvent(new TaggedEvent(source,id,mask,button,local));}
 static void move(Point point,int mask){Component target=hit(point);if(target!=hover){if(hover!=null)send(hover,point,MouseEvent.MOUSE_EXITED,mask,0);if(target!=null)send(target,point,MouseEvent.MOUSE_ENTERED,mask,0);hover=target;}}
 static void expectSelection(int n,int mode)throws Exception{if(n<0)return;if(mode==3)check(field("driveIndex").getInt(panel)==n,"clicked-drive-index");else check(panel.getArrayIndex()==memberOracle[n],"clicked-array-index");}
 static void runStep(Step step)throws Exception{
  check(SwingUtilities.isEventDispatchThread(),"input-on-edt");for(int n=0;n<14;n++)check(originalBounds[n].equals(icons[n].getBounds()),"stable-hit-bounds");
  if(step.action<=1){check(!field("inDragSelect").getBoolean(panel),"clean-drag-before-press");panel.setSelectionMode(step.mode);}
  int driveBefore=field("driveIndex").getInt(panel),arrayBefore=panel.getArrayIndex();Component target=hit(step.point);int n=slot(target);
  if(step.action==0){move(step.point,0);send(target,step.point,MouseEvent.MOUSE_PRESSED,InputEvent.BUTTON1_DOWN_MASK,1);send(target,step.point,MouseEvent.MOUSE_RELEASED,0,1);send(target,step.point,MouseEvent.MOUSE_CLICKED,0,1);expectSelection(n,step.mode);check(!field("inDragSelect").getBoolean(panel),"click-release-clears-drag");if(n<0)check(driveBefore==field("driveIndex").getInt(panel)&&arrayBefore==panel.getArrayIndex(),"gap-click-unchanged");}
  else if(step.action==1){check(n>=0,"drag-start-hit");move(step.point,0);pressTarget=target;send(target,step.point,MouseEvent.MOUSE_PRESSED,InputEvent.BUTTON1_DOWN_MASK,1);expectSelection(n,step.mode);check(field("inDragSelect").getBoolean(panel)&&field("selecting").getBoolean(panel),"drag-start-flag");}
  else if(step.action==2){move(step.point,InputEvent.BUTTON1_DOWN_MASK);send(pressTarget,step.point,MouseEvent.MOUSE_DRAGGED,InputEvent.BUTTON1_DOWN_MASK,0);expectSelection(n,step.mode);check(field("inDragSelect").getBoolean(panel)&&field("selecting").getBoolean(panel),"drag-enter-flag");}
  else if(step.action==3){send(pressTarget,step.point,MouseEvent.MOUSE_RELEASED,0,1);pressTarget=null;check(!field("inDragSelect").getBoolean(panel),"captured-release-clears-drag");check(driveBefore==field("driveIndex").getInt(panel)&&arrayBefore==panel.getArrayIndex(),"release-selection-unchanged");}
  else{move(step.point,0);check(!field("inDragSelect").getBoolean(panel)&&driveBefore==field("driveIndex").getInt(panel)&&arrayBefore==panel.getArrayIndex(),"post-release-hover-unchanged");}
 }
 static class TaggedEvent extends MouseEvent {TaggedEvent(Component c,int id,int mask,int button,Point p){super(c,id,System.currentTimeMillis(),mask,p.x,p.y,(id==MouseEvent.MOUSE_PRESSED||id==MouseEvent.MOUSE_RELEASED||id==MouseEvent.MOUSE_CLICKED)?1:0,false,button);}}
 static int hash(JLabel label){Image im=((ImageIcon)label.getIcon()).getImage();check(createdImages.containsKey(im),"override-used");if(!"A".equals(variant))check(im.getAccelerationPriority()==0f,"priority-zero");if("C".equals(variant))check(((BufferedImage)im).getType()==BufferedImage.TYPE_INT_RGB,"software-type");check(im instanceof BufferedImage,"native-image-kind");BufferedImage b=(BufferedImage)im;return java.util.Arrays.hashCode(b.getRGB(0,0,b.getWidth(),b.getHeight(),null,0,b.getWidth()));}
 public static void main(String[] args)throws Exception{
  variant=args[0];check(variant.matches("[ABC]"),"variant");
  check(!GraphicsEnvironment.isHeadless(),"native-required");OfflineGuard.install();
  Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler(){public void uncaughtException(Thread t,Throwable x){failure=x;done.countDown();}});
  SwingUtilities.invokeAndWait(new Runnable(){public void run(){try{setup();}catch(Throwable x){failure=x;if(frame!=null)frame.dispose();done.countDown();}}});
  try{check(done.await(100,java.util.concurrent.TimeUnit.SECONDS),"timeout");}finally{SwingUtilities.invokeAndWait(new Runnable(){public void run(){if(timer!=null)timer.stop();if(frame!=null)frame.dispose();}});}
  OfflineGuard.assertUntouched();
  if(failure!=null){System.out.println("FAIL_CODE "+failureCode);for(Throwable x=failure;x!=null;x=x.getCause()){System.out.println(x.getClass().getName());for(StackTraceElement e:x.getStackTrace())System.out.println(e.getClassName()+"."+e.getMethodName()+":"+e.getLineNumber());}throw new AssertionError("native-fixture-failed");}
  check(paints>0,"paint-inconclusive");
  System.out.println("PASS native variant="+variant+" paint_scale="+paintScale+" created="+created+" image_class="+imageClass+"; transitions="+turn+"; paints="+paints+" stale_generations_at_tick="+stale+" max_paint_after_event_ns="+maxPaintNs+" java_guard_prohibited_operations=0; native_OS_preferences_unmeasured; no_framebuffer_or_controller_qualification");
 }
}
