# Audit.17 synchronous callback guard

Status: development; clean qualification pending. This is defense in depth, not
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
