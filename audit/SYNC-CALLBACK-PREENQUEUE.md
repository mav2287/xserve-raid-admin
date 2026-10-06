# Audit.17 synchronous callback guard

Status: clean memory-fixture qualification passed at source/fixture/package commit `47166ed`. This is defense in depth, not
proof of a reachable original GUI workflow. Original source facts and actual
[Claude design](claude-review/SYNC-CALLBACK-PREENQUEUE-DESIGN.txt) show that a
SyncSender posts its request before checking whether it is on the manager thread.
A callback which catches the resulting IllegalStateException can return normally
and leave the request executable after reporting failure.

The hash-locked constructor now performs the exact original thread comparison and
throws the exact original fixed exception before the second clone/enqueue. The
first clone in Manager.postMessage remains original. Code length 109 becomes 138;
stack/locals 7, major 47, original constant pool, exception table, nested metadata,
other methods, monitor/wait/interrupt instructions and old duplicate thread guard
remain unchanged. PC14..19 is a short goto109 with dead padding; the appended
check uses original #4..#9 and queue bytes, then goes back to PC20. The transformation
fallback now rejects unsupported method names instead of treating them as toString.
No commands, headers, polling, retry timing, shutdown or GUI behavior is rewritten.

The constructor-only change is pinned to original class
`69c71a7d47c4c96c713741a86e2539ca6289c6e6b947aae0dec959d9edc161ab` and patched class
`9313aae6769e648e0611e1590de96e0826bf77a45feda06608fbc5abb881170c`.
Only that class entry changes from audit.16. No third-party dependency is introduced.

The real worker memory fixture catches the forbidden callback exception, checks
queue and clone counts, and compares exact second serialized body internally.
Original queues and sends the synthetic restart; candidate rejects before enqueue
and sends the intended getTime follow-up. Both stop at the second scripted response
to bound original continuation; the original follow-up is drained with -102 after
that stop, while candidate getTime succeeds. This is deliberately a memory seam,
not proof of real controller behavior. An initial three-request experiment hit the
socket guard before contact; that experiment is excluded from qualification.
Current cases assert zero guarded operations and emit no header/body values.

Other cases cover another thread's synchronous wait, exact response identity and
two clones, an ImmediateManager callback before wait (test subclass allocated with
Unsafe; never a production constructor), stopped-session rejection before cloning,
and a pending interrupted wait. The latter still returns a plain IOException and
leaves one queued transaction on a live manager: cancellation remains unfixed.
Interpreted/compiled runs on both pinned runtimes and a verifier-valid restored
constructor mutant in default execution mode per architecture are required by the standalone strict posting gate. Byte-mask
negative tests reject every trampoline byte, dead padding, frame/handler changes
and changes to other methods. Application launch is not evidence.

[Claude connect-failure design](claude-review/CONNECT-FAILURE-TERMINAL-DESIGN.txt)
identifies the higher-risk TYPE_CONNECT failure/later-send path for the next
milestone. It corrects the initial design review: run already checks stopped after
doConnect; the connection-failure fix needs doConnect changes, not another run
check. The callback patch is independently valid defense in depth and does not
close TYPE_CONNECT, interruption, post/exit atomicity, lock-order liveness, callback
failure cleanup, GUI recovery or real controller/release qualification. Legacy
HTTP is plaintext. No production-volume test or installed-app modification occurs.

Claude implementation review required proving the caller really reaches WAITING
before releasing the worker; that state is now asserted. Complete artifact identity
is checked against expected-build and the audit.17 matrix pin, supplementing the
constructor-only mask. Parity cases are unchanged behavior, not additional fixes.
Only the successful-response callback path is exercised. An escaping callback
Error at run PC509 can still strand the worker without stopping the manager.

## Clean qualification and archive mapping

Two source builds reproduce JAR
`948c1d8587b43b7b004f193dd5d5eced4ffa8c6d7fd53943c029149f2245b28a`.
Seven gates passed at clean commit `47166ed`, each exit 0 with empty stderr:
[security](sync-preenqueue-clean-security-2.json), [transport](sync-preenqueue-clean-transport-2.json),
[runtime](sync-preenqueue-clean-runtime-2.json), [resources](sync-preenqueue-clean-resources-2.json),
[shared stream](sync-preenqueue-clean-shared-2.json), [factory](sync-preenqueue-clean-factory-2.json)
and [posting](sync-preenqueue-clean-posting-2.json). These are byte-for-byte copies
of the identically named build records. The first clean run's posting checker
failed a metadata lookup caused by a tuple in place of a Path. That run is excluded;
the corrected gate, requalified seven-gate set and package/fixture identity use
`47166ed` and the `-2` records. Application bytes did not change in that correction.
The [108 Python tests](sync-preenqueue-clean-tests.json) pass from the same commit.

The posting record has eight original/candidate interpreted/compiled positives
and two restored-constructor negative controls (default mode, one per architecture).
Both mutant archives have identical hashes; restoring the constructor reproduces
the audit.16 JAR. Other gates retain the 143-line recovery matrix, worker failure
mutants, XML quotas, headers, shared-stream and 116-row factory regressions.

[Package records](sync-preenqueue-bundle-results.json) preserve vendor signatures
and reproduce files, modes and directory modes twice per architecture. Trees:
aarch64 `c1ad83d067cc088315ad0ad9f860a43dce42b5cd244204a6bcdb5b8a5f22f2a9`;
x64 `ffe58e27a43ade1691d26b3894510b4b38d674f7a0f5eafa8316f109642e7d88`.
[Arm64 diagnostics](sync-preenqueue-diagnostics-aarch64.json) and
[x64 diagnostics](sync-preenqueue-diagnostics-x64.json) match the reviewed artifact,
manifest and audit.17 claim. Their architecture field describes the host; x64 runs
under Rosetta. The runtime gate hashes Contents/Home; lock checks hash Runtime.jdk.
Their distinct measured scopes are retained in final integrity. Application signing,
notarization, native UI and physical Intel acceptance remain unperformed.

[Final integrity](sync-preenqueue-final-integrity.json), SHA-256
`22034b0f12291e3a43832b4f60067bfaf8fe4c304293473874bc3c120d10da5b`, hashes all seven records, tests, bundles and diagnostics, maps role
keys to archive filenames, verifies fixture sources against committed bytes and
preserves original mode 444 and installed-app files/modes. Only SyncSender.class
changes from audit.16 JAR entries. No controller contact or production-volume test
occurred, and no installed application was modified.

[Claude clean review](claude-review/SYNC-CALLBACK-PREENQUEUE-CLEAN-EVIDENCE.txt)
found no evidence blocker and required updating pending documentation, retaining
archive file mappings, excluding the metadata-error run and pinning final integrity.
Those changes are now present. No qualification input changed in this archive step.
Claude's review compared recorded hashes; executed gates and final integrity supply
the independent checksum verification. The additional copied guard/enqueue and old
check snapshot mutations requested in follow-up are covered by the 108-test record.
