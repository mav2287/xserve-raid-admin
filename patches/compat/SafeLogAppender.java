package compat;

import org.apache.log4j.AppenderSkeleton;
import org.apache.log4j.Priority;
import org.apache.log4j.spi.LoggingEvent;

/** Bounded error signals only: no message, exception, logger name or context rendering. */
public final class SafeLogAppender extends AppenderSkeleton {
    private static boolean errorReported;
    private static boolean fatalReported;

    private static synchronized boolean claim(int level) {
        if (level == Priority.ERROR_INT && !errorReported) { errorReported = true; return true; }
        if (level == Priority.FATAL_INT && !fatalReported) { fatalReported = true; return true; }
        return false;
    }

    @Override public synchronized void doAppend(LoggingEvent event) {
        // Deliberately bypass inherited filters/layout/error-handler and closed-appender logging.
        if (!closed && event != null) append(event);
    }

    @Override protected void append(LoggingEvent event) {
        try {
            int level = event.getLevel().toInt();
            if (claim(level)) System.err.println(level == Priority.ERROR_INT ? "RAID_ADMIN_ERROR" : "RAID_ADMIN_FATAL");
        } catch (RuntimeException ignored) {
            // Diagnostics must not replace the original application's error handling.
        }
    }

    @Override public synchronized void close() { closed = true; }
    @Override public boolean requiresLayout() { return false; }
}
