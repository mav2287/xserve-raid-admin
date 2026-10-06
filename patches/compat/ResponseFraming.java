package compat;

import com.apple.xsr.net.HttpResponse;

/** Enforces a single explicit length supported by the legacy response reader. */
public final class ResponseFraming {
    private ResponseFraming() { }
    /** No peer data can enter this terminal rejection. */
    public static RuntimeException invalidHeader() {
        return new UntrustedResponseException("Response header is invalid");
    }
    private static boolean header(String name,String expected) {
        if(name.length()!=expected.length())return false;
        for(int i=0;i<name.length();i++) {
            char actual=name.charAt(i),wanted=expected.charAt(i);
            if(actual>='A' && actual<='Z')actual=(char)(actual+32);
            if(actual!=wanted)return false;
        }
        return true;
    }
    public static void setHeader(HttpResponse response,String name,String value) {
        if(header(name,"transfer-encoding"))
            throw new UntrustedResponseException("Response transfer encoding is unsupported");
        if(header(name,"content-length")) {
            if(response.getHeaderField("Content-Length")!=null)
                throw new UntrustedResponseException("Response length is ambiguous");
            response.setHeaderField("Content-Length",value);
        }else response.setHeaderField(name,value);
    }
    public static String lengthHeader(HttpResponse response,String name) {
        String value=response.getHeaderField(name);
        if(value==null)throw new UntrustedResponseException("Response length is missing");
        return value;
    }
}
