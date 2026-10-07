# Xserve RAID Admin

Compatibility and preservation work on Apple's RAID Admin 1.5.1 for modern macOS, retaining its existing Apple silicon and Intel runtime support. This audit candidate is not yet operationally qualified.

Current local baseline is audit.23: thirteen candidate regression gates, one
historical characterization, 140 unit tests
and repeated ARM/x64 packages verified locally. Initial socket read-timeout setup
now fails closed while original DNS/TCP connection timing is retained. See
[the qualified scope](audit/SOCKET-CONFIGURATION.md) and the
[integrity ledger](audit/socket-configuration-final-integrity.json). Native GUI,
physical Intel, controller compatibility and release acceptance remain open.

## About

The original RAID Admin was a Java application bundled with Mac OS X for managing Apple Xserve RAID hardware. It was compiled for Java 1.3 and relied on Apple-specific APIs that no longer exist in modern JVMs, making it unable to run on current macOS versions.

This project contains compatibility patches for the original application. Full functionality, UI behavior, protocol parity, and supported runtime/firmware combinations are not yet qualified. See [AUDIT-BASELINE.md](AUDIT-BASELINE.md) for measured results and limitations.

## Patches Applied

1. **`sun.io.MalformedInputException` shim** — The original `CommunicationsManager` catches this exception class which was removed from modern JDKs. A compatibility shim extending `java.nio.charset.CharacterCodingException` supplies the required catch type. Isolated dispatch fixtures pass; controller operation remains unqualified.

2. **`com.apple.mrj.MRJApplicationUtils` replacement** — Selects `com.apple.eawt` on Java 8 and `java.awt.Desktop` handlers on Java 9+; forwards original About, Preferences, Quit and file-open callbacks. Headless bridge tests pass; native menu/event qualification remains open.

3. **`com.apple.eio.FileManager` replacement** — Provides legacy folder mappings, but the runtime class shadows this replacement on tested Corretto 8/11. The verified MRJ caller bridge below handles Desktop lookup.

4. **`Launcher` wrapper** — Applies Swing UIManager fixes for the Aqua Look & Feel tab text rendering on modern macOS before delegating to the original entry point.

5. **`com.apple.mrj.MRJFileUtils` Desktop bridge** — Repairs the null folder lookup used by firmware selection and event-log export. Other stubs remain unchanged. Offline regression and method-preservation checks pass; dialog workflows remain to be qualified.

6. **Plist entity resolver and request diagnostics** — Three hash-locked method substitutions preserve the original embedded DTD, reject external entities, and redact both credential-bearing request diagnostic methods.

7. **Bounded logging adapter** — Emits only fixed ERROR/FATAL signals, at most once per level per process. No message, exception or context is rendered. This is terminal diagnostic support; GUI error handling remains unqualified.

8. **Secure plist parser boundary** — Uses the pinned bootstrap JDK provider with
   explicit verified resource quotas and external-access denial, retaining the
   original plist Handler, DTD and serializer. Custom entity expansion is bounded
   to 1 MiB. These are deliberate security restrictions; real-response compatibility
   remains open. See [audit.6 evidence](audit/XML-PARSER-COMPATIBILITY.md).

9. **Response allocation ceiling** — An operand-only change selects a bounded
   ByteArrayOutputStream subclass. Advertised response bodies above 16 MiB fail
   before allocation through the existing terminal malformed-input path.
   Security rejection recovery is refined in audit.9; framing remains open. See
   [audit.7 evidence](audit/HTTP-ALLOCATION-GUARD.md).

10. **Bounded response headers** — A per-response stream wrapper caps line,
    field-count and aggregate header input while preserving the original parser.
    Unsafe input fails once without resend; audit.9 retires the rejected connection.
    See [audit.8 evidence](audit/HTTP-HEADER-GUARD.md).

11. **Security rejection recovery** — Exact-marker handling closes the rejected
    connection, preserves one failure callback and lets the next distinct command
    use the original reconnect path. Cleanup failures cannot trigger a resend.
    Invalid numeric/negative lengths are refined in audit.10. See
    [audit.9 evidence](audit/REJECTION-RECOVERY.md).

12. **Invalid length rejection** — Malformed, overflowing and negative response
    lengths use the same safe retirement path, with a fixed message and no raw
    header value/cause. Valid runtime numeric parsing remains unchanged. See
    [audit.10 evidence](audit/INVALID-LENGTH-GUARD.md).

13. **Explicit response framing** — Accepts one Content-Length regardless of
    ASCII letter case. Missing/duplicate lengths and unsupported Transfer-Encoding
    fail through the same safe retirement path. This is an intentional security
    restriction with controller compatibility still unqualified. See
    [audit.11 evidence](audit/RESPONSE-FRAMING-POLICY.md).
14. **Malformed-header rejection** — Fixed terminal errors for colonless and
    leading-colon headers prevent peer-text exceptions and command replay on
    that response path. See [audit.12 evidence](audit/MALFORMED-HEADER-GUARD.md).
15. **Null-message IO recovery** — Replaces dispatch worker death with one fixed
    terminal failure and connection retirement, preserving nonnull IO retry behavior.
    See [audit.13 evidence](audit/NULL-IO-RECOVERY.md).

## Requirements

Pinned runtime candidates include Corretto 8 for the selected architecture and
need no system Java. Their vendor binaries require macOS 11.0 or later; native UI
and hardware qualification across OS versions remains open. Development builds
require the exact compiler and Python versions recorded in the audit locks.

## Building

Use the exact compiler recorded in `audit/jdk-lock.json` and Python version in
`audit/python-lock.json`. Choose a new output directory for each build:

```bash
./build.sh --jdk /path/to/locked-jdk/Contents/Home --output build/audit-local
```

This produces `build/audit-local/RAID Admin.app` and `provenance.json`.
The unsigned audit bundle retains a historical launcher for comparison. For a
self-contained candidate, use the pinned runtime packaging described below.
No build command installs, signs, launches, or deletes an existing output.
Installation and hardware qualification remain separate acceptance work.

## Usage

The original application offers a **+** workflow for discovery or manual IP entry.
That GUI/network workflow has not been qualified in this audit. Hardware testing
of these candidates requires an approved test context.

The original application can replay a mutation after a dropped response. The
current compatibility guards stop the affected worker session on the verified
ambiguous-failure paths and preserve honest uncertain outcomes. Full GUI/CLI
retry and firmware workflows remain unqualified; launch is not feature proof.
See [G10](GAPS.md#g10--ambiguous-writes-and-queue-retry-semantics).

## Hardware Compatibility

- Apple Xserve RAID (firmware compatibility remains to be qualified)
- Communicates via the ACPX protocol over HTTP to the Xserve RAID coprocessor
- Contains Bonjour/mDNS discovery implementation (`_xserveraid._tcp`); operation unqualified

## Original Software

The `original/` directory contains the unmodified JAR and icon assets from Apple's RAID Admin 1.5.1. The `patches/` directory contains compatibility Java source. `tools/class_patch.py` performs three hash-locked, method-only substitutions documented in `audit/security-patches.json`.

## Audit tooling

`build.sh` delegates to the [hash-locked audit builder](AUDIT-BASELINE.md#build-reproducibility).
Consult [architecture](ARCHITECTURE.md), [protocol inventory](PROTOCOL-INVENTORY.md),
and [dependencies](DEPENDENCIES.md). No audit artifact is a qualified release.

## Pinned runtime packaging

`tools/runtime.py` fetches only the versioned archives in `audit/runtime-lock.json`,
verifies vendor SHA-256, exact file bytes/modes and Developer ID signatures, and
keeps them in a local cache. `tools/bundle.py` adds one pinned runtime to a verified
clean audit build; it never signs, installs or launches the app. Produce separate
`aarch64` and `x64` artifacts to preserve both architectures. The bundled launcher
uses only that runtime and a committed icon, with no temporary icon or PATH fallback.

The pinned vendor Java binaries require macOS 11.0 or later; this binary floor is
not a claim that every OS version is qualified. These remain unsigned local
candidates, not release artifacts.


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
