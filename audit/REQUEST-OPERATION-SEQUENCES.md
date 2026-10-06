# Ambiguous outcome and queued operation sequencing

Facts below derive from immutable original bytecode. Eight inspected caller
classes are byte-identical in audit.13; [identities](request-operation-sequence-identities.json)
pin them and the complete extracted-class disassembly digest. No original app,
controller, firmware action or volume was exercised. This is source evidence,
not a runtime qualification of these workflows.

## Confirmed source facts

| Original method | Relevant bytecode PCs | Result handling |
|---|---|---|
| ManagementController.handleDeleteRaid | optional initialization-stop post 219; delete post 267; unmapLuns 285; last-array restart post 356 | Async posts have null handlers; restart follows enqueue, not delete acknowledgement. unmap helper requires separate trace. |
| RaidSetCreator.createRaidSet | create post 376; first-array restart post 437; waitForRaidSetOnline 535; assignment post 783; flush 837; second restart 857 | Async posts have null handlers. First restart precedes state wait. Later mapping depends on polled state; controller-online timeout is caught and execution continues. |
| Restarter.restart | flush posts 44/74; RAID restart posts 103/132; system property flush 203/273; system restarts 317/384 or 416/484 | Async null handlers; target 1/2 depends on flags and primary controller. Pair includes original 10-second sleep. |
| FirmwareUpdater UpdateThread.run | cache-disable regions 99–135 and 440–476; restart posts 1373/1546 | Cache-helper exceptions are swallowed. Restart getResultCode branches 1385→1388 and 1558→1561 reach the next instruction regardless of result. A synchronous exception reaches outer IOException handler 1622 instead. |
| RaidSystem post methods | target overload sets target before CommunicationsManager post | Target is captured by cloning; body/header sharing remains as characterized separately. |
| CommunicationsManager SyncSender | Object.wait 52; interrupt handler 58; callback notifyAll 11 | Interrupt reports failure without removing the queued transaction. A later send remains possible. |

Manager run PC 417 prepends a failed transaction on ordinary IOException. The
catch covers connect/send and cannot establish whether controller action occurred.
A -102 result does not identify whether a request was sent or applied. The generic
audit.13 security-marker path retired the transport and allowed the next queued
transaction; audit.14 stops local dispatch before callbacks. Async null-handler callers do not inspect that result.

## Security implications and limits

**Inference:** returning a terminal result for the failed command while continuing
queued writes can permit restart, flush or LUN changes whose prerequisite outcome
is unknown. This is a distinct safety gap from repeating the failed command.
Audit.13 null-message recovery also allows subsequent work after a failure that
previously killed the worker. Its isolated next-read success is therefore not
proof of safe operation sequencing.

[Actual Claude review](claude-review/AMBIGUOUS-IO-CALLER-SEQUENCES.txt) independently
confirmed these branches and required queued and delayed follow-up containment.
No broad classifier is implemented. getCommand alone is insufficient, shared RPC
bodies make later classification unstable, and apparent getter names do not prove
controller-side idempotency. A retry allowlist requires stronger evidence.

Current audit builds remain unqualified for production/controller operation and
release. [audit.14 session containment](SECURITY-SESSION-CONTAINMENT.md) stops security-marker
follow-up dispatch; the ordinary
nonnull IO replay gap remains open. Remaining source checks include LunMapper,
firmware flash/cache helpers, shutdown=true handling, polling failure behavior,
other UI paths and direct CLI entry/exit. Hardware outcomes remain unmeasured.
