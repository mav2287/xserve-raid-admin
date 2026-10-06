package compat;

import java.io.InputStream;
import java.io.IOException;

/** Per-response header budget; mirrors the unchanged legacy readLine automaton. */
public final class BoundedHeaderStream extends InputStream {
    private final InputStream source;
    private int bytes, characters, lines;
    private boolean newline, body, rejected;
    private BoundedHeaderStream(InputStream source) { this.source=source; }
    public static InputStream wrap(InputStream source) {
        return source==null ? null : new BoundedHeaderStream(source);
    }
    private void reject() { rejected=true; throw new UntrustedResponseException("Response headers exceed limit"); }
    private void finish() {
        if(lines>0 && characters==0) body=true;
        lines++;characters=0;newline=false;
    }
    @Override public int read() throws IOException {
        if(rejected) reject();
        int value=source.read();
        if(body) return value;
        if(value==-1) {finish();return value;}
        if(++bytes>1048576) reject();
        if(value==10 || value==13) {
            if(newline) finish(); else newline=true;
        } else {
            // Status + 128 fields are complete: line 130 may only be blank.
            if(lines>=129 || ++characters>65536) reject();
        }
        return value;
    }
    @Override public int available() throws IOException { return source.available(); }
    @Override public void close() throws IOException { source.close(); }
}
