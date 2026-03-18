package sun.io;

/**
 * Shim for sun.io.MalformedInputException which was removed from modern JDKs.
 * The original CommunicationsManager.class catches this exception type in its
 * network dispatch loop. Without this shim, the JVM throws NoClassDefFoundError
 * and the entire communications thread crashes.
 */
public class MalformedInputException extends java.nio.charset.CharacterCodingException {
    public MalformedInputException() {
        super();
    }

    public MalformedInputException(String message) {
        super();
    }
}
