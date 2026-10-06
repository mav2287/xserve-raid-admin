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
