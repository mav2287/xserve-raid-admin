package atomicfixture;
/** Same Java loader call for an empty native baseline and the candidate. */
public final class NativeLoadObservation {
    public static void main(String[] arguments) {
        System.load(System.getProperty("fixture.atomic.library"));
        System.out.println("PASS native load");
    }
}
