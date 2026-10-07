package atomiccaller;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
/** Direct actual private Session lifecycle; no serializer/controller/application entry. */
public final class SessionObservation {
 static void check(boolean value,String code){if(!value)throw new AssertionError("secure-session:"+code);}
 static Throwable call(Method m,Object owner,Object...args)throws Exception{try{m.invoke(owner,args);return null;}catch(InvocationTargetException e){return e.getCause();}}
 static void code(Throwable t,String code){check(t instanceof IOException&&code.equals(t.getMessage()),"consumed-code");}
 public static void main(String[] argv)throws Exception{
  Path root=Paths.get(System.getProperty("fixture.directory")).toRealPath(),target=root.resolve("profile");byte[] bytes={9,8,7};Files.write(target,bytes);
  AtomicCallerObservation.Guard guard=new AtomicCallerObservation.Guard(root,System.getProperty("fixture.allowed.library"));System.setSecurityManager(guard);
  URL url=new File(System.getProperty("fixture.candidate")).toURI().toURL();
  try(URLClassLoader loader=new URLClassLoader(new URL[]{url},null)){
   Class<?> helper=Class.forName("compat.PrivatePreferenceFile",true,loader),api=Class.forName("compat.PrivatePreferenceFile$Session",true,loader),library=Class.forName("compat.PrivatePreferenceFile$Library",true,loader);
   Method available=library.getDeclaredMethod("available");available.setAccessible(true);check((Boolean)available.invoke(null),"native-available");
   Constructor<?> constructor=api.getDeclaredConstructor();constructor.setAccessible(true);
   Method commit=api.getDeclaredMethod("commit"),abort=api.getDeclaredMethod("abort"),begin=helper.getDeclaredMethod("begin0",byte[].class,FileDescriptor.class,api),nativeCommit=helper.getDeclaredMethod("commit0",api),nativeAbort=helper.getDeclaredMethod("abort0",api);
   for(Method m:new Method[]{commit,abort,begin,nativeCommit,nativeAbort})m.setAccessible(true);
   Field handle=api.getDeclaredField("handle");handle.setAccessible(true);
   Object empty=constructor.newInstance();code(call(commit,empty),"atomic-session-consumed");check(call(abort,empty)==null,"empty-abort");code(call(nativeCommit,null,empty),"atomic-session-consumed");code(call(nativeAbort,null,empty),"atomic-session-consumed");code(call(nativeCommit,null,new Object[]{null}),"atomic-session-state");code(call(nativeAbort,null,new Object[]{null}),"atomic-session-state");
   Object one=constructor.newInstance();FileDescriptor descriptor=new FileDescriptor();try(FileOutputStream stream=new FileOutputStream(descriptor)){
    check(call(begin,null,target.toString().getBytes("UTF-8"),descriptor,one)==null,"begin");check(handle.getLong(one)!=0,"owned");
    code(call(begin,null,target.toString().getBytes("UTF-8"),new FileDescriptor(),one),"atomic-session-state");check(handle.getLong(one)!=0,"duplicate-begin-owned");stream.write(bytes);
   }
   check(call(commit,one)==null&&handle.getLong(one)==0,"commit-consumes");code(call(commit,one),"atomic-session-consumed");check(call(abort,one)==null,"abort-after-commit");check(Arrays.equals(Files.readAllBytes(target),bytes),"committed-bytes");
   Object two=constructor.newInstance();FileDescriptor second=new FileDescriptor();try(FileOutputStream stream=new FileOutputStream(second)){check(call(begin,null,target.toString().getBytes("UTF-8"),second,two)==null,"begin-again");stream.write(new byte[]{1,2,3});}
   check(call(abort,two)==null&&handle.getLong(two)==0,"abort-consumes");check(call(abort,two)==null,"abort-twice");code(call(commit,two),"atomic-session-consumed");check(Arrays.equals(Files.readAllBytes(target),bytes),"abort-retains");
  }
  check(guard.denied.get()==0&&root.toFile().list().length==1,"guard-listing");System.out.println("PASS secure session; consumed_rules=true; duplicate_begin_rejected=true; native_entry_owns_cleanup=true");
 }
}
