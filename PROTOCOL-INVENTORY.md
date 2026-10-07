# Protocol inventory

## Evidence and boundaries

Facts below derive from the hash-verified candidate JAR, its `javap -c -p -constants` disassembly and network-denied fixtures. [CONTROLLER-OPERATIONS.md](audit/CONTROLLER-OPERATIONS.md) lists all **59 factory overloads**, with command, endpoint and parameter/default literals. [static-inventory.json](audit/static-inventory.json) records methods and call sites. No method was invoked against a controller. Synthetic request serialization and retry tests use memory only; no firmware transmission occurred.

## Transport

- `HttpConnection`: scheme `http`, port 80, no explicit application connect deadline, normally 30,000 ms per socket read (setup-error caveat in [source correction](audit/TRANSPORT-TIMEOUTS.md)). No TLS transport is implemented. This does not prove that every possible firmware lacks another endpoint.
- `HttpRequest`: defaults to POST, HTTP/1.1 and `Content-Type: application/xml`. Credentials are carried by `AcpxConnection.addHeaders` as `ACP-User` and `ACP-Password`; never log their values.
- `AcpxConnection` defaults to persistent and unencrypted; adds `Apple-Xsync` when a target is present and `Connection: close` for shutdown/restart/nonpersistent requests. Optional `Content-Encoding: acp-crypt` is body handling, not TLS and does not protect credential headers.
- Important fidelity detail: `HttpRequest` defaults its user agent to `Apple-Xserve_RAID_Admin/1.5.1`, but `AcpxConnection.addHeaders` overrides it to **`Apple-Xserve_RAID_Admin/1.6.0`**. Preserve this discrepancy until reviewed wire evidence justifies changing it.
- Plist request serialization and map ordering are inherited. ACP-style bodies map command to parameter dictionary; RPC-style bodies contain a `requests` array with `method` and `inputs`. RPC names such as `/raid/array/create` are **body method names**, sent to `/cgi-bin/perform`.

## HTTP endpoint families

Offline response characterization now confirms that HTTP status is ignored;
result codes come from the plist `status`. Header lookup is case-sensitive,
duplicate length fields use the last value and missing/lowercase length can
produce empty success. These original semantics are preserved, with explicit
open risks in [G12](GAPS.md#g12--http-response-framing-and-error-interpretation)
and [fixture findings](audit/HTTP-RESPONSE-FINDINGS.md).

| Actual HTTP path | Purpose | Safety classification |
|---|---|---|
| `/cgi-bin/noop` | No-op request/authentication context | Read-only candidate; auth side effects unqualified |
| `/cgi-bin/acp-get` | Single/multiple property retrieval | Read |
| `/cgi-bin/acp-set` | Property writes including management settings | Mutation; property-dependent risk |
| `/cgi-bin/rsp-action` | Controller page/time, power-related, array/diagnostic commands | Mixed; never classify by endpoint alone |
| `/cgi-bin/acp-action` | Power state, power/restart, create/delete, LEDs/buzzer/NVRAM | Mixed/high risk |
| `/cgi-bin/diagnostic-action` | Temperature and device-property retrieval | Read for enumerated getters only |
| `/cgi-bin/perform` | Structured RPC for system, events, cache, RAID, fibre/LUN operations | Mixed/high risk |
| `/cgi-bin/firmware-update-full` | Full coprocessor image | Restricted firmware transmission |
| `/cgi-bin/firmware-update` | Coprocessor update image | Restricted firmware transmission |
| `/cgi-bin/update-raid-firmware` | RAID-controller image | Restricted firmware transmission |

## Operation families and semantics to qualify

Read candidates: status, properties, pages, event log/date, time, temperature/device properties, power state, POST results and signature reads. Requests with apparently read-like names still require parameter and hardware-target review.

Mutations: set properties/time; clear logs; identify LEDs/buzzer; system monitor reset; drive/RAID cache, synchronize cache, slow-read bypass and prefetch; fibre-channel speed/topology/hard-loop ID; LUN masks/assignment; test email; JBOD masking; flush/reset NVRAM; array create (RPC and ACP variants), delete, expand, slicing; verify/recalculate parity; background read/write scans and threshold; delete broken member/change broken ID; power/restart/controller restart; LED/disk/cache/fibre/serial diagnostics; write signature; firmware. “Diagnostic” does not imply non-destructive. No writes were exercised.

Polling/retry facts: `RaidSystemAgent.DEFAULT_POLLING_DELAY=15000`; `CommunicationsManager.CONNECT_BACKOFF_CEILING=3600000`; one queued worker path and reusable connection. These are defaults/code structure, not measured request rate or confirmed lifecycle behavior. A full status update fans out through multiple getters; the class/method inventory captures calls, but firmware-conditioned sequence/order and retry cadence need sessions.

## Firmware

`FirmwareBundleConnection`, `FirmwareUpdater`, `FirmwareUpdatePane` and `UpdateFirmwareRequest` implement loading, chooser, selection, progress and transfer. Manifest keys include `firmware-version`, `firmware-date`, `xserveraid-raid-controller-update-image`, `xserveraid-coprocessor-full-image`, and `xserveraid-coprocessor-update-image`; expected paths include `raid-controller/updateROM.bin` and `coprocessor/updateROM.bin`. A RAID firmware version header is conditionally added. An Apple-served `firmware-1.5.1-1.51.xfb` is now acquired and hash-pinned. Guarded wrapper tests check its metadata and image hashes on both pinned runtimes; preflight UI and transfer remain unqualified. The full-image key is absent in this package and must not be made mandatory. Host signature verification and controller-side validation remain distinct unresolved questions.

## Discovery, OS and other network surfaces

`_xserveraid._tcp` and `_xserve._tcp` appear in discovery bytecode and plist metadata. JmDNS 0.2 provides mDNS; interface selection, duplicate identity handling and sleep/wake remain unqualified. Manual IP is an existing UI path. Help/URL opening goes through OS integration, and XML external resolution can initiate unexpected network access. Notification test email is a controller RPC; it was not sent.

## Offline evidence and capture procedure

[Parity results](audit/parity-results.txt) cover ten credential-free read factories serialized through the original `HttpRequest` plus synthetic in-memory HTTP response replay. The entire process denies network connections. Original/installed/audit outputs match under the locked JDK. ACP header injection, actual sockets, persistence, timeouts, UI, polling and hardware are outside this test. No genuine controller fixture has been obtained.

[CAPTURE-PROCEDURE.md](CAPTURE-PROCEDURE.md) defines a narrow metadata-only capture without raw credential-bearing pcap files. Full wire equivalence remains **not run**. A future comparison must retain verb/path, nonsensitive headers, order, sanitized bodies, timings, reuse and terminal UI result while omitting credentials before any persistence. Do not turn legacy debug logging on or store raw HTTP captures.

The 1.5.1 release notes say LUN Masking was removed from the Advanced panel.
Legacy protocol/class presence does not authorize restoring that UI. The same
notes confirm controller/disk cache changes and an automatic RAID restart during
firmware updates. All remain restricted hardware operations.


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
