package compat;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.net.*;

/** Initial read-timeout setup only: original DNS/TCP timing and port are retained. */
public final class SocketConfiguration {
    private SocketConfiguration() { }
    private static final String MESSAGE = "Connection setup failed";
    private static IOException fixed(IOException error) {
        // Preserve the standard categories consumed by legacy callers without rendering error data.
        IOException clean;
        if (error instanceof UnknownHostException) clean = new UnknownHostException(MESSAGE);
        else if (error instanceof ConnectException) clean = new ConnectException(MESSAGE);
        else if (error instanceof NoRouteToHostException) clean = new NoRouteToHostException(MESSAGE);
        else if (error instanceof SocketTimeoutException) clean = new SocketTimeoutException(MESSAGE);
        else if (error instanceof BindException) clean = new BindException(MESSAGE);
        else if (error instanceof SocketException) clean = new SocketException(MESSAGE);
        else if (error instanceof InterruptedIOException) clean = new InterruptedIOException(MESSAGE);
        else clean = new IOException(MESSAGE);
        if (clean instanceof InterruptedIOException)
            ((InterruptedIOException)clean).bytesTransferred = ((InterruptedIOException)error).bytesTransferred;
        return clean;
    }
    public static Socket open(String host, int readTimeout) throws IOException {
        if (readTimeout <= 0) throw new IOException(MESSAGE);
        Socket socket;
        try {
            // Same constructor as the original, including single-address and null-host behavior.
            socket = new Socket(host, 80);
        } catch (IOException failure) {
            throw fixed(failure);
        }
        return configure(socket, readTimeout);
    }
    static Socket configure(Socket socket, int readTimeout) throws IOException {
        boolean ready = false;
        try {
            if (readTimeout <= 0) throw new IOException(MESSAGE);
            socket.setSoTimeout(readTimeout);
            if (socket.getSoTimeout() != readTimeout) throw new IOException(MESSAGE);
            ready = true;
            return socket;
        } catch (SecurityException denied) {
            throw denied;
        } catch (IOException failure) {
            throw fixed(failure);
        } catch (RuntimeException invalid) {
            throw new IOException(MESSAGE);
        } finally {
            if (!ready) {
                try { socket.close(); } catch (Throwable ignored) { }
            }
        }
    }
}
