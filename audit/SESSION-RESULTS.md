# Completed offline milestones and remaining work

Application source: `13ac370` (audit.5). Runtime packager: `b0c1c18`.
Final acquisition and real-firmware fixture source: `b4e79e2` (clean).
XML resource fixture source: `5d882ec` (clean; eight bounded runs with JDK positive controls).
HTTP response fixture source: `c3a3436` (clean; six matching original/candidate/logging runs).

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
- Broader HTTP/ACP error fixtures: 21 direct replies, nine queued replies and two-request retry ordering, on both pinned runtimes. See [HTTP findings](HTTP-RESPONSE-FINDINGS.md); application parser behavior remains unchanged.
- XML provider/resource characterization with JDK positive controls: bundled Xerces ignores the tested JDK settings. Eleven bounded cases also identify a legacy validation stack-growth defect — [XML findings](XML-RESOURCE-FINDINGS.md). audit.6 adds the narrow secure parser layer; see [scope](XML-PARSER-COMPATIBILITY.md).

Validation:

- 38 Python tests pass, including new harness completion/input regressions.
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
- Representative XML size/provider compatibility, HTTP allocation, persistent-stream framing/desynchronization, concurrent queue/cancellation coverage and representative controller replies. HTTP status is ignored and lowercase/missing length can produce empty success; [G12](../GAPS.md#g12--http-response-framing-and-error-interpretation).
- Firmware preflight UI and malformed-package handling; cache/update/restart lifecycle.
- Original retry remains unbounded: a non-idempotent command may repeat after a dropped response, and exhausted firmware streams may send an empty retry body. No retry behavior was changed. Interrupted updates or failed cache restoration could leave caches disabled; this is an unqualified risk, not an observed hardware result.
- Physical Intel-machine and independent-host build qualification.
- Redistribution/license resolution, signing/notarization/Gatekeeper, standard release SBOM and published release.

Hardware available is production/mounted RAID. No controller was contacted, no firmware
was transmitted, no production-volume test was performed, and the installed app was
not modified. Restricted operations still require immediate explicit confirmation.
The Phase 0 hardware/wire-evidence exit gate and full operational acceptance remain open.


Completed audit.6: verified bootstrap XML parser, explicit bounded entity policy,
independent quota rejection codes, accepted-value/depth differential, queue failure
mapping, repeated clean source and architecture bundles. Installed app and immutable
JAR remain unchanged. See [final evidence](XML-PARSER-COMPATIBILITY.md).
Next safe security scope is the original HTTP Content-Length preallocation; its
Claude design review is in progress. No controller contact is needed for this work.


Completed audit.7: response allocation ceiling, independent operand/helper verification, candidate-only oversized input and allowed-ceiling retry tests, and measured terminal-rejection follow-on state. 39 Python tests and both repeated architecture packages pass; [clean evidence](HTTP-ALLOCATION-GUARD.md). Header bounds, connection recovery and native/hardware qualification remain open.
