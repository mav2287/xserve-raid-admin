# Acceptance matrix

Copy this table into test reports and add evidence links. “Pass” requires an
observable expected result, not the absence of an error dialog.

| Area | Test | Original reference | Compatibility build | Wire parity | Hardware evidence | Status |
|---|---|---|---|---|---|---|
| Startup | Launch from Finder on Apple silicon |  |  | N/A |  | Not run |
| Startup | Launch from Finder on Intel; preserve existing support |  |  | N/A |  | Not run |
| Offline parity | Original and candidate serializer/HTTP-parser fixture on arm64 Java 8/11 and x86_64 Java 11 under Rosetta | `audit/architecture-fixtures.json` |  | N/A | No sockets or GUI | Pass; physical Intel and full functionality not qualified |
| Startup | Launch with no system Java installed |  |  | N/A |  | Not run |
| Startup | Damaged/missing bundled runtime gives useful error | N/A |  | N/A |  | Not run |
| Identity | About/diagnostics show Apple baseline and modern build | Original About unchanged | Diagnostics implemented; About not qualified | N/A | None | Partial — [baseline](AUDIT-BASELINE.md) |
| Discovery | Find both controllers on Ethernet |  |  |  |  | Not run |
| Discovery | Find controllers on Wi-Fi where network permits |  |  |  |  | Not run |
| Discovery | Interface changes do not duplicate or lose identities |  |  |  |  | Not run |
| Discovery | Sleep/wake recovery |  |  |  |  | Not run |
| Connection | Direct-IP connection to each controller |  |  |  |  | Not run |
| Connection | Monitor authentication |  |  |  |  | Not run |
| Connection | Administrator authentication |  |  |  |  | Not run |
| Connection | Wrong password produces visible failure |  |  |  |  | Not run |
| Connection | Disconnect and reconnect in the same app session |  |  |  |  | Not run |
| Connection | Quit/relaunch and reconnect |  |  |  |  | Not run |
| Connection | One controller unavailable |  |  |  |  | Not run |
| Connection | Controller timeout and later recovery |  |  |  |  | Not run |
| Security | Password absent from all logs and diagnostics | Unsafe toString found statically | audit.4 request redaction and audit.5 bounded appender fixtures pass; other output paths unresolved | N/A | None | Open — [G04](GAPS.md#g04--credential-bearing-logging) |
| Security | External XML entity/file/network access blocked | Fail: original and installed guarded fixtures | Pass: audit.4 guarded Reader/InputStream fixtures | N/A | Offline synthetic only; real response compatibility open | Partial — [G05](GAPS.md#g05--xml-external-resolution) |
| Status | System overview |  |  |  |  | Not run |
| Status | Both controller status pages |  |  |  |  | Not run |
| Status | Drive inventory and state |  |  |  |  | Not run |
| Status | RAID set and volume inventory |  |  |  |  | Not run |
| Status | Power, cooling, temperature, and battery state |  |  |  |  | Not run |
| Status | Event log retrieval and display |  |  |  |  | Not run |
| Status | Controller time display and refresh |  |  |  |  | Not run |
| Polling | Continuous 24-hour monitoring without loss |  |  |  |  | Not run |
| Polling | Request rate matches expected original behavior |  |  |  |  | Not run |
| Network | Read both controller network settings |  |  |  |  | Not run |
| Network | Validate network-setting edits before submission |  |  |  |  | Not run |
| Network | Apply and rediscover after approved address change |  |  |  |  | Not run |
| RAID | Read RAID configuration |  |  |  |  | Not run |
| RAID | Create test RAID set on disposable media |  |  |  |  | Not run |
| RAID | Delete test RAID set with confirmation |  |  |  |  | Not run |
| RAID | Rebuild begins with designated replacement disk |  |  |  |  | Not run |
| RAID | Rebuild progress and completion are accurate |  |  |  |  | Not run |
| Drive | Identify and inspect each drive |  |  |  |  | Not run |
| Drive | Failure/removal/insertion state transitions |  |  |  |  | Not run |
| Cache | Read cache configuration |  |  |  |  | Not run |
| Cache | Approved reversible cache setting change |  |  |  |  | Not run |
| Diagnostics | Retrieve available diagnostic information |  |  |  |  | Not run |
| Power | Restart one test controller |  |  |  |  | Not run |
| Power | Reconnect after controller restart |  |  |  |  | Not run |
| Firmware | Reject wrong extension/type visibly |  |  | N/A | Emulator | Not run |
| Firmware | Reject malformed archive visibly |  |  | N/A | Emulator | Not run |
| Firmware | Parse known-good `.xfb` and show metadata | Apple-served 1.5.1 archive pinned | Wrapper metadata/image hashes pass; display untested | N/A | Offline only | Partial; preflight UI open |
| Firmware | Confirm exact images before transfer |  |  | N/A | Offline | Not run |
| Firmware | Transfer progress is visible |  |  |  |  | Not run |
| Firmware | Controller acknowledgement is verified |  |  |  |  | Not run |
| Firmware | Restart/reconnect/version verification |  |  |  |  | Not run |
| macOS | File chooser and dialogs behave normally |  |  | N/A |  | Not run |
| macOS | Keychain remember/update/forget | N/A |  | N/A |  | Not run |
| macOS | Menus, shortcuts, focus, Retina, accessibility |  |  | N/A |  | Not run |
| Distribution | Clean install passes Gatekeeper | N/A |  | N/A | Clean Mac | Not run |
| Distribution | Signature and notarization validate | N/A |  | N/A |  | Not run |
| Distribution | Offline reproducible build matches manifest | Upstream archive hashes differ | Audit content matches twice on locked host | N/A | None | Partial; release open — [G08](GAPS.md#g08--release-engineering) |

## Evidence format

For each completed row, record:

- Build commit and application hash
- macOS version and architecture
- JRE version and hash
- RAID firmware versions and controller address/identity
- Preconditions, including whether volumes were mounted
- Exact action taken
- Expected result
- Actual result
- Relevant redacted log excerpt
- Packet-capture comparison or reason it is not applicable
- Controller event-log entry where applicable
- Pass, fail, blocked, or unsupported conclusion
- Issue link for every failure or unexplained difference


## 2026-10-05 audit scope and added coverage

“Original” distinguishes the repository original candidate from the installed
patched reference where relevant. No hardware acceptance row passes from static
inspection or fixture serialization. Unchanged Not run rows remain intentionally
unclaimed. Exact hashes, host, JDK, preconditions and fixture commands are in
[the baseline report](AUDIT-BASELINE.md). No hardware event log or
packet capture applies to offline tests; no controller firmware or identity was
queried. Failures/open issues use local stable [gap IDs](GAPS.md).

| Area | Additional test | Result / evidence |
|---|---|---|
| Provenance | Reject unexpected original JAR | Pass: hash guard regression test |
| Build | Preserve every non-allowlisted original entry | Pass: byte comparison |
| Build | Two deterministic unsigned app builds match | Pass on locked host; cross-host not run |
| Harness | Drop credential/header/body/arbitrary event fields | Pass: four-test Python suite includes allowlist cases |
| Protocol | Ten synthetic read request serializers match | Pass: original/installed/audit; no ACP header injection or timing coverage |
| Protocol | Ten in-memory HTTP responses replay | Pass: synthetic OK responses; not controller fixtures |
| Protocol | Malformed HTTP/ACP replies and queued errors | Characterization passes on both pinned runtimes: 21 direct and nine queued cases; original behavior retained. Framing/status defects remain open — [G12](GAPS.md#g12--http-response-framing-and-error-interpretation) |
| Protocol | Two read requests after one response drop | Offline sends first–first–second on connections 1–2–2, callbacks in order with context retained. Concurrency and real reconnect unqualified — [findings](audit/HTTP-RESPONSE-FINDINGS.md) |
| Harness | Network sockets prohibited in parity fixture | Pass: guard denial verified |
| XML | Known Apple plist DTD remains local | Pass: all three JARs on locked JDK |
| XML | Provider, quota controls and bounded nested/entity cases | Characterization complete on both pinned runtimes with JDK positive controls. Bundled parser controls unsupported; legacy depth defect identified. Functional/resource gaps remain open — [findings](audit/XML-RESOURCE-FINDINGS.md) |
| Classloading | FileManager origin and preferences lookup | Runtime shadows shim on Corretto 8/11; guarded Java 8 preferences lookup passes. Shadowing alone is not a defect; [G02](GAPS.md#g02--runtime-and-classloading) |
| Menus | Java 8 About/Preferences fallback | API mismatch observed; GUI not run; [G03](GAPS.md#g03--os-lifecycle-and-menus) |
| Lifecycle | Quit saves state; open-document/open-application hooks | Not run; source no-ops require repair |
| UI | License, About, Help, preferences and Finder document open | Not run |
| Credentials | Monitor/admin password change and forget | Not run; changes require deliberate test targets |
| Notifications | Read settings, validate edits, test email | Not run; no messages sent |
| Time | Set controller time and refresh | Not run |
| Logs | Clear controller/system log; inspect, export and print | Not run |
| RAID | Recognize array, repair LUN map, reset RAID | Not run; potentially destructive |
| RAID | Expand array and set slice size | Not run; disposable media and immediate approval required |
| RAID | Verify/recalculate check data; background read/write scans | Not run; treat as mutation until qualified |
| RAID | Delete broken member/change broken RAID ID | Not run; restricted data operations |
| Fibre | Read/edit speed, topology, hard-loop ID | Not run; volume disruption possible |
| LUN | Masking, assignment and JBOD mask | Not run; volume exposure/disruption possible |
| Cache | Sync-cache, slow-read bypass, prefetch, drive cache | Not run; explicit approval required before changes |
| NVRAM | Flush/reset controller NVRAM | Not run; treat as destructive configuration mutation |
| Diagnostics | LED, buzzer, disk, DRAM, fibre and serial tests | Not run; do not assume diagnostics are read-only |
| Signature | Read/write diagnostic signature blocks | Not run; write is destructive-risk |
| CLI | Complete dispatcher/option behavior matches original | Static inventory only; not run |
| HTTP | ACP headers, target, retries, ordering and persistence | Not run; serializer fixture does not cover these |
| Malformed replies | Authentication failure, delay/drop, truncation/oversize | Not run; real-fixture emulator remains open |

## audit.2 offline compatibility evidence

| Area | Test | Result / limitation |
|---|---|---|
| Folder lookup | Desktop singleton, null/custom types and unused overloads | Pass: `audit/folder-fix-results.json`; GUI workflows remain unrun |
| Preservation | MRJFileUtils ABI and all other method instructions | Pass: `tools/check_folders.py` |
| ACP | Synthetic auth/target/user-agent and plist response through original send | Pass in memory: `audit/transport-observation.json`; no actual authentication or TCP |
| Retry characterization | Dropped response, repeated loss, parse-error callback | Original behavior reproduced; duplicate sends are a risk finding, not a safety pass |
| Firmware stream | Closed/exhausted synthetic stream reuse | Throw-before-send and empty-body retry distinguished; no firmware or network transmission |

## audit.3 macOS callback bridge

`audit/menu-runtime-fixtures.json` records passing API-selection, real-interface
proxy construction, synthetic backend dispatch, proxy identity, ordered file delivery
(including failure on the first file), and quit return/failure cancellation tests.
Runtime matrix: original local Java 8 arm64, Java 11 arm64/x86_64, and pinned
Corretto 8.504.04.1 arm64/x86_64. Intel execution on this host uses Rosetta.
Native singleton registration, real AppleEvents, GUI, preference saves and physical
Intel qualification remain unrun. A failed original save cancels quit and records
a fixed code; visible in-app error presentation remains outstanding.

## audit.4 offline security evidence

`audit/security-fixtures.json` ties fixtures to the reviewed build and records an
independent javap comparison of original class versions, constant-pool prefixes,
and all non-target members. Request hierarchy inspection covers every original
request diagnostic override. Password-change payloads and credential fields are
redacted by the candidate. The original embedded DTD and valid plist fixture
outputs match exactly. No controller operations or real credentials are involved.

## Synthetic archive and logging characterization

- FirmwareBundleConnection class bytes remain identical. Synthetic stored/deflated
  archives exercise manifest/image attributes, continuation lines, missing manifest
  and images, duplicates, corrupt local headers and truncation. Original and candidate
  results match on both pinned runtimes. This does not pass firmware preflight UI,
  real package validity, cache changes, transfer or restart acceptance rows.
- The safe appender is tested through the actual candidate JAR configuration, with
  hostile message/exception objects and synthetic private metadata. Only two fixed
  codes are emitted per process, including after reconfiguration; write failures
  do not escape. Other application outputs and visible GUI failures remain open.

## audit.6 XML security

| Scope | Requirement | Evidence | Status |
|---|---|---|---|
| XML security | Explicit provider, quota readback and external-access denial | audit.6 bounded differential and policy probes; original/candidate accepted hashes, mixed/container depth boundaries and entity quota rejection | Partial — real responses and exhaustive provider semantics remain open; [scope](audit/XML-PARSER-COMPATIBILITY.md) |


## audit.7 response allocation

| Requirement | Evidence | Status |
|---|---|---|
| Reject oversized declared body before allocation | Operand-only Code preservation and candidate-only guarded send/queue fixtures | Partial; framing/recovery and real response compatibility open — [scope](audit/HTTP-ALLOCATION-GUARD.md) |


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


### Audit26 model diagnostics and offline qualification

JAR `7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158`,
clean application/fixture/build/package/release source `46dec9e`; assembler
source `809bdb2`. Sixteen candidate gates and 170 units pass. Model diagnostics
redact both credential fields, including null/empty values. Actual original
differential, getter identity, saved flags and observer counts pass in child
and product loaders; four runtime/mode runs each cover 40 cases. Sixteen
behavioral controls fail at their intended assertion. All other audit25 JAR
entries and controller protocol bytes remain unchanged.

Repeated ARM/x64 packages, unsigned ZIPs, extracted runtime signatures and SPDX
inventories pass. Hardware rows remain deferred, not passed. Full GUI, physical
Intel, signing/notarization and redistribution acceptance remain unverified.
Credential storage/crypt functions remain unchanged; HTTP remains plaintext.
See [scope and reproduction](audit/MODEL-DIAGNOSTIC.md),
[frozen evidence](audit/model-final-integrity.json) and
[archival locations](audit/model-archival-map.json).


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
