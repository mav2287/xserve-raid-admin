package uiprobe;
import com.sun.tools.attach.VirtualMachine;
public final class AttachObserver {
 public static void main(String[] args) throws Exception {
  VirtualMachine vm=null;
  try{vm=VirtualMachine.attach(args[0]);vm.loadAgent(args[1],args[2]);System.out.println("ATTACHED numeric UI observer");}
  catch(Throwable ignored){throw new AssertionError("UI observer attach failed; details withheld");}
  finally{if(vm!=null)vm.detach();}
 }
}
