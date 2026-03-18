package com.apple.mrj;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.lang.reflect.InvocationHandler;

/**
 * Replacement for the non-functional MRJApplicationUtils stub bundled in the original JAR.
 * Bridges the old MRJ handler API to modern java.awt.Desktop (Java 9+) or
 * com.apple.eawt.Application (Java 8) via reflection.
 */
public class MRJApplicationUtils {

    public static boolean isMRJToolkitAvailable() {
        return true;
    }

    public static void registerAboutHandler(final MRJAboutHandler handler) {
        try {
            Object app = getDesktopOrEAWTApp();
            if (app != null && handler != null) {
                setHandler(app, "setAboutHandler", "java.awt.desktop.AboutHandler",
                    new InvocationHandler() {
                        public Object invoke(Object proxy, Method method, Object[] args) {
                            handler.handleAbout();
                            return null;
                        }
                    });
            }
        } catch (Exception e) { /* silently ignore */ }
    }

    public static void registerQuitHandler(final MRJQuitHandler handler) {
        // Intentional no-op: custom quit handlers conflict with modern macOS window management.
        // The default quit behavior (Cmd+Q) works correctly without a custom handler.
    }

    public static void registerPrefsHandler(final MRJPrefsHandler handler) {
        try {
            Object app = getDesktopOrEAWTApp();
            if (app != null && handler != null) {
                setHandler(app, "setPreferencesHandler", "java.awt.desktop.PreferencesHandler",
                    new InvocationHandler() {
                        public Object invoke(Object proxy, Method method, Object[] args) {
                            handler.handlePrefs();
                            return null;
                        }
                    });
            }
        } catch (Exception e) { /* silently ignore */ }
    }

    public static void registerOpenDocumentHandler(final MRJOpenDocumentHandler handler) {
        // No-op: complex to bridge and rarely used
    }

    public static void registerOpenApplicationHandler(final MRJOpenApplicationHandler handler) {
        // No-op
    }

    private static Object getDesktopOrEAWTApp() {
        try {
            Class<?> desktopClass = Class.forName("java.awt.Desktop");
            Method getDesktop = desktopClass.getMethod("getDesktop");
            return getDesktop.invoke(null);
        } catch (Exception e) {
            try {
                Class<?> appClass = Class.forName("com.apple.eawt.Application");
                Method getApp = appClass.getMethod("getApplication");
                return getApp.invoke(null);
            } catch (Exception e2) {
                return null;
            }
        }
    }

    private static void setHandler(Object target, String setterName, String handlerClassName, InvocationHandler ih) {
        try {
            Class<?> handlerInterface = Class.forName(handlerClassName);
            Object proxy = Proxy.newProxyInstance(
                handlerInterface.getClassLoader(),
                new Class<?>[]{ handlerInterface },
                ih
            );
            Method setter = target.getClass().getMethod(setterName, handlerInterface);
            setter.invoke(target, proxy);
        } catch (Exception e) { /* silently ignore */ }
    }
}
