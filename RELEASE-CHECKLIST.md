# Release checklist

The current artifact is an unsigned audit build, not a qualified release.

- [x] Preserve installed reference and record source/artifact hashes.
- [x] Hash-lock original-JAR candidate and exact local compiler runtime.
- [x] Demonstrate deterministic unsigned app content on this host.
- [x] Separate compatibility identity in audit bundle and diagnostic report.
- [x] Record file-complete dependency inventory with explicit provenance/license unknowns.
- [x] Accept GitHub repository JAR as the project baseline per user direction.
- [ ] Resolve redistribution rights/notices.
- [ ] Independently reproduce on a second machine with a documented obtainable toolchain.
- [x] Pin and bundle Corretto 8 for both architectures; remove bundled-launcher PATH fallback.
- [ ] Qualify that runtime with native GUI, controller workflows and physical Intel hardware.
- [ ] Qualify runtime FileManager behavior; repair menu/quit/open-document integration and Keychain boundary.
- [ ] Provide visible failures and credential-safe application logging.
- [x] Block external entity resolution while preserving the original embedded plist DTD in offline fixtures.
- [ ] Qualify real controller plist responses and XML resource limits.
- [ ] Validate firmware preflight without transmission, then qualify transfer only with immediate approval.
- [ ] Complete every acceptance row with observable results or evidence-based unsupported status.
- [ ] Obtain safe real response fixtures and full sanitized wire parity, including timing/reuse.
- [ ] Preserve existing Intel and Apple silicon support; qualify physical machines separately.
- [ ] Minimize entitlements; sign with Developer ID, notarize/staple, and validate clean-install Gatekeeper behavior.
- [ ] Generate standard release SBOM/provenance and deterministic distributable archive hashes.
- [ ] Publish compatibility matrix, rollback procedure, Apple credit and remaining limitations.

No signing identity, notarization credential, release upload or installation change was used.


### Audit24 failed-open publication and LaunchServices arguments (local qualification)

Clean application, fixture and package source `8c246e1`, JAR
`9592145c933f611888a00cb159340a86f99d427672483701212023078f823553`.
Fourteen candidate regression gates and 146 unit tests pass; 290 gate source hash
entries are checked against their recorded clean Git commit and current bytes.
Only private AcpxConnection.createConnection changes inside the JAR from audit23:
open a local candidate once, publish only after success. Public timeout handling,
command bytes, polling and retries remain unchanged. Each candidate runtime/mode
covers 26 cases and 34 explicit failed-send attempts; four additional observations
characterize the actual audit23 reference. Eight interpreted negative controls
fail at their exact intended assertions. Direct post-newRequest failure recovery
remains unchanged and is not qualified by this fix.

The pinned-runtime launcher strips only one leading canonical legacy process
serial number, preventing that metadata from selecting CLI mode. All other
arguments remain exact. Its shell tests use a synthetic executable, not app Main.
Paired builds and repeated packages match bytes and file/directory modes on both
architectures; vendor runtime signatures verify. x64 execution is Rosetta, not
physical Intel. Apps remain unsigned and unnotarized. See
[audit scope and reproduction](audit/CONNECTION-PUBLICATION.md) and
[hash-bound evidence](audit/connection-publication-final-integrity.json).

Real hardware acceptance is deferred by the user's latest instruction, until an
actual operational need arises. No controller, production/mounted-volume test,
firmware transfer or installed-app modification occurred. Native GUI workflows,
physical Intel, signed release acceptance and controller behavior are unverified.
Separate offscreen native component probes are development-only, with no windows
shown or app Main/profile/controller access. HTTP remains plaintext.


### Audit25 original Help boundary and local release preparation

Qualified JAR `59087dceed5865b08cef4db0b554a0822837618a07e59b6fd92a2b25880e6393`.
Product/build/package source `82f9c4f`; final stop comparator, units and release
postprocessing source `aee4580`. Fifteen candidate regression gates and 165 units
pass. Two original browser call operands route through a thin Desktop helper;
original localized URLs, UI action filtering, controller code, commands, polling
and retries remain. Browser failures receive deliberate fixed English feedback.
The actual browser/native-dialog path remains unverified.

Paired packages, unsigned deterministic ZIPs, extracted vendor runtime signatures
and repeated schema-validated SPDX inventories pass on both architecture artifacts.
x64 execution is Rosetta. No installed app modification, controller contact or
production/mounted-volume test occurred. Hardware acceptance is deferred until
actual operational need. Native full GUI, physical Intel, signing/notarization,
redistribution rights and remaining documented compatibility/security gaps are
not waived. Model diagnostic credential redaction is a separate development
milestone; its current prototype is not shipping qualification. HTTP is plaintext.
See [audit scope, record hashes and reproduction](audit/HELP-COMPATIBILITY.md),
[the frozen ledger](audit/help-final-integrity.json), and
[archived record locations](audit/help-archival-map.json).

### Audit26 diagnostic confidentiality and offline release evidence

Qualified JAR `7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158`.
Product, build, package and execution source `46dec9e`; reviewed evidence assembler
source `809bdb2`. Sixteen candidate gates and 170 unit tests pass. Paired builds,
packages, repeated unsigned ZIPs, extracted vendor runtime signatures and SPDX
inventories pass for both architecture artifacts. The only JAR delta from audit25
is the exact two-window RaidSystem diagnostic password redaction. Getters,
persistence, controller protocol, polling and retries are preserved.

See [the qualified scope](audit/MODEL-DIAGNOSTIC.md),
[frozen ledger](audit/model-final-integrity.json), and
[archived record map](audit/model-archival-map.json). Native full startup, actual
browser presentation, physical Intel execution, signing/notarization and unresolved
redistribution rights remain unverified. Hardware acceptance is deferred until
actual operational need. No controller contact, production/mounted-volume tests
or installed application modifications occurred. HTTP remains plaintext.

A subsequent preference-write prototype is development work only, separate from
the qualified audit26 artifacts. It is not release evidence until integrated and
qualified with a new candidate and its own complete regression record.


### Audit27 preference save lifetime — completed offline scope

Clean product/fixture/build/package/archive/SPDX source `4735f41` passes seventeen
candidate gates and 175 units. Clean evidence assembly `c7ea088` binds 39 records
and 883 actual Git/source proofs. The only JAR delta from audit26 is an exactly
reversible FileBasedPreferences.store window and one pinned helper. The original
noninterruptible FileOutputStream, XML serializer, UTF-8, explicit flush, paths,
file modes, links, interrupt flags, change counts, catch/monitor behavior remain.
Eight candidate variants cover 18 cases each; eight original controls and sixteen
specific behavioral negatives pass. Successful/Exception/Error stores show zero
FD growth without GC. Valid original loads showed no growth; load is not patched.

Paired ARM/x64 packages, repeated unsigned ZIPs, extracted vendor signatures and
SPDX inventories pass. The original JAR and installed application remain unchanged.
A NIO private-creation prototype was rejected because interrupts could truncate a
file then abort a save the original would complete. Private creation, existing
permissions/ACLs, atomic replacement and at-rest confidentiality remain open.
New close errors and the Writer-allocation/OOM ordering edge are documented.
Hardware is deferred until actual need, not passed. Full native GUI requires a
known disposable macOS environment; physical Intel, signing/notarization and
redistribution acceptance remain unverified. HTTP remains plaintext.
See [scope](audit/PREFERENCE-IO.md), [ledger](audit/preference-final-integrity.json)
and [archive map](audit/preference-archival-map.json).
