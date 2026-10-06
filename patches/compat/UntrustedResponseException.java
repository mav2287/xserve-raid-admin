package compat;

/** Only the compatibility guards construct this terminal, non-retryable signal. */
public final class UntrustedResponseException extends IllegalArgumentException {
    UntrustedResponseException(String message) { super(message); }
}
