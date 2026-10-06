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
