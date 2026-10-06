# Diagnostic version-label correction

The audit.14 app and packages are unchanged. Allowlisted diagnostics previously
reported audit.12/13/14 as unrecognized because their fixed version list ended at
11. Supported labels now derive from trusted BUNDLE_VERSION with the fixed Apple
compatibility prefix. VERSION/BUNDLE_VERSION alignment is tested.

Only known strings are emitted; invented, zero-padded, future and non-string values
are fixed unrecognized. Lists/dictionaries cannot bypass the type guard. A version
label remains a manifest claim: compatibility_version_matches_reviewed_artifact
is true only if the independent artifact checks pass and the label equals the
current trusted VERSION. Known historical claims on the current artifact explicitly
mismatch. Error fallback returns false. No Java, preferences, controller traffic
or application writes occur.

[Claude design](claude-review/DIAGNOSTIC-VERSION-DESIGN.txt) and
[implementation review](claude-review/DIAGNOSTIC-VERSION-IMPLEMENTATION.txt)
found no blockers. Both recommended optional cases were added: current-label
artifact tampering and consistent false fallback. All 85 Python tests pass before
commit. Clean packaged diagnostic observations follow this tooling commit;
application JAR and package fingerprints remain unchanged.
