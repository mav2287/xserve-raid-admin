import fixture.FixtureIdentity;
/** Verify the actual class sources before installing either offline guard. */
public final class ConfigurationRunner {
    public static void main(String[] args) throws Exception {
        FixtureIdentity.verify();
        if (args.length != 1) throw new AssertionError("Fixture selection differs");
        if (args[0].equals("publication")) ConfigurationPublicationObservation.main(new String[0]);
        else if (args[0].equals("direct")) compat.ConfigurationObservation.main(new String[0]);
        else throw new AssertionError("Fixture selection differs");
    }
}
