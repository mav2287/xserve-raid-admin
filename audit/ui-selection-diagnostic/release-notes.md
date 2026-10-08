Audit30 removes an artificial 68-millisecond pause from information-view array-row clicks and internal Array/Drive view switches. Rapid clicks previously queued waits on the drawing thread before selection actions ran. The helper uses the same original Swing click sequence with zero simulated press delay, only inside the information view. Outside that view, shared row behavior keeps its original timing.

Download the **aarch64 ZIP for Apple silicon** or **x64 ZIP for Intel**. Both include Amazon Corretto 8.504.04.1; no separate Java installation is needed. These packages are **unsigned and unnotarized**.

Two original listener classes have three exact invocation substitutions; one small Java 8 helper is added. Full-class inverses and every other JAR entry are verified. Audit29's cleared-selection fix remains. There is no constructor, renderer, controller command, polling, retry, launcher, native-helper or runtime change. The simulated button-press flash is shortened on these programmatic information-view paths.

Validation: two equal common rebuilds; repeated ZIP/extraction/mode/vendor-signature/SPDX byte checks for each architecture; four guarded before/after runs with 300 mixed selection rounds each; selected details/cards and all 14 icon samples; separate 12-sample row-click and mode-switch checks with matching ordered button-state/action traces (no item transitions); deterministic zero-delay argument assertions through the actual patched listeners, with the original 68 retained outside the information view; 196 Python tests, six existing skips. Claude independently diagnosed the delay and reviewed the fix and tests. ARM ran natively; x64 ran under Rosetta, not physical Intel.

Tests use synthetic ancestry/model data and bypass the full information-pane constructor to avoid profiles. Actual containment is established by original constructor bytecode. The removed wait is proven; the user's remaining on-screen symptom needs confirmation with the new bundle. Native presentation, full GUI/controller workflows, physical Intel, Gatekeeper, signing/notarization and future OS behavior remain unqualified. No real profiles, credentials, controller commands, production volumes or installed-app changes were used for this fix. Legacy HTTP is plaintext.

Product and package source: `1a2ef1f35ad26dc28821ab19ba3677a2280312b9`.
Common JAR SHA-256: `3875edc404c7773d602fdb834bf8090dcb73b53a30d6306bc2fb09951a542059`.
Later documentation/tag commits add evidence, not a new product build. Previous releases and tags remain unchanged.

`SHA256SUMS.txt` covers the exact uploaded filenames. Architecture-specific provenance, SPDX SBOM and observations accompany the packages. [Evidence and reproduction](https://github.com/mav2287/xserve-raid-admin/blob/v1.5.1-modern.audit.30/audit/ARRAY-CLICK.md).

To check the improvement, use normal Array & Drives selections, including rapid side changes and drive-to-array changes. No firmware, RAID, disk, cache/network or controller power operation is needed.

### Selection and boundary follow-up (2026-10-08)

An operator-observed native Apple silicon test passed a **60-step synthetic sequence at one-second intervals**, covering all 14 drive centers, selected shared boundaries and corners, inert off-label hits, the divider gap, and captured-release drags. Expected selections, icon data, drag cleanup and unchanged synthetic model checks passed, with no stale Java paint generations at the checks and no guarded prohibited operations. The operator reported that it looked fine. A separate three-second original-path test was also smooth.

These tests use the **unchanged original renderer** in an isolated fixture. They do not establish that the earlier intermittent highlight issue in the complete application is fixed. OS pointer routing, the full information-pane hierarchy and framebuffer timing were not measured. This follow-up fixture ran on native Apple silicon only; Intel/x64 was not rerun for it. The existing ARM/Rosetta and package qualification above remains its separate record.

This is an evidence and documentation update: **both downloadable architecture packages, their checksums, SBOM/provenance, the common JAR and the release tag are unchanged**. No new renderer patch or binary release is implied. No controller commands or production-volume tests were performed. Both ZIPs still include their matching Java runtime; no separate Corretto download is needed.

[Follow-up source, results and limitations](https://github.com/mav2287/xserve-raid-admin/blob/619658557631fb73002454dfe3cbb99f674ed109/audit/UI-SELECTION-DIAGNOSTIC.md).

