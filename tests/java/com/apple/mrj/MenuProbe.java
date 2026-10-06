package com.apple.mrj;

import fixture.OfflineGuard;
import java.io.File;
import java.util.*;
import java.lang.reflect.Proxy;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

/** Exercises the reflection bridge only: never initializes Desktop or the native app. */
public final class MenuProbe {
    public interface About { void handleAbout(Object event); void unexpected(); }
    public interface Prefs { void handlePreferences(Object event); }
    public interface Quit { void handleQuitRequestWith(Object event, QuitResponse response); }
    public interface OpenFiles { void openFiles(FilesEvent event); }
    public interface QuitResponse { void cancelQuit(); void performQuit(); }
    private static final class PrivateResponse implements QuitResponse {
        int cancellations; int performed;
        public void cancelQuit() { cancellations++; }
        public void performQuit() { performed++; }
    }
    public static final class FilesEvent {
        final List<File> files;
        FilesEvent(List<File> files) { this.files = files; }
        public List<File> getFiles() { return files; }
    }
    public static final class Backend {
        About about; Prefs prefs; Quit quit; OpenFiles open;
        public void setAboutHandler(About h) { about = h; }
        public void setPreferencesHandler(Prefs h) { prefs = h; }
        public void setQuitHandler(Quit h) { quit = h; }
        public void setOpenFileHandler(OpenFiles h) { open = h; }
    }
    private static void check(boolean value) { if (!value) throw new AssertionError("Menu regression failed"); }
    public static void main(String[] args) throws Exception {
        ByteArrayOutputStream errors = new ByteArrayOutputStream();
        System.setErr(new PrintStream(errors, true, "UTF-8"));
        OfflineGuard.install();
        boolean java8 = System.getProperty("java.version").startsWith("1.8.");
        for (String name : new String[]{"AboutHandler", "PreferencesHandler", "QuitHandler", "OpenFilesHandler"}) {
            MRJApplicationUtils.RuntimeApi api = MRJApplicationUtils.runtimeApi(name);
            String setter = name.equals("AboutHandler") ? "setAboutHandler" : name.equals("PreferencesHandler") ? "setPreferencesHandler" : name.equals("QuitHandler") ? "setQuitHandler" : "setOpenFileHandler";
            api.application.getMethod(setter, api.handler);
            api.application.getMethod(api.getter);
            String callback = name.equals("AboutHandler") ? "handleAbout" : name.equals("PreferencesHandler") ? "handlePreferences" : name.equals("QuitHandler") ? "handleQuitRequestWith" : "openFiles";
            Object actualProxy = Proxy.newProxyInstance(api.handler.getClassLoader(), new Class<?>[]{api.handler},
                new MRJApplicationUtils.Adapter(new Object(), api.handler, callback));
            check(actualProxy.equals(actualProxy));
            check(actualProxy.toString().equals("RAID Admin macOS callback"));
            check(api.handler.getName().equals((java8 ? "com.apple.eawt." : "java.awt.desktop.") + name));
        }
        final int[] calls = new int[3];
        final List<File> received = new ArrayList<File>();
        Backend backend = new Backend();
        final PrivateResponse response = new PrivateResponse();
        MRJApplicationUtils.bind(backend, Backend.class, "setAboutHandler", About.class,
            new MRJAboutHandler() { public void handleAbout() { calls[0]++; } }, "handleAbout");
        MRJApplicationUtils.bind(backend, Backend.class, "setPreferencesHandler", Prefs.class,
            new MRJPrefsHandler() { public void handlePrefs() { calls[1]++; } }, "handlePreferences");
        MRJApplicationUtils.bind(backend, Backend.class, "setQuitHandler", Quit.class,
            new MRJQuitHandler() { public void handleQuit() { check(response.cancellations == 0); calls[2]++; } }, "handleQuitRequestWith");
        MRJApplicationUtils.bind(backend, Backend.class, "setOpenFileHandler", OpenFiles.class,
            new MRJOpenDocumentHandler() { public void handleOpenFile(File file) { received.add(file); } }, "openFiles");
        check(backend.about.equals(backend.about)); check(!backend.about.equals(null));
        check(!backend.about.equals(backend.prefs)); check(backend.about.hashCode() == System.identityHashCode(backend.about));
        check(backend.about.toString().equals("RAID Admin macOS callback")); check(Arrays.equals(calls, new int[3]));
        try { backend.about.unexpected(); throw new AssertionError("Unknown method dispatched"); }
        catch (UnsupportedOperationException expected) { }
        backend.about.handleAbout(null); backend.prefs.handlePreferences(null);
        backend.quit.handleQuitRequestWith(null, response);
        check(Arrays.equals(calls, new int[]{1,1,1})); check(response.cancellations == 1);
        List<File> files = Arrays.asList(new File("synthetic-one.xfb"), new File("synthetic-two.xfb"));
        backend.open.openFiles(new FilesEvent(files)); check(received.equals(files));
        MRJApplicationUtils.bind(backend, Backend.class, "setQuitHandler", Quit.class,
            new MRJQuitHandler() { public void handleQuit() { throw new IllegalStateException("fixture"); } }, "handleQuitRequestWith");
        backend.quit.handleQuitRequestWith(null, response);
        check(Arrays.equals(MRJApplicationUtils.getCompatibilityFailures(), new String[]{"callback:handleQuitRequestWith"}));
        check(response.cancellations == 2 && response.performed == 0);
        backend.quit.handleQuitRequestWith(null, response);
        check(response.cancellations == 3 && response.performed == 0);
        check(errors.toString("UTF-8").equals("RAID Admin macOS integration failure: callback:handleQuitRequestWith\n"));
        received.clear();
        MRJApplicationUtils.bind(backend, Backend.class, "setOpenFileHandler", OpenFiles.class,
            new MRJOpenDocumentHandler() { public void handleOpenFile(File file) {
                if (received.isEmpty()) { received.add(file); throw new IllegalStateException("synthetic-private-message"); }
                received.add(file);
            } }, "openFiles");
        backend.open.openFiles(new FilesEvent(files)); check(received.equals(files));
        check(!errors.toString("UTF-8").contains("synthetic-private-message"));
        OfflineGuard.assertUntouched();
        System.out.println("PASS runtime_api=" + (java8 ? "eawt" : "desktop") + "; About/Preferences/Quit/OpenFiles callbacks; proxy identity; quit cancellation; guarded operations=0");
    }
}
