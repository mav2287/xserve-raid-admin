# Hardware qualification report — 2026-10-05

**Not run.** No controller was contacted by this audit. No network capture, GUI launch, mounted-volume test, mutation or firmware transfer occurred. Existing addresses in the handoff remain historical observations, not newly verified endpoints. Mount/backup/firmware/identity preconditions have not been established.

Read-only evidence consists of local source/binary inspection, copied-bundle verification, local builds and network-denied fixtures described in [AUDIT-BASELINE.md](AUDIT-BASELINE.md). These do not qualify hardware behavior.

Before hardware qualification, record disposable/unmounted target status, backups, both controller identities/firmware, chosen interface, exact operation, recovery plan and immediate approval for each restricted action. Use [CAPTURE-PROCEDURE.md](CAPTURE-PROCEDURE.md) and the updated acceptance matrix. No restricted operation is queued or scheduled.

User clarified that the available RAID has production or mounted volumes. No hardware test is authorized by that clarification. Both Apple silicon and Intel must be supported.

Latest user direction: real RAID tests are deferred until the corresponding
commands or workflows actually become necessary. Complete safe local work; do
not contact hardware for this completion effort. All restricted-operation
confirmation boundaries remain in effect immediately before any future action.
No hardware test is queued or scheduled; deferred is not pass or unsupported.


Audit25 local gates, unsigned archives and SPDX documents are complete. These are software/packaging evidence only. Hardware tests remain deferred by the user, with no controller contact or production/mounted-volume test. The installed app remains identical to intake. No destructive or setting-changing operation is queued.


Audit26 adds sixteen passing local gates, 170 units, repeated packages/archives
and SPDX inventories. It does not change hardware qualification: no controller
contact, mounted/production-volume test or installed-app modification occurred.
Hardware is deferred until actual operational need, with immediate confirmation
still required before every restricted operation. HTTP is plaintext.
