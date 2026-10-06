package compat;

/** Checks advertised response size before the legacy eager buffer allocation. */
public final class BoundedResponseBuffer extends java.io.ByteArrayOutputStream {
    public static final int MAX = 16 * 1024 * 1024;
    public BoundedResponseBuffer(int length) { super(checkLength(length)); }
    public static int parseLength(String value) {
        try { return Integer.parseInt(value); }
        catch (NumberFormatException ignored) {
            throw new UntrustedResponseException("Response length is invalid");
        }
    }
    static int checkLength(int length) {
        if (length < 0) throw new UntrustedResponseException("Response length is invalid");
        if (length > MAX) throw new UntrustedResponseException("Response length exceeds limit");
        return length;
    }
}
