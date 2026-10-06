package com.apple.mrj;

import java.io.File;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.List;
import java.util.SortedSet;
import java.util.TreeSet;

/** Bridge the original callbacks to the public macOS API supplied by Java 8 or 9+. */
public class MRJApplicationUtils {
    private static final SortedSet<String> FAILURES = new TreeSet<String>();
    private static final boolean MODERN = modernApiAvailable();
    private static boolean modernApiAvailable() {
        try { Class.forName("java.awt.desktop.AboutHandler", false, MRJApplicationUtils.class.getClassLoader()); return true; }
        catch (ClassNotFoundException absent) { return false; }
    }
    public static synchronized String[] getCompatibilityFailures() { return FAILURES.toArray(new String[0]); }
    public static boolean isMRJToolkitAvailable() { return true; }

    public static void registerAboutHandler(MRJAboutHandler handler) {
        register(handler, "setAboutHandler", "AboutHandler", "handleAbout");
    }
    public static void registerPrefsHandler(MRJPrefsHandler handler) {
        register(handler, "setPreferencesHandler", "PreferencesHandler", "handlePreferences");
    }
    public static void registerQuitHandler(MRJQuitHandler handler) {
        register(handler, "setQuitHandler", "QuitHandler", "handleQuitRequestWith");
    }
    public static void registerOpenDocumentHandler(MRJOpenDocumentHandler handler) {
        register(handler, "setOpenFileHandler", "OpenFilesHandler", "openFiles");
    }
    public static void registerOpenApplicationHandler(MRJOpenApplicationHandler handler) {
        // No original RAID Admin caller. Preserve the existing no-op; reopening is a different event.
    }

    public static void registerPrintDocumentHandler(MRJPrintDocumentHandler handler) {
        // Preserve the original stub's unused entry point.
    }

    static final class RuntimeApi {
        final Class<?> application;
        final Class<?> handler;
        final String getter;
        RuntimeApi(Class<?> application, Class<?> handler, String getter) {
            this.application = application; this.handler = handler; this.getter = getter;
        }
    }
    static RuntimeApi runtimeApi(String handlerName) throws ClassNotFoundException {
        ClassLoader loader = MRJApplicationUtils.class.getClassLoader();
        String prefix = MODERN ? "java.awt.desktop." : "com.apple.eawt.";
        return new RuntimeApi(Class.forName(MODERN ? "java.awt.Desktop" : "com.apple.eawt.Application", false, loader),
                              Class.forName(prefix + handlerName, false, loader), MODERN ? "getDesktop" : "getApplication");
    }

    private static void register(Object handler, String setter, String handlerName, String callback) {
        if (handler == null) return;
        try {
            RuntimeApi api = runtimeApi(handlerName);
            // Check the complete public API before initializing the native application singleton.
            api.application.getMethod(setter, api.handler);
            Object application = api.application.getMethod(api.getter).invoke(null);
            bind(application, api.application, setter, api.handler, handler, callback);
        } catch (Exception failure) {
            registrationFailure(handlerName);
        } catch (LinkageError failure) {
            registrationFailure(handlerName);
        }
    }
    private static void registrationFailure(String handlerName) { recordFailure("registration:" + handlerName); }
    private static synchronized void recordFailure(String code) {
        // Codes come only from fixed bridge call sites, never exception text, files or callback objects.
        if (FAILURES.size() < 8 && FAILURES.add(code)) System.err.println("RAID Admin macOS integration failure: " + code);
    }
    static void bind(Object target, Class<?> application, String setter, Class<?> handlerType,
                     Object legacyHandler, String callback) throws Exception {
        Object proxy = Proxy.newProxyInstance(handlerType.getClassLoader(), new Class<?>[]{handlerType},
                                             new Adapter(legacyHandler, handlerType, callback));
        application.getMethod(setter, handlerType).invoke(target, proxy);
    }
    static final class Adapter implements InvocationHandler {
        private final Object handler;
        private final String callback;
        private final Method callbackMethod;
        Adapter(Object handler, Class<?> handlerType, String callback) throws NoSuchMethodException {
            this.handler = handler; this.callback = callback;
            Method selected = null;
            for (Method method : handlerType.getMethods()) {
                if (method.getName().equals(callback)) {
                    if (selected != null || method.getReturnType() != void.class) throw new NoSuchMethodException("Ambiguous callback");
                    selected = method;
                }
            }
            if (selected == null) throw new NoSuchMethodException("Missing callback");
            callbackMethod = selected;
        }
        public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
            if (method.getDeclaringClass() == Object.class) {
                if (method.getName().equals("equals")) return proxy == args[0];
                if (method.getName().equals("hashCode")) return System.identityHashCode(proxy);
                if (method.getName().equals("toString")) return "RAID Admin macOS callback";
            }
            if (!method.equals(callbackMethod)) throw new UnsupportedOperationException("Unknown macOS callback");
            try {
                if (callback.equals("handleAbout")) {
                    ((MRJAboutHandler) handler).handleAbout();
                } else if (callback.equals("handlePreferences")) {
                    ((MRJPrefsHandler) handler).handlePrefs();
                } else if (callback.equals("handleQuitRequestWith")) {
                    // Original handler saves and exits. Returning or failing leaves the app running.
                    // A failed save must never be bypassed with an independent performQuit decision.
                    try { ((MRJQuitHandler) handler).handleQuit(); }
                    finally { method.getParameterTypes()[1].getMethod("cancelQuit").invoke(args[1]); }
                } else if (callback.equals("openFiles")) {
                    Method getFiles = method.getParameterTypes()[0].getMethod("getFiles");
                    List<?> files = (List<?>) getFiles.invoke(args[0]);
                    for (Object file : files) {
                        try { ((MRJOpenDocumentHandler) handler).handleOpenFile((File) file); }
                        catch (RuntimeException failure) { recordFailure("callback:openFiles"); }
                    }
                }
            } catch (Exception failure) {
                recordFailure("callback:" + callback);
            } catch (LinkageError failure) {
                recordFailure("callback:" + callback);
            }
            return null;
        }
    }
}
