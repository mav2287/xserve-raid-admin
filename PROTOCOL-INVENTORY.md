# Protocol inventory

## Evidence and boundaries

Facts below derive from the hash-verified candidate JAR, its `javap -c -p -constants` disassembly and network-denied fixtures. [CONTROLLER-OPERATIONS.md](audit/CONTROLLER-OPERATIONS.md) lists all **59 factory overloads**, with command, endpoint and parameter/default literals. [static-inventory.json](audit/static-inventory.json) records methods and call sites. No method was invoked against a controller. Synthetic request serialization and retry tests use memory only; no firmware transmission occurred.

## Transport

- `HttpConnection`: scheme `http`, port 80, connection timeout 5,000 ms, default socket timeout 30,000 ms. No TLS transport is implemented. This does not prove that every possible firmware lacks another endpoint.
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
