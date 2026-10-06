# Audit.19 local stop lock ordering

Status: development; clean qualification pending. Audit.18 remains the current
qualified candidate. This milestone does not change asynchronous admission or
callback timing.

Fact: original run holds the queue monitor while invoking synchronized isStopped
at PC18 and PC45. Original shutdown holds the Manager monitor, then locks the
queue to notify it. This produces an opposing lock order. The same pattern can
block the worker and shutdown forever; failure is demonstrated using exact
ThreadMXBean deadlock pairs in isolated JVMs, not inferred from elapsed time.

The narrow patch makes private stopped volatile (0x0002 -> 0x0042), and replaces
only run's two three-byte invoke instructions with getfield #11. No new constant
pool entries or Code lengths, frames, branches, exception tables or metadata are
introduced. Shutdown, isStopped, exit and all other methods stay byte-identical
from audit.18. Restoring one field flag and two reads reconstructs the entire
verified audit.18 Manager SHA a928b493ecf796ab90415339a20f8f7cd4914afaa3add052bdff1796cad70893.
That class's original doConnect Code reconstructs audit.17 as previously qualified.
The audit.18 measured class pin is linked to its final integrity record.

Volatile is required: the queue-held direct reads must observe the stop write
without acquiring the Manager monitor. The original write-then-notify ordering
and queue condition/exit logic remain. isStopped calls outside the queue monitor
retain their original synchronized behavior. This avoids lost notification while
removing the two direct reverse-lock sites. Request clone code inside the queue
monitor is not a general arbitrary-code lock safety guarantee.

The fixture allocates an empty Manager with Unsafe, skips its self-starting
constructor, and leaves its connection null. It creates no requests, RaidSystem,
polling agent, GUI, profile or transport. A daemon holder retains the Manager
monitor; a daemon worker executes the real run loop. The PC18 case must reach
WAITING on the exact queue before shutdown. The PC45 case starts stopped and must
terminate while the holder still owns the Manager monitor. With either getter
restored, the relevant scenario must show BLOCKED on that exact Manager with the
holder's thread ID, then an exact two-thread deadlock pair. No stack trace, thread
name from outside the fixture, request or credential is logged. A watchdog,
exception or verifier failure fails the check; it is never negative evidence.
Deadlocked controls leave only daemon threads and exit naturally, without interrupt.

There are 20 development observations: eight candidate interpreted/compiled
positives on the two pinned runtimes, ten exact deadlock controls, and two restored-
PC45 controls that still complete the PC18 scenario. This last cross-control
attributes the two sites correctly. The full original both-getter variant would
block at PC18 even in the PC45 scenario, as Claude's focused review corrected.
The -jar launcher has no manifest Class-Path, so application Manager subclasses
must reside in the candidate JAR. Original/candidate inventories find none.
Vendor extension inventories are supplementary: parent loaders cannot link an
application-loader superclass. The direct reads therefore bypass no original
isStopped override. External plugins and native GUI are unqualified.
X64 here runs under Rosetta, not physical Intel.

Candidate JAR f7c829f83735ccd7fd6d36d6b7220bd4be8f82733b38bfa7d150d704f42a6775;
Manager cfefcc5b8cb0b0c15b5f63788503c8e41414b01abe2dbcedcc95cdebca8ecc24.
A recovery feature constant advertises this scoped behavior. No dependency is added.
Original JAR remains an immutable reference and the installed app is untouched.

Actual [atomicity design consultation](claude-review/POST-EXIT-ATOMICITY-DESIGN.txt)
identified caller-thread recursive callback risks in an immediate stopped-post
refusal. That broader admission change is deferred until GUI re-posting and caller
lock evidence are reviewed. [Focused lock design](claude-review/STOP-LOCK-ORDER-DESIGN.txt)
supports this standalone prerequisite. Application launch is not feature proof.

Residuals: asynchronous posts after worker exit and the synchronous stopped-check/
enqueue/exit race still strand. Interrupted waits can report failure before work
later executes. A callback or Error can kill the worker without completing waiters.
This patch does not promise liveness under arbitrary request clone implementations,
callbacks, external subclasses or unqualified native GUI behavior. Firmware GUI
preflight binding, response schema/status, hardware acceptance, physical Intel,
signing/notarization and release remain open. Legacy HTTP is plaintext.

[Claude implementation review](claude-review/STOP-LOCK-ORDER-CODE-REVIEW.txt) found
no Phase B blocker. Its refinements are implemented: the both-restored control
now uses the exact audit.18 Manager class (in the otherwise current candidate JAR),
monitor ownership is asserted for both threads, and the classpath proof is based
on the actual single-JAR launcher rather than vendor extension inventory. Clean
qualification remains pending; development results are not release acceptance.
