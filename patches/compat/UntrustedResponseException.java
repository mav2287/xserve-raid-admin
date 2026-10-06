package compat;

/** Only compatibility guards and terminal transport recovery construct this terminal, non-retryable signal. */
public final class UntrustedResponseException extends IllegalArgumentException {
    UntrustedResponseException(String message) { super(message); }
}
