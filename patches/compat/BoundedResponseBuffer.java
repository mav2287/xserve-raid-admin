package compat;

/** Checks advertised response size before the legacy eager buffer allocation. */
public final class BoundedResponseBuffer extends java.io.ByteArrayOutputStream {
    public static final int MAX = 16 * 1024 * 1024;
    public BoundedResponseBuffer(int length) { super(checkLength(length)); }
    static int checkLength(int length) {
        if (length > MAX) throw new UntrustedResponseException("Response length exceeds limit");
        return length; // Negative lengths retain the original superclass failure.
    }
}
