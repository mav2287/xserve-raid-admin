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
