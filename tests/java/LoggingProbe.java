import fixture.OfflineGuard;
import java.io.*;
import java.util.*;
import org.apache.log4j.*;

/** Loads the candidate JAR's real logging configuration under a no-IO guard. */
public final class LoggingProbe {
    private static void check(boolean value) { if (!value) throw new AssertionError("Logging fixture mismatch"); }
    private static final class Hostile {
        @Override public String toString() { throw new AssertionError("Message rendered"); }
    }
    private static final class HostileThrowable extends RuntimeException {
        @Override public String getMessage() { throw new AssertionError("Throwable message read"); }
        @Override public String toString() { throw new AssertionError("Throwable rendered"); }
        @Override public void printStackTrace() { throw new AssertionError("Stack rendered"); }
        @Override public void printStackTrace(PrintStream stream) { throw new AssertionError("Stack rendered"); }
        @Override public void printStackTrace(PrintWriter writer) { throw new AssertionError("Stack rendered"); }
    }
    private static int appenders(Category logger) {
        int count = 0;
        Enumeration values = logger.getAllAppenders();
        while (values.hasMoreElements()) {
            Object appender = values.nextElement(); count++;
            check(appender.getClass().getName().equals("compat.SafeLogAppender"));
        }
        return count;
    }
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        PrintStream originalOut = System.out, originalErr = System.err;
        String originalThreadName = Thread.currentThread().getName();
        ByteArrayOutputStream stdout = new ByteArrayOutputStream(), stderr = new ByteArrayOutputStream();
        boolean failing = args.length == 1 && args[0].equals("write-failure");
        boolean closedFirst = args.length == 1 && args[0].equals("closed-first");
        try {
            System.setOut(new PrintStream(stdout,true,"UTF-8"));
            System.setErr(failing ? new PrintStream(stderr) {
                @Override public void println(String value) { throw new IllegalStateException("synthetic-private-write-failure"); }
            } : new PrintStream(stderr,true,"UTF-8"));
            Thread.currentThread().setName("synthetic-private-thread");
            NDC.push("synthetic-private-ndc"); MDC.put("fixture", "synthetic-private-mdc");
            Logger root = Logger.getRootLogger();
            check(root.getEffectiveLevel().toInt() == Priority.ERROR_INT);
            check(appenders(root) == 1);
            Logger logger = Logger.getLogger("synthetic-private-logger");
            logger.setLevel(Level.DEBUG);
            Object message = new Hostile(); Throwable problem = new HostileThrowable();
            logger.debug(message,problem); logger.info(message,problem); logger.warn(message,problem);
            check(stderr.size() == 0 && stdout.size() == 0);
            if (closedFirst) {
                Enumeration closing = root.getAllAppenders();
                while (closing.hasMoreElements()) ((Appender)closing.nextElement()).close();
                logger.error(message,problem); logger.fatal(message,problem);
                check(stderr.size() == 0 && stdout.size() == 0);
            } else {
            logger.log(Priority.ERROR,message,problem);
            logger.log(Priority.FATAL,message,problem);
            logger.error("synthetic-private-password",problem); logger.fatal(message,problem);
            PropertyConfigurator.configure(LoggingProbe.class.getClassLoader().getResource("log4j.properties"));
            logger.error(message,problem); logger.fatal(message,problem);
            check(appenders(root) == 1);
            Enumeration loggers = LogManager.getCurrentLoggers();
            while (loggers.hasMoreElements()) appenders((Category)loggers.nextElement());
            Enumeration values = root.getAllAppenders();
            while (values.hasMoreElements()) ((Appender)values.nextElement()).close();
            logger.error(message,problem);
            check(stdout.size() == 0);
            check(stderr.toString("UTF-8").equals(failing ? "" : "RAID_ADMIN_ERROR\nRAID_ADMIN_FATAL\n"));
            }
        } finally {
            NDC.remove(); MDC.remove("fixture");
            System.setOut(originalOut); System.setErr(originalErr);
            Thread.currentThread().setName(originalThreadName);
            OfflineGuard.assertUntouched();
        }
        System.out.println("PASS safe_log_codes; no_message_or_exception_rendering; bounded_across_reconfiguration; guarded_operations=0; write_failure=" + failing + "; closed_first=" + closedFirst);
    }
}
