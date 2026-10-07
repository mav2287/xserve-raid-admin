# Detailed implementation and audit plan

> Current audit28 status and credential-path corrections: [SECURE-PREFERENCES.md](audit/SECURE-PREFERENCES.md#credential-path-evidence-correction). This historical document is retained; its earlier inference that the unavailable JNI disables Save/Forget Password is superseded. Those original controls remain in code; persistence and behavior through the new writer remain unverified.


## 1. Mission and non-negotiable principles

Make Apple RAID Admin 1.5.1 fully usable on supported modern macOS systems while
remaining as faithful as practical to the original application.

Non-negotiable principles:

1. Preserve the original user-visible workflow and controller protocol by
   default.
2. Modernize operating-system boundaries, not unrelated application behavior.
3. Never hide failure. Every requested operation must reach a visible terminal
   state: completed, rejected, failed, timed out, or unconfirmed.
4. Treat the original JAR as an immutable reference artifact.
5. Separate compatibility patches from original Apple code whenever practical.
6. Prove parity with tests and packet captures rather than relying on the fact
   that the interface opens.
7. Perform destructive, power, RAID-layout, and firmware tests only in a defined
   maintenance environment.

## 2. Repository intake and provenance

The first assigned agent must perform this phase before implementing fixes.

### 2.1 Acquire and inventory the source

1. Clone or update `https://github.com/mav2287/xserve-raid-admin` in this project
   folder.
2. Record the branch, commit, remotes, submodules, tags, and dirty status.
3. Read all build, packaging, and release scripts before running them.
4. Locate any original Apple binaries and compare their hashes with
   `EVIDENCE.md`.
5. Identify which files were authored for modernization and which are unmodified
   original artifacts.
6. Produce a file-level architecture map covering launcher, packaging, Java
   patches, native helpers, entitlements, signing, and release automation.

### 2.2 Establish artifact provenance

Create a machine-readable manifest containing:

- Source commit
- Build timestamp and builder version
- Original JAR SHA-256
- Launcher and helper hashes
- Bundled JRE vendor/version/architecture/hash
- Dependency names, versions, licenses, and hashes
- Signing identity and notarization status
- Final application hash

Do not overwrite Apple's version identity. Use a compatibility version such as
`1.5.1-modern.N` and show both the Apple baseline and compatibility build in the
About dialog or diagnostic report.

### 2.3 Reproducible baseline

Build the repository without source changes. Compare the resulting bundle with
the installed application. Document every difference. Launch it only after the
build scripts and artifacts have been inspected for unsafe or unexpected
behavior.

Deliverable: `AUDIT-BASELINE.md` with source provenance, architecture, build
instructions, hashes, and known gaps.

## 3. Architecture strategy

Offline refinement: HTTP status/framing and ACP result interpretation are now
characterized across both pinned runtimes, including two-request retry order.
The original can report empty success for missing/lowercase length and ignores
HTTP error status; [G12](GAPS.md#g12--http-response-framing-and-error-interpretation)
tracks this. Do not silently normalize framing, remap results or change retries.
Persistent-stream/concurrent-queue and real authentication qualification remain
open; see [findings](audit/HTTP-RESPONSE-FINDINGS.md).

Prefer a thin compatibility layer around the original JAR.

### 3.1 Immutable upstream artifact

Store the verified original JAR as a versioned input or obtain it during a
documented build step. Do not silently modify it in place. Licensing and
redistribution questions must be documented before public distribution.

### 3.2 Patch overlay

Investigate launching with a classpath shaped like:

```text
compatibility-patches.jar:RAID_Admin.jar
```

and invoking the original `Launcher` main class. The patch JAR should contain
only classes that must differ on modern systems. Verify classloading behavior
with an automated test; do not assume the manifest's `-jar` behavior supports
the desired precedence.

If an overlay is impractical, use a reproducible JAR transformation that:

- starts from a verified input hash,
- replaces an explicit allowlist of classes,
- produces a deterministic output,
- records before/after hashes, and
- fails if the input differs from the expected original.

### 3.3 Native compatibility helper

Use a small native macOS helper only for capabilities that Java cannot reliably
provide with the desired fidelity:

- application lifecycle integration,
- Keychain access,
- modern DNS-SD/Bonjour browsing,
- native firmware file selection,
- secure temporary-file creation,
- opening diagnostic/log locations.

Keep controller protocol implementation in one place. The native helper must not
invent a second independent RAID protocol stack unless there is a compelling,
reviewed reason.

### 3.4 Runtime policy

Bundle one supported, tested JRE rather than choosing arbitrary installed Java.
Start by evaluating a maintained Java 8 runtime for behavioral fidelity, then
test Java 11 as a separate supported configuration. Choose based on the full
acceptance matrix, not launch success alone.

Preserve the repository's existing Intel and Apple silicon support. The shell
launcher and Java bytecode do not require a new architecture port. A bundled
runtime strategy must retain both architectures; qualify each independently.

## 4. Work phases

### Phase 0: Preserve the reference and build an observation harness

1. Copy and hash the installed reference bundle.
2. Add a redacted diagnostic command that reports app version, source commit,
   JRE, architecture, interfaces, discovered controllers, and bundle hashes.
3. Create a packet-capture procedure limited to controller IPs and ports.
4. Add log redaction tests that ensure passwords and authentication headers
   never appear in logs.
5. Capture representative read-only sessions from the existing application.

Exit criterion: repeatable baseline build and enough evidence to compare old and
new behavior.

### Phase 1: Fix immediate operational gaps

#### Runtime

- Bundle and explicitly invoke the selected JRE.
- Remove fallback to arbitrary `PATH` Java in release builds.
- Report a clear startup error if the bundled runtime is missing or damaged.

#### Discovery

- Replace or wrap JmDNS 0.2 with macOS DNS-SD behavior that correctly handles
  Ethernet, Wi-Fi, VPNs, interface changes, and sleep/wake.
- Preserve expected RAID service types.
- Keep manual direct-IP connection available at all times.
- Show which interface and address produced each discovered controller.
- Deduplicate dual announcements without merging two physical controllers.

#### Connection lifecycle

- Make connection states explicit: disconnected, discovering, connecting,
  authenticating, connected, degraded, reconnecting, and failed.
- Stop timers and polling before disconnecting.
- Drain or cancel queued read operations safely.
- Close the HTTP connection on disconnect and quit.
- Reset excessive reconnect backoff after a user-requested reconnect.
- Ensure reopening the application does not leave an invisible stale session.

#### Errors and logging

- Turn swallowed exceptions into concise user-facing errors with a diagnostic
  reference ID.
- Use rotating logs with credentials, authentication headers, and sensitive
  payloads redacted.
- Keep ordinary users out of debug noise; provide an opt-in diagnostic mode.

Exit criterion: reliable discovery/direct-IP connection, disconnect, reconnect,
app restart, sleep/wake, and controller restart behavior.

### Phase 2: Repair macOS integration

#### Firmware chooser

- Use a native open panel restricted to `.xfb` files.
- Reject other file types even if the chooser allows manual override.
- Never use predictable shared paths in `/tmp`; use per-process secure temporary
  storage where necessary.

#### Keychain

- Replace the unavailable JNI password manager with Keychain Services.
- Store secrets under a new compatibility-app service identifier.
- Migrate nothing silently from unrelated entries.
- Provide explicit remember, update, and forget controls.

#### Application behavior

- Verify menus, window activation, close/quit behavior, Retina rendering,
  keyboard shortcuts, accessibility labels, and dark-mode legibility.
- Preserve the original visual appearance unless a modern OS issue makes an
  element unusable.

Exit criterion: all operating-system integrations behave normally on supported
macOS releases without altering controller semantics.

### Phase 3: Safety hardening with compatibility tests

#### XML

- Block external entity expansion and network/file resolution.
- Prefer a controlled local resolver for any known required plist/DTD content.
- Add fixtures from real controller responses.
- Test malformed, oversized, truncated, and unexpected XML.

#### Firmware preflight

A strict known-package offline foundation now exists. Unknown packages reject
before any ZIP/manifest interpretation; structural properties are inherited only
from exact identity with the checked Apple reference. This is not general ZIP
validation or completed application preflight. Java snapshot binding and the
summary/confirmation UI remain required. See
[foundation scope](audit/FIRMWARE-PREFLIGHT-FOUNDATION.md).

Before the client sends firmware data, validate:

1. Readability and maximum size.
2. ZIP/JAR integrity and absence of unsafe paths.
3. Required manifest keys and allowed image paths.
4. Referenced images exist and have plausible nonzero sizes.
5. Version and hardware compatibility rules that can be established from Apple
   documentation or known-good packages.
6. SHA-256 against a maintained allowlist when an authoritative official image
   is available.

Display a preflight summary and require explicit confirmation. Report transfer
progress, controller acknowledgement, expected restart, reconnection, and the
post-update version. If any step cannot be verified, label the result
“unconfirmed,” not successful.

Do not add a client-side signature claim unless an authoritative verification
scheme exists. Do not assume whether controller-side verification occurs;
determine that separately in a safe environment.

#### Network exposure

- Document that the legacy protocol is plaintext.
- Warn when managing the RAID over an interface classified as untrusted.
- Recommend a dedicated management VLAN or physical network.
- Do not attempt a transparent TLS conversion that the controller cannot speak.

Exit criterion: hardening passes all recorded legitimate sessions and negative
tests without changing valid controller requests.

### Phase 4: Behavior-conformance system

Build two complementary tools.

#### Record/replay test server

Create a local emulator from sanitized controller exchanges. It should reproduce
normal responses, delays, connection drops, malformed replies, authentication
failure, one-controller failure, restart, and firmware-progress states.

Do not treat the emulator as proof that hardware operations work. Its purpose is
repeatable UI, parsing, state-machine, and error-handling testing.

#### Wire parity comparator

For the same user action, compare the original and compatibility builds:

- HTTP method and path
- Header names and values, excluding expected build/user differences
- Ordering where semantically important
- Request body structure and bytes
- Retry timing
- Connection reuse
- Resulting UI state

Every difference must be categorized as expected modernization, bug fix,
unavoidable runtime difference, or regression.

Exit criterion: automated read-only parity suite and controlled mutation tests
cover the complete feature inventory.

### Phase 5: Hardware qualification

Use a written maintenance procedure. Before any destructive test:

- Verify backups.
- Unmount all volumes as required.
- Confirm both controller addresses and identities.
- Confirm the exact target array and controller.
- Disable unrelated subnet scanners and high-rate discovery tools.
- Capture management traffic only from the test host/controller pair.
- Define recovery and power-cycle procedures.

Run tests in escalating order:

1. Read-only status and inventory.
2. Authentication and permissions.
3. Long-duration monitoring and reconnect behavior.
4. Non-destructive setting reads and reversible settings.
5. Drive replacement/rebuild monitoring with designated test media.
6. RAID configuration mutation on disposable data.
7. Controller restart/shutdown.
8. Firmware update using an authoritative known-good package.

Record application logs, packet captures, controller event logs, expected
result, actual result, and recovery steps for every test.

Exit criterion: every applicable item in `ACCEPTANCE-MATRIX.md` passes on real
hardware or is explicitly documented as unsupported with evidence.

### Phase 6: Release engineering

- Produce deterministic release artifacts.
- Generate an SBOM and provenance manifest.
- Use a project-specific bundle identifier rather than presenting the release as
  current Apple software.
- Sign with Developer ID and notarize.
- Harden the runtime and entitlements to the minimum required set.
- Verify Gatekeeper behavior on a clean modern macOS installation.
- Publish supported macOS, CPU, RAID firmware, and JRE combinations.
- Include rollback instructions and hashes.

## 5. Recommended first implementation sequence

After the source audit, implement in this order:

1. Reproducible baseline build and immutable original-JAR check.
2. Compatibility build identity and diagnostic report.
3. Bundled pinned JRE.
4. Redacted logging and visible error reporting.
5. Firmware chooser and non-destructive preflight inspection only.
6. Discovery with direct-IP fallback.
7. Graceful connection lifecycle and bounded reconnect behavior.
8. XML external-resource hardening with response fixtures.
9. Keychain integration.
10. Record/replay emulator and wire-parity suite.
11. Controlled hardware qualification.
12. Signing, notarization, and release documentation.

Do not make firmware transmission the first firmware-related change. First make
inspection, validation, logging, and confirmation trustworthy.

## 6. Coding and review requirements

- Keep each behavioral patch narrow and independently reviewable.
- Add a regression test before or with each fix.
- Never log passwords or `ACP-Password` values.
- Do not add telemetry.
- Do not change polling frequency, retry policy, or controller commands without
  a benchmark and captured comparison.
- Require two-person review for firmware, RAID-layout, cache-policy, power, and
  destructive-drive commands.
- Ensure UI buttons cannot submit the same destructive operation twice.
- Add timeouts and cancellation without pretending cancellation succeeded on the
  controller when it cannot be confirmed.
- Keep test fixtures sanitized of passwords, serial-sensitive information, and
  private network details when they leave the private repository.

## 7. Required agent outputs

The agent performing this plan should leave behind:

1. `AUDIT-BASELINE.md`
2. `ARCHITECTURE.md`
3. `PROTOCOL-INVENTORY.md`
4. `DEPENDENCIES.md` or an SBOM
5. A reproducible build command
6. Automated unit, fixture, record/replay, and wire-parity tests
7. A completed copy of `ACCEPTANCE-MATRIX.md`
8. `HARDWARE-TEST-REPORT.md`
9. `RELEASE-CHECKLIST.md`
10. A list of remaining limitations stated without euphemism

## 8. Stop conditions

Stop and request operator review before:

- writing RAID configuration,
- changing controller network settings,
- changing cache or battery policy,
- restarting or shutting down a controller,
- starting a rebuild with non-disposable data,
- erasing or initializing a disk,
- transmitting firmware,
- modifying the installed reference application, or
- testing against mounted production volumes.

Read-only inspection, source analysis, local builds, emulation, and offline
fixture tests do not require those hardware-operation approvals.


## 9. Intake refinement — 2026-10-05

See [baseline](AUDIT-BASELINE.md),
[architecture](ARCHITECTURE.md),
[protocol](PROTOCOL-INVENTORY.md), and
[dependency inventory](DEPENDENCIES.md).

Repository intake and offline observation tooling are complete. **Phase 0 exit
is still open** pending representative hardware sessions and sanitized wire
comparison. Existing upstream build is nondeterministic; the new unsigned audit
builder is content-reproducible on the exact locked local toolchain. Independent
host reproduction and a distributable pinned runtime remain open.

Refinements supported by source/runtime evidence:

1. Keep three distinct artifacts: the user-accepted, hash-locked repository JAR,
   installed patched reference, and rebuilt compatibility output. Use the GitHub
   repository artifact as the authoritative project baseline. The historical
   digest discrepancy is an audit note, not a blocker.
2. A simple overlay cannot override bootstrap FileManager on observed Corretto
   8/11. Test class origin before choosing a thin caller bridge or another narrow
   strategy. The audit uses the permitted deterministic transformation instead.
3. Preserve the existing local Apple DTD resolver when hardening XML. The problem
   is fallback external resolution, not a wholly absent resolver.
4. Secure request/object formatting before enabling any application logs. The
   offline harness's metadata allowlist is not a general HTTP redactor.
5. Add explicit coverage for advanced arrays, slicing/expansion, LUN and fibre
   settings, notification/time/password changes, log clearing, NVRAM and diagnostic
   mutations; some diagnostic operations may write data.
6. Preserve the existing ACP user-agent 1.6.0 override unless reviewed parity
   evidence supports a change. Do not infer supported firmware from UI presence.
7. The next narrow compatibility milestone should test and repair OS integration
   classloading/menu/lifecycle boundaries. Continue runtime and credential-safe
   error handling qualification before full operational claims.

No restricted operations are preauthorized by these refinements. No packet capture,
firmware, controller mutation, production-volume test or installed-app change was
performed. The user must confirm restricted operations immediately before each one.

## Current execution constraints and reviewed order

Both Apple silicon and Intel are required. The available RAID has production or
mounted volumes: hardware testing remains deferred. Offline builds and fixtures
continue autonomously. The GitHub JAR remains the accepted immutable baseline.

User clarification: both architectures are existing support to preserve, not new
features to add. The same original and audit-built JARs pass the limited offline
serializer/HTTP-parser fixture on arm64 Java 8, arm64 Java 11, and x86_64 Java 11
under Rosetta. See `audit/architecture-fixtures.json`. Native Intel GUI and hardware
qualification remain unperformed.

First correct extraction/class-origin evidence and strengthen input/output gates;
then exercise the ACP/logging/retry paths in isolation. Pin the evaluated runtime
before menu/lifecycle fixes. Test the confirmed MRJ folder-null issue separately.
The ordinary overlay remains a viable candidate: runtime shadowing also affects
the existing transformation and does not by itself favor either strategy.

## audit.4 implementation refinement

Completed offline milestones: MRJ Desktop lookup, Java 8/11 menu adapter, pinned
Corretto 8 packaging for both existing architectures, and narrow XML/request
diagnostic hardening. The build entry point now uses the deterministic builder.
The security patch preserves the original embedded DTD and all non-target methods;
external entity resolution is intentionally rejected. Controller command creation,
serialization, polling and retry semantics have not changed.

Next: credential-safe application error reporting, firmware archive preflight
fixtures, broader malformed-response and queue-order characterization, and
controlled native UI qualification. App-wide logging, parser resource limits,
physical Intel qualification, signing/notarization and real controller behavior
remain open. Production hardware approval has not been given.

## audit.5 offline continuation

Added bounded credential-safe logging signals after full-JAR level-guard inspection
and Claude design review. This does not close GUI-visible failure handling. Added
synthetic firmware archive characterization without constructing the updater or
contacting controllers; stored/deflated closed streams explain the two observed
retry outcomes. Next safe scope remains firmware preflight validation and broader
response/queue fixtures, followed by isolated native UI qualification. Full hardware
and release acceptance remains outstanding.

## Official-source refinement

Apple’s still-served 1.5.1 archive contains a JAR identical to the immutable
GitHub reference. Keep the existing reference; no replacement is necessary.
The accompanying firmware archive is pinned and inspected offline. Its optional
full-image key is absent. Release notes state that LUN Masking was removed from
the Advanced panel, despite remaining bytecode. Preserve intended visible 1.5.1
behavior rather than exposing every catalogued legacy class.


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


## audit.7 response allocation

Close the demonstrated Content-Length preallocation path with a narrowly bounded buffer subclass and two operand changes. Keep all existing valid-response and retry code. Oversized input is a deliberate terminal security rejection, with real response compatibility and framing/recovery unresolved. Follow with bounded header/framing investigation, isolated UI and firmware preflight work.


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


### Request-factory characterization refinement

[Request-factory characterization](audit/REQUEST-FACTORY-CHARACTERIZATION.md)
records 59 exact instance overloads: 58 synthetic invocations at timeout 0/123,
with the filename-based firmware overload explicitly excluded. The reviewed table
contains 116 body digests and six enqueue-sharing cases. No controller function
is qualified by this evidence. RPC getCommand equals its body method, refining the
previous hidden-method inference. RPC bodies and headers remain shared through
cloning; command/property bodies are copied, including supported Date/byte[] leaves.
Command alone cannot classify property/no-op requests. Broader ambiguous-IO retry
classification still requires caller/control-flow and multi-step operation evidence.
Clean qualification is linked from the characterization record when complete.


### Security qualification limitation: queued follow-up operations

[Operation-sequence source audit](audit/REQUEST-OPERATION-SEQUENCES.md) and
[actual Claude review](audit/claude-review/AMBIGUOUS-IO-CALLER-SEQUENCES.txt)
confirm that several UI workflows enqueue writes with null handlers and do not
wait for prerequisite results. Audit.13's successful next-read recovery does not
qualify safe next-write behavior. Terminal rejection of one uncertain command
must also contain queued/delayed dependent writes. Production/controller and
release acceptance remain open; no hardware action was performed. Prior fixture
results remain valid within their stated isolated scope, not whole-workflow proof.


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

### Next security milestone: ownership plus terminal worker exit

The user authorizes closing the security hole conservatively. Implement and
qualify interrupted-request ownership together with worker-exit completion before
promoting the next baseline. A claimed operation must remain unconfirmed when
its worker dies; it must never be replayed or reported as safely cancelled.
Unclaimed queued operations are unsent shutdowns. Stop admission before callbacks,
avoid double callback attempts including doConnect failure publication, and keep
new boundary signals free of arbitrary throwable data. Exceptional callback
thread/order changes must be documented and tested. The current
[audit.20 baseline](AUDIT-BASELINE.md) remains qualified; the
[ownership experiment](audit/SYNC-OWNERSHIP-EXPERIMENT.md) is not acceptance.


2026-10-06 security continuation: combined audit.21 ownership and worker-exit guards
are integrated locally and under verification. Exact predecessor reconstruction,
independent bytecode checks, paired deterministic builds and 133 unit tests pass.
Do not promote as release-qualified until the current runtime fixtures and clean
source evidence are complete. audit.20 qualification records remain immutable.
Startup prepare propagation and the AddSystemAction counter effect are documented
in audit/WORKER-EXIT-DESIGN.md; no real profile or production-volume test was run.

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

### Audit.22 implementation: final stop admission boundary

The guard is integrated and paired development builds match. 136 unit tests and
104 artifact-bound memory observations pass. Only Manager changes within the JAR
from audit.21. See [scope and pending clean qualification](audit/STOP-BEFORE-SEND.md).
Next: commit source, produce paired clean builds, rerun the complete regression
set and package both pinned runtimes. Do not infer hardware/release readiness.


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

Next application milestone: fail closed when initial read-timeout installation or
verification fails, before publishing the socket. Keep the original TCP connection
timing and single-address behavior. The bounded-TCP prototype is separate new
timing policy and is not integrated or qualified. Audit caller exception categories,
interrupt state and socket lifetime, then promote only the reviewed narrow repair.
DNS, TCP writes and total-operation bounds remain separately unresolved.


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


### Audit26 completed local milestone

Clean `46dec9e` passes sixteen candidate gates and 170 units, paired builds and
packages, repeated unsigned ZIPs and schema-validated SPDX inventories. Evidence
assembly `809bdb2` binds 38 records and 753 source proofs. Only two RaidSystem
diagnostic password reads change from audit25; all other JAR entries remain
identical. See [scope](audit/MODEL-DIAGNOSTIC.md),
[ledger](audit/model-final-integrity.json) and [archive map](audit/model-archival-map.json).
Hardware remains deferred until actual need. Full native GUI requires a disposable
macOS environment; user.home does not isolate native preferences. Existing native
component probes remain development-only. Physical Intel, signing/notarization,
redistribution and other documented gaps remain open. HTTP remains plaintext.
Next safe local investigation: inspect preference resource lifetime and file
privacy using only synthetic files; do not access real saved profiles.


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


### Private atomic-save security investigation — nonshipping

Audit27 remains the packaged application. The in-place private-descriptor
experiment cannot protect new content from an already-open reader. The separate
atomic-save experiment writes a checked private temporary inode and replaces the
profile only after serialization and raw close. This deliberately changes inode,
ACL, hard-link, metadata and failed-save behavior; no controller code, command,
polling or retry timing changes are made by the experiment.

Actual Claude reviews identified and refined read-only/deny-write preservation,
partial JNI registration, stale-library binding, cleanup reporting and negative
control coverage. Native methods are private, eager linking and ABI token
0x58415201 are required, and partial registration is undone on failed load.
Sustained exceptional failures can leave private temporary files per attempt;
there is no blanket zero-leftover claim and no unsafe glob cleanup.

The latest development matrix passes on both pinned runtimes: 16 variants of
37 cases; 26 native negative controls; 44 injected-failure/recovery variants;
32 library/permission bindings; four empty JNI load controls; two full JNI-checked
functional variants; four pure-Java suppression variants. x64 is Rosetta.
These are dirty-source, nonshipping observations, not application qualification.
See [scope and reproduction](experiments/atomic-preferences/README.md) and
[development evidence](audit/atomic-preference-development.json).

Next safe milestone: qualify the actual FileBasedPreferences.synchronize caller,
resolve experimental filename restrictions, visible save failures and replacement
frequency, then integrate native packaging and rerun the complete candidate and
unsigned release checks. Real remote filesystems, ownership-disabled filesystems,
other users/root, arbitrary JVM exhaustion and full GUI remain unqualified.
Hardware is deferred until actual need. No disposable VM/account or signing setup
is available; continue offline and finish unsigned local packages. The immutable
Apple JAR and installed app remain unchanged. HTTP remains plaintext; no stored
credential encryption claim is made.


Clean experimental reproduction at `ff84e6a` passes the same expanded matrix
with `source_dirty=false`, all source bytes verified against that Git commit,
repeated native outputs, and compiler/runtime/probe/native-input/output hashes
checked before and after. Record: [atomic-preference-clean.json](audit/atomic-preference-clean.json).
`qualification=false` remains explicit: this qualifies the nonshipping experiment
only, not FileBasedPreferences caller integration or the application release.


### Clean preserved-caller evidence — nonshipping

The atomic-save adapter now passes the preserved Apple and audit27
FileBasedPreferences.synchronize caller at clean source `7a5d32b`: four
ARM/Rosetta-x64 interpreted/compiled variants of 19 cases, plus sixteen
caller-specific negative controls. Actual store locking, XML bytes, Error
identity, unchanged changeCount, interrupt flags, failure retention and zero
FD/GC growth are asserted. Source bytes match Git before and after execution.
See [caller scope](experiments/atomic-preferences/caller/README.md) and
[clean caller record](audit/atomic-caller-clean.json).

FACT: only the nonshipping adapter JAR changes; release audit27 and the installed
app remain unchanged. UNRESOLVED: original filename encoding/path behavior,
real default preference-directory policy, save-error feedback and replacement
frequency, native packaging and full candidate/release requalification. This
record is explicitly `qualification=false`; factory/Main/GUI, physical Intel and
real controllers are not validated. No hardware action was performed.


### Clean filename and save-site findings — nonshipping

Clean source `6791a76` passes four ARM/Rosetta-x64 interpreted/compiled filename
variants of 22 cases. Raw APFS directory-entry bytes, File/NIO normalization,
observed 0644 modes, permission-check calls and synthetic XML hashes are recorded.
The original-style stream substitutes `?` for lone surrogates; the experimental
encoder rejects them. Kernel resolution of dotdot must be preserved: nonexistent
or file components cannot be lexically removed. File.list normalizes NFD names
to NFC, so it is not sufficient evidence of stored filename bytes.

Read-only bytecode selection verifies 22 original classes and 23 methods matching
selected call names. Original Apple counter writes are load reset and set/remove
increments; store does not reset it. The seven selected putfield instructions
include three belonging to the separate chaotic Preferences class. Among selected
audit27 classes only FileBasedPreferences differs. No retry, count, polling or
controller changes follow from these observations. MacPreferences null default is
`preferences.plist`.

See [filename evidence](audit/atomic-path-clean.json),
[static evidence](audit/preference-save-site-clean.json),
[scope](experiments/atomic-preferences/paths/README.md), and
[save-site findings](audit/PREFERENCE-SAVE-SITES.md). Actual Claude reviews found
no blockers in this bounded scope; clean source bytes match Git.
`qualification=false`: audit27 packages remain unchanged. Existing-name aliases,
PATH_MAX, native release integration and visible save failures remain open. An
unavailable native helper must fail visibly rather than use an insecure in-place
fallback. Full GUI, physical Intel and hardware remain unverified/deferred.


Clean filename/static records at `91aa134` reproduce the same passing matrices
and correct `compiler_tree_sha256` to the digest string, rather than the full
compiler lock object previously stored under that name. The older records remain
historical and are not overwritten. Current records:
[filename v2](audit/atomic-path-clean-v2.json) and
[static selection v2](audit/preference-save-site-clean-v2.json).

The atomic-save implementation and preserved caller are committed but remain
nonshipping. Next required product work is to port tested path handling without
fixture properties/hooks, provide fixed-code visible save failures, integrate
architecture-specific native loading/packaging, and rerun the complete candidate
and unsigned archive/SPDX checks. Neither application launch nor these bounded
experiments establishes full application functionality. The original JAR,
installed JAR, audit27 release JAR and frozen integrity ledger remain unchanged.
