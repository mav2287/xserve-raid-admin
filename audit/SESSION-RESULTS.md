# Completed offline milestones and remaining work

Application source: `13ac370` (audit.5). Runtime packager: `b0c1c18`.
Final acquisition and real-firmware fixture source: `b4e79e2` (clean).

Completed with actual Claude CLI model consultation plus the recorded automated checks (not independent human review or operational qualification):

- MRJ Desktop lookup and macOS menu/quit/OpenFiles compatibility bridges.
- External plist entity blocking with the exact original embedded DTD retained.
- Two request diagnostic methods redacted; all other methods in those classes preserved.
- Bounded fixed-code ERROR/FATAL reporting with no event rendering.
- One deterministic build entry point and pinned, vendor-verified runtime packages for both existing architectures.
- Schema-aware diagnostics checked against repository anchors, including exact file and directory sets.
- Synthetic ACP/retry, archive, parsing, logging and OS-adapter fixtures.
- Apple-served distribution acquisition: its JAR exactly matches the immutable reference.
- Hash-only reads of the accompanying real firmware package through the unchanged wrapper, without updater/model/command construction.

Validation:

- 35 Python tests pass.
- Independent javap preservation checks and guarded Java fixtures pass.
- Both architecture bundles reproduce with identical bytes and permissions.
- arm64 and x64 pinned-runtime fixtures pass; x64 runs under Rosetta on this arm64 host.
- Java 11 arm64/x64 observations also pass the limited fixtures.
- Original/candidate synthetic memory-only transport observations match with logging OFF and candidate logging configured.
- Real firmware image hashes agree between Python and Java on both pinned runtimes.
- Installed application still matches its preserved reference; original JAR hash remains unchanged.

Not complete:

- Native UI/menu/Finder/preference workflows in an isolated test environment.
- Keychain/native credential integration and visible in-app failure states.
- Representative controller responses, discovery/authentication/polling/reconnect/sleep/wake and long-duration behavior.
- XML resource limits and broader malformed-response/queue-order coverage.
- Firmware preflight UI and malformed-package handling; cache/update/restart lifecycle.
- Original retry remains unbounded: a non-idempotent command may repeat after a dropped response, and exhausted firmware streams may send an empty retry body. No retry behavior was changed. Interrupted updates or failed cache restoration could leave caches disabled; this is an unqualified risk, not an observed hardware result.
- Physical Intel-machine and independent-host build qualification.
- Redistribution/license resolution, signing/notarization/Gatekeeper, standard release SBOM and published release.

Hardware available is production/mounted RAID. No controller was contacted, no firmware
was transmitted, no production-volume test was performed, and the installed app was
not modified. Restricted operations still require immediate explicit confirmation.
The Phase 0 hardware/wire-evidence exit gate and full operational acceptance remain open.
