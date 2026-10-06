/** Runtime-provider check only; no keys, sockets, controller or application initialization. */
public final class RuntimeProbe {
    public static void main(String[] args) throws Exception {
        if (javax.crypto.Cipher.getInstance("AES") == null) throw new AssertionError("Vendor provider absent");
        if (!new java.util.Locale("fr").getDisplayLanguage(java.util.Locale.FRENCH).equals("fran\u00e7ais"))
            throw new AssertionError("Vendor locale data unavailable");
        System.out.println("PASS vendor crypto-provider availability and French locale data; no encryption/network operation performed");
    }
}
