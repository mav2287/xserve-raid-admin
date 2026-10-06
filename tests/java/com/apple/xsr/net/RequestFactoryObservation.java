package com.apple.xsr.net;

import com.apple.net.acp.AcpPropertyCode;
import com.apple.util.plist.PropertyList;
import com.apple.xsr.TestEmail;
import fixture.OfflineGuard;
import java.io.*;
import java.lang.reflect.*;
import java.security.MessageDigest;
import java.util.*;

/** Synthetic factory objects and body-only serialization. Never sends a request. */
public final class RequestFactoryObservation {
    private static void check(boolean ok){if(!ok)throw new AssertionError("Request factory fixture failed");}
    private static String quote(String value){
        if(value==null)return "null";
        check(value.length()<512);StringBuilder b=new StringBuilder("\"");
        for(char c:value.toCharArray()){
            check(c>=32&&c<127);
            if(c=='\\'||c=='\"')b.append('\\');b.append(c);
        }
        return b.append('"').toString();
    }
    private static String descriptor(Class<?> type){
        if(type==Integer.TYPE)return "I";if(type==Boolean.TYPE)return "Z";
        check(!type.isPrimitive());
        return type.isArray()?type.getName().replace('.','/') : "L"+type.getName().replace('.','/')+";";
    }
    private static String signature(Method method){
        StringBuilder b=new StringBuilder(method.getName()+"(");
        for(Class<?> type:method.getParameterTypes())b.append(descriptor(type));
        return b.append(")Lcom/apple/xsr/net/RequestMessage;").toString();
    }
    private static Object argument(Class<?> type){
        if(type==Integer.TYPE||type==Integer.class)return Integer.valueOf(0);
        if(type==Boolean.TYPE)return Boolean.FALSE;
        if(type==Boolean.class)return Boolean.FALSE;
        if(type==String.class||type==Object.class)return "TEST";
        if(type==Date.class)return new Date(0);
        if(type==Integer[].class)return new Integer[]{0};
        if(type==String[].class)return new String[]{"TEST"};
        if(type==AcpPropertyCode.class)return AcpPropertyCode.SYS_VERSION;
        if(type==AcpPropertyCode[].class)return new AcpPropertyCode[]{AcpPropertyCode.SYS_VERSION};
        if(type==Map.class){Map<String,Object> map=new HashMap<String,Object>();map.put("TEST","fixture");return map;}
        if(type==ArrayList.class){ArrayList<String> list=new ArrayList<String>();list.add("fixture");return list;}
        if(type==TestEmail.class)return new TestEmail("fixture",null,null,null,null,null,new ArrayList());
        throw new AssertionError("Unsupported synthetic argument type");
    }
    private static Object field(Object owner,String name)throws Exception {
        for(Class<?> type=owner.getClass();type!=null;type=type.getSuperclass()){
            try{Field f=type.getDeclaredField(name);f.setAccessible(true);return f.get(owner);}
            catch(NoSuchFieldException absent){}
        }
        throw new AssertionError("Missing request field");
    }
    private static Object plist(RequestMessage request)throws Exception {
        if(Class.forName("com.apple.xsr.net.AcpxMessageFactory$AcpxRequestTemplate").isInstance(request))return field(request,"plist");
        check(request.getClass().getName().equals("com.apple.xsr.net.AcpxMessageFactory$1"));return null;
    }
    private static Object params(RequestMessage request)throws Exception {
        if(Class.forName("com.apple.xsr.net.AcpxMessageFactory$AcpxRequestTemplate").isInstance(request))return field(request,"paramDict");
        check(request.getClass().getName().equals("com.apple.xsr.net.AcpxMessageFactory$1"));return null;
    }
    private static byte[] body(RequestMessage request)throws Exception {
        final ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        OutputStream bounded=new OutputStream(){
            @Override public void write(int value){check(bytes.size()<65536);bytes.write(value);}
            @Override public void write(byte[] value,int off,int len){check(len>=0&&len<=65536-bytes.size());bytes.write(value,off,len);}
        };
        request.writeTo(bounded);return bytes.toByteArray();
    }
    private static String hash(byte[] bytes)throws Exception {
        StringBuilder b=new StringBuilder();for(byte value:MessageDigest.getInstance("SHA-256").digest(bytes))b.append(String.format("%02x",value&255));return b.toString();
    }
    private static RequestMessage queued(RequestMessage request)throws Exception {
        Field access=sun.misc.Unsafe.class.getDeclaredField("theUnsafe");access.setAccessible(true);sun.misc.Unsafe unsafe=(sun.misc.Unsafe)access.get(null);
        CommunicationsManager manager=(CommunicationsManager)unsafe.allocateInstance(CommunicationsManager.class);
        Field queue=CommunicationsManager.class.getDeclaredField("queue");queue.setAccessible(true);LinkedList<Object> entries=new LinkedList<Object>();queue.set(manager,entries);
        manager.postMessageAsync(new CommunicationHandler(){public void handleResponse(com.apple.xsr.som.RaidSystem system,Response response,Object context){throw new AssertionError("No worker permitted");}},request,new Object());
        check(entries.size()==1);Object transaction=entries.getFirst();Method get=transaction.getClass().getDeclaredMethod("getMessage");get.setAccessible(true);return (RequestMessage)get.invoke(transaction);
    }
    private static String sharing(String label,RequestMessage request,Map original,boolean expectedBodyChange)throws Exception {
        request.setRequestProperty("X-Fixture","before");request.setTargetController(RequestMessage.TARGET_TOP);request.setTimeout(10);
        if(original!=null)original.put("fixture","before");
        RequestMessage copy=queued(request);byte[] before=body(copy);
        if(original!=null){check("before".equals(original.get("fixture")));original.put("fixture","after");original.put("added","fixture");if(label.equals("command")){check(original.containsKey("rtc"));original.put("rtc",new Date(60000));}if(label.equals("property")){check(original.containsKey("TEST"));original.put("TEST","after");}}
        request.setRequestProperty("X-Fixture","after");request.setTargetController(RequestMessage.TARGET_BOTTOM);request.setTimeout(20);
        boolean changed=!Arrays.equals(before,body(copy));
        check(changed==expectedBodyChange&&"after".equals(copy.getRequestProperty("X-Fixture"))&&copy.getTargetController()==RequestMessage.TARGET_TOP&&copy.getTimeout()==10);
        return "{\"case\":"+quote(label)+",\"body_changed_after_post\":"+changed+",\"header_shared\":true,\"target_snapshot\":true,\"timeout_snapshot\":true}";
    }
    private static List<String> sharing()throws Exception {
        AcpxMessageFactory factory=new AcpxMessageFactory();factory.setDefaultTimeout(123);List<String> rows=new ArrayList<String>();
        RequestMessage rpc=factory.newGetStatusRequest();rows.add(sharing("rpc",rpc,(Map)params(rpc),true));
        RequestMessage command=factory.newSetTimeRequest(new Date(0));rows.add(sharing("command",command,(Map)params(command),false));
        Map<String,Object> values=new HashMap<String,Object>();Date date=new Date(0);byte[] data={1,2};values.put("date",date);values.put("data",data);
        RequestMessage property=factory.newSetPropertyRequest("TEST",values);rows.add(sharing("property",property,(Map)((PropertyList)plist(property)).getRootElement(),false));
        RequestMessage leaves=factory.newSetPropertyRequest("LEAF",values);RequestMessage clone=queued(leaves);byte[] before=body(clone);date.setTime(60000);data[0]=3;check(Arrays.equals(before,body(clone))&&!Arrays.equals(before,body(leaves)));
        rows.add("{\"case\":\"property-mutable-leaves\",\"date_and_bytes_isolated\":true}");
        rows.add(sharing("noop",factory.newNoOpRequest(),null,false));
        ArrayList<String> list=new ArrayList<String>();list.add("fixture");RequestMessage masks=factory.newSetFibreChannelLUNMaskRequest(list);RequestMessage masksCopy=queued(masks);byte[] masksBefore=body(masksCopy);list.add("after");check(!Arrays.equals(masksBefore,body(masksCopy)));
        rows.add("{\"case\":\"rpc-caller-list\",\"body_changed_after_post\":true}");
        return rows;
    }
    private static String strings(Collection<?> values){
        ArrayList<String> sorted=new ArrayList<String>();
        for(Object value:values){check(value instanceof String);sorted.add((String)value);}
        Collections.sort(sorted);StringBuilder b=new StringBuilder("[");
        for(String value:sorted){if(b.length()>1)b.append(',');b.append(quote(value));}
        return b.append(']').toString();
    }
    private static String target(RequestMessage request)throws Exception {
        Object target=request.getTargetController();if(target==null)return null;
        String result=null;for(Field field:RequestMessage.class.getFields())if(field.getType()==RequestMessage.Target.class&&field.get(null)==target){check(result==null);result=field.getName();}
        check(result!=null);return result;
    }
    private static String observation(Method method,RequestMessage request,int timeout)throws Exception {
        check(request.getUser()==null&&request.getPassword()==null&&request.getRequestProperties().length==0);
        String path=request.getPath(),command=request.getCommand();
        Object originalPlist=plist(request),parameters=params(request);
        Object root=originalPlist==null?null:((PropertyList)originalPlist).getRootElement();
        String shape;Collection<?> keys=Collections.emptyList();boolean bodyTimeout=false;
        if(root==null)shape="none";
        else if(root instanceof ArrayList)shape="property-array";
        else {
            check(root instanceof Map);Map map=(Map)root;
            if("/cgi-bin/perform".equals(path)){
                shape="rpc";check(map.size()==1&&map.get("requests") instanceof ArrayList);
                ArrayList requests=(ArrayList)map.get("requests");check(requests.size()==1&&requests.get(0) instanceof Map);
                Map rpc=(Map)requests.get(0);check(rpc.size()==2&&command!=null&&command.equals(rpc.get("method"))&&rpc.get("inputs")==parameters);
            }else if(command!=null){shape="command-dict";check(map.size()==1&&map.get(command)==parameters);}
            else shape="property-dict";
        }
        if(parameters!=null){check(parameters instanceof Map);Map map=(Map)parameters;keys=map.keySet();bodyTimeout=map.containsKey("timeout");}
        if(shape.equals("property-dict")||shape.equals("property-array")||shape.equals("none"))check(parameters==null);
        RequestMessage clone=(RequestMessage)request.clone();
        byte[] serialized=body(request);
        check(clone!=request&&clone.getClass()==request.getClass()&&Arrays.equals(serialized,body(clone)));
        String plistClone=originalPlist==null?"absent":plist(clone)==originalPlist?"shared":"copied";
        String parametersClone=parameters==null?"absent":params(clone)==parameters?"shared":"copied";
        boolean sharedHeaders=field(request,"properties")==field(clone,"properties");
        return "{\"signature\":"+quote(signature(method))+",\"factory_timeout\":"+timeout+
            ",\"class\":"+quote(request.getClass().getName())+",\"path\":"+quote(path)+",\"command\":"+quote(command)+
            ",\"target\":"+quote(target(request))+",\"body_sha256\":"+quote(hash(serialized))+",\"body_size\":"+serialized.length+",\"shutdown\":"+request.getShutdownConnection()+",\"restart\":"+request.getRestartConnection()+
            ",\"timeout\":"+request.getTimeout()+",\"body_timeout_present\":"+bodyTimeout+
            ",\"shape\":"+quote(shape)+",\"parameter_keys\":"+strings(keys)+
            ",\"plist_clone\":"+quote(plistClone)+",\"parameters_clone\":"+quote(parametersClone)+",\"shared_headers\":"+sharedHeaders+"}";
    }
    public static void main(String[] args)throws Exception {
        check(args.length==0);OfflineGuard.install();PrintStream out=System.out,err=System.err;
        ByteArrayOutputStream captured=new ByteArrayOutputStream(),errors=new ByteArrayOutputStream();
        List<String> rows=new ArrayList<String>(),signatures=new ArrayList<String>(),shared=null;
        try {
            System.setOut(new PrintStream(captured,true,"UTF-8"));System.setErr(new PrintStream(errors,true,"UTF-8"));
            org.apache.log4j.LogManager.getLoggerRepository().setThreshold(org.apache.log4j.Level.OFF);
            TreeMap<String,Method> methods=new TreeMap<String,Method>();
            for(Method method:AcpxMessageFactory.class.getDeclaredMethods())if(method.getName().startsWith("new")&&method.getReturnType()==RequestMessage.class){check(Modifier.isPublic(method.getModifiers())&&!Modifier.isStatic(method.getModifiers())&&!method.isBridge()&&!method.isSynthetic());check(methods.put(signature(method),method)==null);}
            check(methods.size()==59);signatures.addAll(methods.keySet());
            for(int timeout:new int[]{0,123}){
                AcpxMessageFactory factory=new AcpxMessageFactory();factory.setDefaultTimeout(timeout);
                for(Method method:methods.values()){
                    if(method.getName().equals("newUpdateFirmwareRequest")){check(signature(method).equals("newUpdateFirmwareRequest(IILjava/lang/String;)Lcom/apple/xsr/net/RequestMessage;"));continue;}
                    Class<?>[] types=method.getParameterTypes();Object[] arguments=new Object[types.length];
                    for(int i=0;i<types.length;i++)arguments[i]=argument(types[i]);
                    RequestMessage request=(RequestMessage)method.invoke(factory,arguments);
                    rows.add(observation(method,request,timeout));
                }
            }
            shared=sharing();
            check(rows.size()==116&&captured.size()==0&&errors.size()==0);OfflineGuard.assertUntouched();
        }finally{System.setOut(out);System.setErr(err);OfflineGuard.assertUntouched();}
        out.print("{\"signatures\":"+strings(signatures)+",\"rows\":[");
        for(int i=0;i<rows.size();i++){if(i>0)out.print(',');out.print(rows.get(i));}
        out.print("],\"enqueue_observations\":[");for(int i=0;i<shared.size();i++){if(i>0)out.print(',');out.print(shared.get(i));}
        out.println("],\"invoked_per_sweep\":58,\"excluded_per_sweep\":1,\"guarded_operations\":0}");
    }
}
