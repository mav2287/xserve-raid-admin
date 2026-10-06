# Open audit issues

Local issue IDs are stable evidence references; no remote issues were filed.

## G01 — Original provenance and installed/source divergence

The repository original now matches the JAR served in Apple’s 1.5.1 download byte-for-byte; see `audit/apple-distribution-acquisition.json`. This is current HTTPS acquisition evidence, not an independently verified historical signature. Installed patches differ from source, including extra MRJ helpers and a different FileManager replacement. The starting EVIDENCE.md JAR digest is only 62 hex characters and cannot authenticate a historical artifact; the launcher hash does match. A transcription error is inferred, not proven. The user has accepted the GitHub JAR as the project baseline: historical digest investigation is closed for this work. Installed/source behavioral divergence remains relevant. See AUDIT-BASELINE.md and entry-diff JSON.

## G02 — Runtime and classloading

Upstream had no bundled JRE and selected arbitrary external Java with a predictable icon path. The pinned packaging path now includes an architecture-specific, vendor-verified Corretto 8 runtime and fixed icon. Runtime FileManager shadows the packaged replacement on tested Corretto 8/11, but the guarded probe confirms its preferences-folder result works. This is a loading fact, not itself a functional defect. Supported OS/CPU/JRE combinations are unqualified. The audit launcher remains historical; the bundled launcher selects only its pinned runtime.

## G03 — OS lifecycle and menus

audit.3 repairs Java 8 EAWT vs Java 9+ Desktop selection and binds About, Preferences, Quit and OpenFiles to original callbacks. Headless adapter tests pass on five runtime/architecture configurations. Object methods no longer invoke callbacks; failures use bounded fixed codes. Print/open-application registration remains an unused original stub. Real native registration, menu delivery, preference persistence and Finder events remain unqualified. A failing original quit/save callback cancels quit; fixed stderr/status codes exist, but a visible in-app failure dialog remains open.

## G04 — Credential-bearing logging

Original AbstractRequestMessage.toString includes password, and AcpxRequestTemplate.toString appends the entire payload. audit.4 replaces exactly these two diagnostic methods with a fixed redacted string, including password-change fixtures. audit.5 replaces root OFF with ERROR and a dedicated appender that emits only fixed ERROR/FATAL codes, at most one of each per process. Actual-JAR configuration tests cover hostile messages/throwables, NDC/MDC/thread/logger names, DEBUG child categories, reconfiguration, closed appenders and write exceptions. No Console/FileAppender is attached and the guard observes no writes. The full original JAR has only INFO/DEBUG level guards outside log4j; both remain disabled.

The two bounded stderr writes are synchronous and could block error-logging threads on a blocked pipe. RuntimeExceptions are contained; VM Errors are not swallowed. Finder launches may not display stderr; visible in-app failures remain open. No application-wide confidentiality claim is made for other output paths, reflection or externally reconfigured logging. ACP headers still carry plaintext credentials. No real credentials were read or emitted.

## G05 — XML external resolution

Original, installed and earlier audit JARs resolve the known Apple DTD locally but permit external file entities and unknown-DTD network attempts. audit.4 substitutes only the resolver method: the exact original embedded DTD is retained and other external identifiers are rejected. Reader/InputStream fixtures, malformed/truncated inputs and external general/parameter entities pass without file or network access attempts. audit.6 replaces the parser construction boundary with verified bootstrap-provider quotas and external-access denial. Offline resource-limit enforcement is covered; real controller response sizes and complete provider compatibility remain open. See [audit.6 scope](audit/XML-PARSER-COMPATIBILITY.md). The actual bundled Xerces provider does not recognize the tested JDK controls; lowered-property positive controls affect the JDK parser but not the application parser. See [XML findings](audit/XML-RESOURCE-FINDINGS.md). Legacy external DTD variants outside the original Apple prefix are intentionally blocked and need real-data compatibility assessment.

## G06 — Controller and UI qualification

Discovery, roles/authentication, polling, timing, persistence, reconnect, sleep/wake, dual-controller behavior and terminal UI states are untested. Static catalogs do not prove feature operation. Real sanitized read-only fixtures and controlled hardware environment are absent.

## G07 — Firmware and mutation safety

The Apple-served 1.5.1 package is now acquired and pinned for offline inspection. No hardware maintenance context is available. Guarded wrapper tests read its metadata and both image hashes identically on both pinned runtimes. Preflight UI, visible errors, confirmation, transfer, acknowledgement, restart and final-version validation remain unqualified. Original updater bytecode also disables/restores disk and controller caches; firmware approval must explicitly cover these ancillary restricted actions. Inference/open risk: an interruption or failed restoration could leave caches disabled; the cache state after failure has not been qualified. Array/cache/network/power/diagnostic mutations are not authorized for execution without immediate confirmation.

## G08 — Release engineering

Upstream ZIP timestamps prevented exact rebuilds and signing failures were swallowed. The single build entry point is now deterministic and never signs or installs. Separate pinned runtime bundles reproduce on this host; they remain unsigned and lack independent-host reproduction, signed distribution, notarization/Gatekeeper qualification and resolved dependency licenses.

## G09 — Native credentials and integration fidelity

No bundled JNI PasswordManager library, no modern Keychain helper. Menus, chooser, Finder document opening, Retina/accessibility/help, metadata behavior, notification and event export/printing are unqualified.

## G10 — Ambiguous writes and queue retry semantics

Source requeues the same transaction on non-parse IO failure, without a bounded
attempt count. The callback is retained in the transaction; the failed iteration
suppresses an immediate result and later attempts can notify it. A command may
have reached the controller before a connection failure, making a repeat unsafe.
Firmware uses a single-use stream; a retry may fail before sending anything.
The memory-only fixture now observes two identical sends after one dropped response,
five after four drops, and one eventual callback with retained context. Parse errors
produce -103 without requeue. Synthetic single-use firmware streams either throw
before a second send or produce a zero-length second body, depending on stream
behavior. See `audit/transport-observation.json`. The synthetic archive fixture now observes stored-entry streams returning EOF after close, while deflated-entry streams throw I/O errors. Real reconnect/backoff and queue
concurrency remain unqualified. A two-read-request fixture now observes first–first–second sends on connections 1–2–2 after one dropped response, with callbacks in order and context retained; see [HTTP findings](audit/HTTP-RESPONSE-FINDINGS.md). Transmission of real firmware packages is untested. No retry behavior
has been changed.

## G11 — MRJ folder lookup

Confirmed offline: the unpatched MRJFileUtils returns null for Desktop. Firmware
and event-log Save call getPath() on that result. Fixed in audit.2: the used
single-argument overload returns the user Desktop for its singleton constant.
`tools/check_folders.py` verifies unchanged ABI and instructions for every other
method, plus null/custom-type/unused-overload behavior. No directories are created.
The two dialog callers are statically verified; GUI workflows remain unqualified.
See `audit/folder-fix-results.json`.

## G12 — HTTP response framing and error interpretation

Guarded original/candidate fixtures confirm that HTTP status is ignored, header
lookup is case-sensitive, duplicate exact length fields use the last value and
missing/lowercase length or chunked-only replies parse as empty. A queued
lowercase-length response reports zero success; HTTP 401/403/500 with a success
plist also report zero. ACP plist authentication error codes are preserved.
Truncated bodies enter the generic I/O retry path; malformed numeric lengths
produce -102 in the queue. See [HTTP findings](audit/HTTP-RESPONSE-FINDINGS.md).
Actual authentication UI and controller framing remain unqualified; these
observations do not establish authentication bypass. Explicit XML quotas and declared-body/header bounds now apply in audit.6–8;
persistent-stream desynchronization, status/framing interpretation and visible
errors remain open. Ordinary response interpretation and original retry timing
remain unchanged; deliberate new security rejections are documented below.

## G13 — Legacy XML validation stack growth

Original and audit.5 reject small valid arrays at nesting 31 and above because
XMLDTDValidator's offset-stack resize comparison skips equality, then indexes
outside the array. Runtime SAX unwrapping and independent bytecode identify the
defect. Depth 30 passes; the 31/32/128 cases fail identically through both input
paths on both pinned runtimes. This must not be credited as a security quota.
No bundled library was rewritten or replaced. A narrow parser-construction
compatibility boundary is under review; [XML findings](audit/XML-RESOURCE-FINDINGS.md).


G13 refinement: audit.6 explicitly enforces depth 32 and preserves measured accepted/rejected container boundaries while converting the original array-bounds failure to a depth-limit rejection. Validation remains enabled with a replaced provider; original Handler and DTD remain.


audit.7 refinement: declared HTTP response body allocation is capped at 16 MiB before allocation using an operand-only buffer substitution and the existing terminal -102 path. Header/status/framing, persistent-stream recovery and real response size compatibility remain open. See [allocation guard](audit/HTTP-ALLOCATION-GUARD.md).


## G14 — Terminal response rejection and persistent connection recovery

A guarded two-command fixture confirms that original invalid numeric lengths leave
requestOutstanding true. The next queued read fails -102 before transmission;
only one request was sent, with zero reconnects. audit.7 oversized rejection takes
this same terminal path. This protects against a resend loop but does not recover
the connection. Header/frame rejection cleanup must be designed explicitly without
silently replaying potentially mutating requests. See [allocation evidence](audit/HTTP-ALLOCATION-GUARD.md).


## audit.8 response header refinement

Line, count and aggregate header input are explicitly bounded through a three-byte
constructor insertion and per-response wrapper; original readLine/parseHeaders
remain unchanged. Exact limits and 174762 short-input/EOF cases pass on both pinned
runtimes. Queue rejection is terminal -102 with no replay, but the next command
still fails before sending: G14 recovery remains open. HTTP framing and actual
controller response compatibility are unqualified. See [scope and clean evidence](audit/HTTP-HEADER-GUARD.md).


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


## Shared-stream G12 characterization

Clean committed offline fixtures now demonstrate prior-body response association
for missing/lowercase/duplicate-last-zero/declared-zero framing, and a stuck
follow-on after chunked parsing failure. Original and audit.10 outcomes match on
both pinned runtimes (x64 via Rosetta); no TCP or hardware qualification is claimed.
The characterization changes no application bytes. Narrow framing policy is the
next reviewed security milestone. See [evidence](audit/SHARED-RESPONSE-FRAMING.md)
and [clean observations](audit/shared-stream-clean-results.json).


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
