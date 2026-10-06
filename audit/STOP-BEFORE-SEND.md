# Audit.22 final stop check before send

Implemented locally; clean integrated qualification is pending. This does not
establish controller, native GUI, physical Intel or release acceptance.

Fact: audit.21 reads stop before SyncSender claim, then marks the transaction
started and calls send. Shutdown can land between that read and claim/exposure.
Audit.22 adds one direct read of private volatile `stopped` after claim and before
exposure. If true, it constructs the original unsent -102 shutdown response at
280. It bypasses the old connection-failure suppression flag only on this new
branch. Original callback-attempt and first-response protections still apply.
If false, original exposure and send continue. A later shutdown cannot establish
that a command was unsent; its actual reply or unconfirmed outcome is retained.
This defines a final admission boundary, not atomic cancellation of TCP writes.
Connection setup, command serialization, polling and retry timing are unchanged.

Only Manager changes within the JAR relative to audit.21. The 17-byte tail adds
four exception-handler rows with the original priority; pool, fields, methods,
stack/locals and all unrelated bytes reconstruct exactly. Current Manager SHA256:
`f2960fbf802500891e23a916441f8b7c586d9ae70d6dba5760d40bc9acf04059`.
The integrated JAR SHA256 is
`202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd`.
Independent javap/CFG checks validate every instruction and handler row and prove
legacy requeue unreachable. Unit negative controls reject code/pool/member
changes and four semantic mutations. The complete unit suite passes 136 tests.

Development evidence: 104 memory-only observations compare the exact audit.21
reference with the integrated artifact. They cover sync/async stop after the old
read, stop after claim, claimed caller interruption, queued requests, artificial
stale suppression flags, synthetic SetTime requests and after-admission actual
memory replies. Send-entry counters distinguish no send from incomplete body
recording. Assertion failures are recorded outside containment. Shutdown
exceptions must originate in dispatchLoop, not terminal helper cleanup. Async
callbacks retain their original worker thread on this normal shutdown path.
The after-admission controls use the actual candidate JAR without a hook and
compare exact body bytes, response identity where applicable, and attempt counts.

Test-only hook JARs are constructed in temporary directories. Builders bind the
immutable original and audit.21 reference, reconstruct the complete hook, and
reject every non-Manager entry difference. The gate compares the unhooked
prototype to the actual packaged Manager, its security golden and the complete
JAR entry delta. No hook class/reference is added to the production artifact.
Targeted Xcomp observations require an installed dispatchLoop nmethod and no
compilation failure; other methods are interpreted in those variants. Separate
Xint observations use the full interpreter. This is bounded method compilation
proof, not whole-app compiled execution qualification.

Excluded: preliminary evidence before independent assertion and send-entry checks;
PrintCompilation stdout interleaving; a full-Xcomp stale task with no installed
nmethod; pre-integration source maps and initial diagnostics on an old golden.
None is accepted as successful qualification or described as a product fix.
Clean source/build/fixture records must follow the source commit.

Claude consultations are archived as `CLAUDE-STOP-ADMISSION-*.txt`. Corrections:
Sender first-response behaviour was verified by existing independent structure
checks, not by pinning the candidate-sender javap file directly. The new gate now
also records that file. Original normal stopped callbacks remain on the worker;
EDT delivery applies to terminal helper cleanup, not this guard. The original
suppression path remains unchanged for already reported failures. The new guard
constructs a shutdown independently of that flag, with positive stale-flag tests.

Unresolved: connect/write/whole-operation deadlines, controller response/status
and empty-ack interpretation, outbound mutable body/headers, GUI firmware binding,
full caller/GUI retry flows, native GUI and hardware/release qualification. VM
exhaustion, ThreadDeath and invalid-metadata completion remain best-effort. x64
runs use Rosetta. HTTP remains plaintext. No app preview, controller contact,
production-volume test or installed app modification was performed.
