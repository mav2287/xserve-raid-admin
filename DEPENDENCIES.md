# Dependencies and SBOM

[audit/sbom.json](audit/sbom.json) is a machine-readable, file-complete inventory of the 3,043 non-directory entries in the immutable candidate JAR. It is a project schema, not falsely labeled SPDX/CycloneDX compliant. It includes every entry hash, component aggregate hashes, observed versions, notice evidence and explicit unknowns. The original JAR hash is the acquisition anchor; aggregate component hashes are not upstream distribution checksums.

| Component | Observed version | Evidence / license status |
|---|---|---|
| Apple application/support | 1.5.1, development 1.5.1GMc5 | Versions.properties; Apple license images present; matches JAR in Apple-served 1.5.1 archive; redistribution rights unresolved |
| JmDNS | 0.2 | JmDNS static VERSION initializer; license not established from this intake |
| Xerces | 2.0.0 | `org.apache.xerces.impl.Version` literal; exact distribution/license provenance unresolved |
| Xalan | 2.3.0 | XSLProcessorVersion initializer; XML/XPath helpers bundled; exact distribution/license provenance unresolved |
| Log4j | 1.x, exact release unresolved | Legacy namespace/API; original root OFF, audit.5 fixed-code adapter; do not assert a precise version/CVE from package names |
| BCEL | Unresolved | Bundled BCEL.LICENSE.txt states Apache Software License 1.1 |
| Apache regexp | Unresolved | regexp.LICENSE.txt states Apache Software License 1.1 |
| JLex | Unresolved | Bundled custom permissive notice; retain full text |
| Java CUP and runtime | 0.10j | java_cup.version constants; separate custom generator/runtime notices |
| W3C DOM, SAX, JAXP and HTML/WML implementations | Mixed/unresolved | Vendored namespaces, some may be superseded by JDK parent loading |
| Chaotic plist/preferences/rendezvous/Base64 support | Unresolved | Bundled classes; no independent release/notice provenance established |
| Stanford BrowserLauncher | Unresolved | Bundled class; version/license unresolved |
| Compatibility Java sources and method transformer | Recorded source commit and per-file hashes | No repository-wide license file found; no new third-party library |
| Build/runtime JDK used in audit | Amazon Corretto 8 1.8.0_362 arm64 | Exact 224-file lock and aggregate hash in jdk-lock.json; build compiler only; bundled release runtime listed below |
| Python | Recorded per build manifest | Standard library only for audit tools; no pip dependency needed |
| macOS tools | Host supplied | Upstream uses bash, java_home, jar/javac, codesign; launcher uses osascript, sips, and open via FileManager |

The deterministic builder hashes its own script, source patches, template build script and JDK lock in provenance. It avoids dependency downloads. The launcher and icons are hashed individually. No native helper is added. The audit-only bundle omits a runtime; pinned runtime package hashes and full file inventories are recorded separately below.

Do not replace bundled libraries wholesale without classloading, XML compatibility and wire regression tests. audit.4 blocks external XML resolution and redacts the two request diagnostic methods. Remaining gaps include real-response XML compatibility and HTTP allocation, application-wide error reporting, old discovery APIs and unqualified native runtime behavior. No current vulnerability-database audit or legal redistribution determination was performed. Before distribution, resolve all NOASSERTION licenses, generate a standard release SBOM, and qualify a maintained runtime independently.

The user accepts the GitHub repository JAR as the authoritative project baseline.
Historical digest discrepancies and independent Apple acquisition evidence do
not block the authorized compatibility work.

## Pinned runtime candidate

Amazon Corretto 8.504.04.1 is now pinned for macOS aarch64 and x64 in
`audit/runtime-lock.json`, with archive URLs/hashes, per-file hashes and vendor
permission bits. Vendor signatures verify as `com.amazon.corretto.8`, Team
`94KV3E626L`. Archives were obtained from the [official download catalog](https://docs.aws.amazon.com/corretto/latest/corretto-8-ug/downloads-list.html);
future builds use recorded versioned URLs and hashes, never a floating latest URL.
The full vendor JDK bundle and its LICENSE, ASSEMBLY_EXCEPTION and
THIRD_PARTY_README files are preserved. Public redistribution/source-availability
requirements and the application's legacy dependencies still require resolution
before publication. The runtime is local to the build; no system JDK was replaced.

## Apple-served acquisition evidence

`audit/apple-distribution-acquisition.json` records the bounded HTTPS acquisition
of the [1.5.1 distribution](https://download.info.apple.com/Mac_OS_X/061-2942.20070123.xRaTg/RAIDAdmin1.5.1.tar.gz),
archive/member hashes, response metadata and exact inspection tool identity.
Its JAR matches the immutable repository reference. Firmware binaries remain
in ignored local cache; only metadata and hashes enter Git. This narrows original
acquisition uncertainty without asserting redistribution rights or a historical
package signature.

The clean follow-up acquisition in `audit/apple-distribution-confirmation.json`
records the explicit CA bundle hash, OpenSSL version and loaded module source
hashes, and returns exactly the same archive bytes. The first tool version is
traceable to commit `41ecbde`; its recorded hash matches that Git version.


## audit.6 security refinement

The user explicitly prioritized safe closure of the XML parser security gap.
A narrow parser-construction override selects the pinned bootstrap JDK provider,
retains the original plist Handler / DTD / serializer, enables validation, enforces
and verifies explicit quotas, and refuses external DTD/schema access. Provider
replacement and intentional security rejections are recorded in
[audit.6 parser evidence](audit/XML-PARSER-COMPATIBILITY.md). Controller commands,
polling and retry timing are unchanged. Production hardware approval remains absent.
Safe work continues with HTTP allocation/framing, firmware preflight and isolated
native UI qualification; successful parser fixtures do not close release acceptance.


Read-only vendor freshness observation on 2026-10-06: both macOS permanent download URLs resolve to the already pinned 8.504.04.1 version. See [observation](audit/runtime-current-observation.json) and the [official catalog](https://docs.aws.amazon.com/corretto/latest/corretto-8-ug/downloads-list.html). Builds retain exact versioned URLs and hashes. This is not a vulnerability-database or complete security audit. audit.7 adds no third-party dependency.


## audit.9 security rejection recovery refinement

Body/header ceiling violations now close the rejected connection and return one
terminal -102 callback without replay. The next distinct queued command uses the
unchanged reconnect path; bounded offline fixtures pass on both architectures.
G14 is partially addressed: ordinary invalid numeric/negative lengths still leave
stale state and require the next security refinement. CLI direct-send lifecycle,
idle/paused polling, real TCP timing and controller behavior remain unqualified.
No third-party dependency is added. See [scope and evidence](audit/REJECTION-RECOVERY.md).


## audit.10 malformed length security refinement

Malformed, overflowing and negative exact Content-Length declarations now fail
once through the reviewed retirement path, with no resend and a fixed secret-free
message. The next distinct queued command succeeds through a fresh memory
connection. Valid Integer.parseInt parsing and original ordinary IO retries remain.
G14's demonstrated length-rejection stale state is addressed in bounded fixtures;
real/idle reconnect timing and CLI lifecycle remain unqualified. G10/G12 framing
and ambiguous IO replay remain open. Both runtime packages reproduce; no hardware,
installed-app modification or third-party dependency change occurred. See
[scope and evidence](audit/INVALID-LENGTH-GUARD.md).


## audit.11 explicit response framing

One ASCII-case-insensitive Content-Length is accepted; missing or duplicate
lengths and any Transfer-Encoding use a fixed terminal marker, close the
connection and return one -102 without failed-command replay in measured
send/dispatch fixtures. Single lowercase length now parses the actual plist;
canonical replies, legitimate zero length, ACP error codes and original ordinary
IO retries remain. Two same-length HttpResponse call substitutions and one small
helper implement the boundary. No third-party dependency is added.

G12 is only partially addressed: declared-zero with extra bytes remains a
measured association gap, status handling and malformed ordinary IO remain
legacy behavior, and no firmware capture proves single-length compatibility.
The HTTP protocol is plaintext. Native UI, physical Intel, hardware, signing and
release acceptance remain open. See [reviewed scope](audit/RESPONSE-FRAMING-POLICY.md).


## Offline firmware known-package foundation

A standalone bounded immutable-snapshot validator accepts only the checked Apple
1.5.1 XFB digest and emits reviewed public metadata. Unknown input never reaches
ZIP parsing/inflation; CLI/read errors use fixed codes. No application bytes,
updater calls, controller/cache operation or transmission change. This is partial
preflight groundwork: generic validation, Java send-time binding, confirmation
UI and hardware/version qualification remain open. See
[scope and review](audit/FIRMWARE-PREFLIGHT-FOUNDATION.md).


## audit.12 malformed-header security boundary

Colonless and leading-colon headers now produce a fixed terminal rejection,
retire the connection and return one -102 callback without command replay in
bounded memory fixtures. See [audit.12 evidence](audit/MALFORMED-HEADER-GUARD.md).
The controller outcome is unconfirmed; -102 does not prove a mutation was not applied.
Valid response behavior and unrelated IO retry paths remain unchanged. Null-message
IO worker death, other ambiguous mutation retries, incorrect single lengths,
trailing bytes, status interpretation and real controller/UI/CLI qualification
remain open. No installed application or production hardware is modified.


## audit.13 null-message dispatch recovery

The null-message IOException worker-death case now returns one fixed -102 with
an unconfirmed controller outcome and retires the connection in bounded fixtures.
A distinct next request succeeds. See [audit.13 evidence](audit/NULL-IO-RECOVERY.md).
Nonnull IO classification and retries remain original; broader ambiguous mutation
replay, GUI sequencing and real sockets remain open. Reflection-metadata failure
shuts dispatch down; original exit closes the source after terminal callbacks.
No production hardware, mounted volumes or installed application are exercised.


### audit.14 security-session containment

[audit.14 containment](audit/SECURITY-SESSION-CONTAINMENT.md) supersedes audit.12/13
next-request recovery for exact security markers. Local dispatch stops before
logging/callbacks, so already-queued dependent writes cannot proceed after an
unconfirmed outcome. No controller shutdown command is sent. Ordinary nonnull IO
replay remains open. Earlier isolated next-read success is historical evidence;
it is not the current containment behavior or whole-workflow qualification.

## Audit.15 no-replay refinement

[Ambiguous I/O containment](audit/AMBIGUOUS-IO-NO-REPLAY.md) intentionally removes
automatic resend for non-prefix I/O failures and stops the local session, including
failed reads. This supersedes audit.14 statements that ordinary nonnull I/O still
retries. Healthy replies and prefix -103 behavior remain original. Clean qualification passes on both pinned runtimes. See the linked evidence
for the 93-test suite, deterministic artifacts and narrowly stated limits. Prefix/generic failure sequencing,
synchronous cancellation/liveness, UI recovery and hardware acceptance remain open.

Audit.15 adds no third-party dependency; it changes a locked branch operand and
a compatibility-helper feature constant. The legacy dependency and plaintext-HTTP
limitations remain.

### Audit.16 worker-failure containment (clean fixtures)

The narrowly scoped audit.16 patch stops the local session before callbacks after
legacy prefix parse failures, typed malformed-input failures and generic worker
exceptions. It preserves their original result codes and exception objects;
healthy negative controller replies still permit the next request. This refines
the audit.15 statement that prefix behavior remains original: its error code is
preserved, but session continuation is deliberately removed for security.
Claude reviewed the design, implementation, follow-up and clean evidence; all six
qualification gates and 103 tests pass at clean source/fixture/package commit `727e5c4`. See [scope, evidence and remaining holes](audit/WORKER-FAILURE-STOP.md).
Interrupted synchronous waits, premature connection completion, queue exit races,
GUI recovery and hardware qualification remain unresolved. No controller command
or installed-app modification is part of this change.

### Audit.17 callback guard (clean fixtures)

A constructor-only defense removes enqueueing before the existing forbidden
synchronous-callback error. The memory differential shows the original queued
command later executing; the patch rejects before enqueueing while preserving
normal synchronous response identity and clone counts. This does not establish
original GUI reachability or fix interrupted waits and TYPE_CONNECT failure/later
transmission. Claude reviewed the design, implementation and clean evidence; seven gates and
108 tests pass at clean source/fixture/package commit `47166ed`. See [scoped evidence](audit/SYNC-CALLBACK-PREENQUEUE.md).

### Audit.18 initial connection failure stop (clean fixtures)

The worker now stops locally before publishing an initial connection failure,
preventing the held command from later executing after its caller receives an
error. The first silent dual-host fallback and retries with no published notice
remain; a stopped session requires a fresh Manager. Native GUI recovery is not
qualified. Nine gates, 112 Python tests and duplicate packages per architecture
pass at clean source/fixture/package commit `7aa02c5`; x64 runs under Rosetta.
See [scope and evidence](audit/CONNECT-FAILURE-STOP.md). No controller or installed
app was modified. Interrupted waits, synchronous enqueue/exit hangs, late async
posts, callback cleanup, lock ordering and hardware/release acceptance remain open.

### Audit.19 local stop lock ordering (clean fixtures)

Private stopped is volatile, and the worker's two queue-held reads avoid acquiring
the Manager monitor. Shutdown, callback timing and admission stay unchanged.
The isolated fixture proves completion and exact deadlock pairs when original
lock calls are restored. Ten gates, 118 tests and duplicate arm64/x64 packages pass
at clean source/fixture/package commit `6e2c210`. The first output-mismatch attempt
has an unresolved cause and is excluded; only the second plain set qualifies.
See [scope, limits and evidence](audit/STOP-LOCK-ORDER.md). Posting/exit stranding,
interrupted waits, callback failure cleanup, native GUI and hardware/release
acceptance remain open. No controller or installed-app modification occurred.

### Audit.20 stopped request admission (clean fixtures)

External posts to a locally stopped Manager are refused after the original clone,
under the queue lock. The lock is released before response delivery: SyncSender
is completed directly; other nonnull handlers are deferred to the EDT. The
worker retains its original enqueue/drain behavior. Deferred errors may update
the GUI/model where the old queue stayed silent, can precede older callbacks,
and can execute before a non-EDT poster returns; extension repost loops and
disposed AppContext delivery remain unqualified. Only Manager and two new
compatibility helper entries differ from audit.19; exact class reconstruction
checks unrelated logic. Eleven gates, 124 tests, 40 admission observations and
duplicate arm64/x64 packages pass at clean `b600ad3`; x64 is Rosetta.
See [scope, evidence and remaining gaps](audit/STOPPED-POST-ADMISSION.md).
Interrupted-wait ownership, abnormal worker exit, stop-versus-active-send,
native GUI, real hardware and signed release acceptance remain open. Original
JAR and installed application are preserved; legacy HTTP remains plaintext.

### Audit.21 ownership and terminal worker exit (local qualification)

Clean app source `ccf069f` and individually pinned clean fixtures `ccf069f`/`f0ca156`
pass twelve regression gates and 133 unit tests, including 120 worker, 46
connection-stop and 40 admission observations. Paired deterministic builds and
repeated ARM/x64 packages match; x64 execution is Rosetta. Claimed operations
wait for their actual outcome; terminal worker failure reports started work as
unconfirmed, drains unsent work without replay and contains callback failures
before arbitrary throwable logging. Exceptional cleanup callback thread/order
changes and best-effort limits are documented. See [scope and bound evidence](audit/WORKER-EXIT-QUALIFICATION.md).
Stop-versus-active-send, native GUI, physical Intel, real controller behavior and
signed release acceptance remain open. Original JAR and installed app are unchanged;
HTTP remains plaintext. Earlier milestones and failed/excluded attempts are historical.

[audit.21 candidate entry inventory](audit/worker-exit-sbom.json) records all 3,061 non-directory JAR entries and the candidate hash. It supplements the immutable original inventory and adds no third-party dependency. It uses the project inventory schema, not SPDX/CycloneDX.


### Audit.22 final stop admission (local qualification)

Clean application source `1e659d5` retains JAR
`202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd`.
Thirteen regression gates and 137 unit tests pass; 217 gate source hash entries
are verified. Twelve fixture records remain at `1e659d5`; clean QA `73ffa4e` makes
test JAR archives reproducible and reruns all 104 stop vectors. Only Manager
changes inside the application JAR from audit.21. A final volatile stop check
refuses unsent claimed work before exposure; admitted work retains its actual
reply or unconfirmed outcome. No command, polling interval or retry timing changes.
Paired builds and repeated ARM/x64 packages match bytes and modes; x64 is Rosetta.
Vendor runtimes are signature-verified; apps remain unsigned and unnotarized.
See [qualification, corrections and limits](audit/STOP-BEFORE-SEND.md) and the
[integrity ledger](audit/stop-admission-final-integrity.json).
Native GUI, physical Intel, controller behavior and release acceptance remain open.
No controller contact, production-volume test or installed-app change occurred.
HTTP remains plaintext. Earlier milestone records remain historical.

The [audit.22 entry inventory](audit/stop-admission-sbom.json) uses the project's
explicit inventory schema, not asserted SPDX/CycloneDX. No third-party dependency
is added. Transport prototypes under ignored build directories are excluded from
the qualified application and runtime packages.


### Audit23 initial socket setup (local qualification)

Application source `f9a5edb`, QA source `96861bf`, JAR
`2fccbee50eb868a04b415085511e0b52e6a13682543858d6f653b7f1f5fcadad`.
Thirteen candidate regression gates plus one historical audit17 characterization,
140 unit tests, paired clean builds and repeated packages per architecture pass. Only HttpConnection.createSocket and one
new helper differ from audit22; all other JAR entry bytes are preserved.
Twenty-nine memory cases per runtime/mode and twelve mutants per architecture
qualify refused publication after failed/mismatched initial read-timeout setup.
Original Socket(host,80), ignored connect argument, DNS/TCP timing, command bytes,
polling and retry policy are retained. Standard IO categories retain fixed safe
error detail. This deliberately changes legacy error prose. HTTP remains plaintext.
See [scope, exclusions and reproduction](audit/SOCKET-CONFIGURATION.md) and
[record hashes](audit/socket-configuration-final-integrity.json). One first lock
fixture mismatch is excluded; an unchanged reduced-concurrency rerun passes,
with the first cause unresolved. x64 runs under Rosetta; native GUI, physical
Intel, controller workflows and release acceptance remain open. Cached timeout
setter, whole-operation/write bounds, mutable outbound inputs, status/empty-ack
interpretation and firmware file binding remain separate gaps. No controller,
production/mounted volume or installed-app modification occurred.


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


## Audit26 dependency/SPDX qualification

No runtime class or dependency is added by the model diagnostic override. The
pinned compiler and both vendor runtimes are unchanged. Each architecture's
repeated SPDX 2.3 documents match, with 3,305 physical/virtual files and 17 packages;
all four pass pinned official schema/semantic validation and twelve negative
controls each. NOASSERTION software licensing and unresolved redistribution
rights remain. See [qualified scope](audit/MODEL-DIAGNOSTIC.md) and
[archived inventories](audit/model-archival-map.json). x64 execution is Rosetta.
