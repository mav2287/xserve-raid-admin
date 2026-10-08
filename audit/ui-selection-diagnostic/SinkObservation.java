package uiprobe;
import java.lang.reflect.*;
import java.nio.channels.FileChannel;
import java.nio.file.*;
public final class SinkObservation {
 public static void main(String[]args)throws Exception{
  Method m=SelectionObserver.class.getDeclaredMethod("validateSink",Path.class);m.setAccessible(true);boolean accepted=false;
  try{FileChannel c=(FileChannel)m.invoke(null,Paths.get(args[0]));c.close();accepted=true;}catch(InvocationTargetException expected){}
  if(accepted!=Boolean.parseBoolean(args[1]))throw new AssertionError("sink expectation");
  System.out.println("PASS sink acceptance="+accepted);
 }
}
