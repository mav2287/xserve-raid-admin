package securefixture;
import java.io.*;
import java.lang.reflect.*;
import com.apple.util.plist.PropertyListUtilities;

/** Fixture only: four race cases invoke the real private JNI/session primitives. */
public final class TransactionProbe {
    public static void write(String path,Object dictionary)throws IOException{compat.PrivatePreferenceFile.write(path,dictionary);}
    static Object invoke(Method method,Object target,Object...args)throws Throwable{
        try{return method.invoke(target,args);}catch(InvocationTargetException failure){throw failure.getCause();}
    }
    static void rethrow(Throwable failure)throws IOException{
        if(failure instanceof IOException)throw(IOException)failure;
        if(failure instanceof RuntimeException)throw(RuntimeException)failure;
        if(failure instanceof Error)throw(Error)failure;
        throw new AssertionError("transaction-probe:unexpected-checked-type");
    }
    public static void writeWithHook(String identifier,Object dictionary,Runnable hook)throws IOException{
        Object session=null;Method abort=null;
        try{
            Class<?> helper=compat.PrivatePreferenceFile.class,library=Class.forName("compat.PrivatePreferenceFile$Library");
            Method path=helper.getDeclaredMethod("path",String.class);path.setAccessible(true);byte[] bytes=(byte[])invoke(path,null,identifier);
            Method available=library.getDeclaredMethod("available");available.setAccessible(true);if(!(Boolean)invoke(available,null))throw new IOException("atomic-library-unavailable");
            Class<?> owner=Class.forName("compat.PrivatePreferenceFile$Session");Constructor<?> constructor=owner.getDeclaredConstructor();constructor.setAccessible(true);session=constructor.newInstance();
            abort=owner.getDeclaredMethod("abortPreserving",Throwable.class);abort.setAccessible(true);
            Method begin=helper.getDeclaredMethod("begin0",byte[].class,FileDescriptor.class,owner);begin.setAccessible(true);
            Method commit=owner.getDeclaredMethod("commit");commit.setAccessible(true);FileDescriptor descriptor=new FileDescriptor();
            try(OutputStream output=new FileOutputStream(descriptor)){
                invoke(begin,null,bytes,descriptor,session);OutputStreamWriter writer=new OutputStreamWriter(output,"UTF-8");PropertyListUtilities.writeXML(dictionary,writer);writer.flush();
            }
            hook.run();invoke(commit,session);
        }catch(Throwable primary){
            if(session!=null&&abort!=null)try{invoke(abort,session,primary);}catch(Throwable ignored){}
            rethrow(primary);
        }
    }
}
