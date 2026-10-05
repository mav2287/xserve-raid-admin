# Protocol inventory

## Evidence and boundaries

Facts below derive from the hash-verified candidate JAR, its `javap -c -p -constants` disassembly and network-denied fixtures. [CONTROLLER-OPERATIONS.md](audit/CONTROLLER-OPERATIONS.md) lists all **59 factory overloads**, with command, endpoint and parameter/default literals. [static-inventory.json](audit/static-inventory.json) records methods and call sites. No method was invoked against a controller; firmware request construction/transfer was not exercised.

## Transport

- `HttpConnection`: scheme `http`, port 80, connection timeout 5,000 ms, default socket timeout 30,000 ms. No TLS transport is implemented. This does not prove that every possible firmware lacks another endpoint.
- `HttpRequest`: defaults to POST, HTTP/1.1 and `Content-Type: application/xml`. Credentials are carried by `AcpxConnection.addHeaders` as `ACP-User` and `ACP-Password`; never log their values.
- `AcpxConnection` defaults to persistent and unencrypted; adds `Apple-Xsync` when a target is present and `Connection: close` for shutdown/restart/nonpersistent requests. Optional `Content-Encoding: acp-crypt` is body handling, not TLS and does not protect credential headers.
- Important fidelity detail: `HttpRequest` defaults its user agent to `Apple-Xserve_RAID_Admin/1.5.1`, but `AcpxConnection.addHeaders` overrides it to **`Apple-Xserve_RAID_Admin/1.6.0`**. Preserve this discrepancy until reviewed wire evidence justifies changing it.
- Plist request serialization and map ordering are inherited. ACP-style bodies map command to parameter dictionary; RPC-style bodies contain a `requests` array with `method` and `inputs`. RPC names such as `/raid/array/create` are **body method names**, sent to `/cgi-bin/perform`.

## HTTP endpoint families

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

`FirmwareBundleConnection`, `FirmwareUpdater`, `FirmwareUpdatePane` and `UpdateFirmwareRequest` implement loading, chooser, selection, progress and transfer. Manifest keys include `firmware-version`, `firmware-date`, `xserveraid-raid-controller-update-image`, `xserveraid-coprocessor-full-image`, and `xserveraid-coprocessor-update-image`; expected paths include `raid-controller/updateROM.bin` and `coprocessor/updateROM.bin`. A RAID firmware version header is conditionally added. No authoritative good `.xfb` was supplied; no preflight or transfer success is claimed. Host signature verification and controller-side validation remain distinct unresolved questions.

## Discovery, OS and other network surfaces

`_xserveraid._tcp` and `_xserve._tcp` appear in discovery bytecode and plist metadata. JmDNS 0.2 provides mDNS; interface selection, duplicate identity handling and sleep/wake remain unqualified. Manual IP is an existing UI path. Help/URL opening goes through OS integration, and XML external resolution can initiate unexpected network access. Notification test email is a controller RPC; it was not sent.

## Offline evidence and capture procedure

[Parity results](audit/parity-results.txt) cover ten credential-free read factories serialized through the original `HttpRequest` plus synthetic in-memory HTTP response replay. The entire process denies network connections. Original/installed/audit outputs match under the locked JDK. ACP header injection, actual sockets, persistence, timeouts, UI, polling and hardware are outside this test. No genuine controller fixture has been obtained.

[CAPTURE-PROCEDURE.md](CAPTURE-PROCEDURE.md) defines a narrow metadata-only capture without raw credential-bearing pcap files. Full wire equivalence remains **not run**. A future comparison must retain verb/path, nonsensitive headers, order, sanitized bodies, timings, reuse and terminal UI result while omitting credentials before any persistence. Do not turn legacy debug logging on or store raw HTTP captures.
