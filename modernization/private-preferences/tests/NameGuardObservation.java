package atomiccaller;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
public final class NameGuardObservation {
 static void check(boolean value,String code){if(!value)throw new AssertionError("name-guard:"+code);}
 public static void main(String[] args)throws Exception{
  Path root=Paths.get(System.getProperty("fixture.directory")).toRealPath();String scenario=System.getProperty("fixture.scenario");boolean hard=scenario.equals("hard");Path target=root.resolve(hard?"hard-target":"Foo"),backup=root.resolve("hard-backup");byte[] bytes={9,8,7};Files.write(target,bytes);if(hard)Files.createLink(backup,target);Object inode=Files.getAttribute(target,"unix:ino");if(hard)Files.getAttribute(backup,"unix:ino");
  AtomicCallerObservation.Guard guard=new AtomicCallerObservation.Guard(root,System.getProperty("fixture.allowed.library"));System.setSecurityManager(guard);
  URL url=new File(System.getProperty("fixture.candidate")).toURI().toURL();Throwable failure=null;
  try(URLClassLoader loader=new URLClassLoader(new URL[]{url},null)){
   Class<?> helper=Class.forName("compat.PreferenceIO",true,loader);check(helper.getProtectionDomain().getCodeSource().getLocation().equals(url),"origin");
   try{helper.getMethod("write",String.class,Object.class).invoke(null,root.resolve(hard?"hard-target":"foo").toString(),new LinkedHashMap());}catch(InvocationTargetException e){failure=e.getCause();}
  }
  {
   check(failure==null,"save-success");check(!Arrays.equals(Files.readAllBytes(target),bytes),"hard-target-bytes");check(!inode.equals(Files.getAttribute(target,"unix:ino")),"target-inode");
   if(hard)check(inode.equals(Files.getAttribute(backup,"unix:ino"))&&Arrays.equals(Files.readAllBytes(backup),bytes),"backup-retained");
   else check(Arrays.equals(root.toFile().list(),new String[]{"Foo"}),"stored-alias-name");
  }
  check(guard.denied.get()==0,"guard");System.out.println("PASS name guard "+scenario+"; requested_target=true; foreign_inode_protected=true");
 }
}
