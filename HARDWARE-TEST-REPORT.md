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
