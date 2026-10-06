# Detailed implementation and audit plan

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
