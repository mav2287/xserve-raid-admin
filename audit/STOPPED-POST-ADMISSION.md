# Stopped-post admission — audit.20 candidate

Status: initial development tests and actual Claude implementation/follow-up
reviews passed; final strict-stderr development gate and clean full qualification
are pending. The previously qualified artifact remains audit.19.
This document does not declare the application fully operational or secure.

## Facts and exact changes

The original three-argument `CommunicationsManager.postMessageAsync` clones and
queues even after shutdown. The original worker exits when its queue is empty
and stopped. A later external asynchronous post therefore has no worker to
respond, and a synchronous caller racing its earlier `isStopped` check can wait
forever on its newly queued sender. The tests positively observe that residual
queue and waiting, unhandled sender using the exact audit.19 Manager restored in
the otherwise candidate JAR. Timeout or verifier failure never counts as proof.

The candidate keeps the original request clone and Transaction construction
before checking admission under the original queue monitor. `stopped` is read
directly as the audit.19 volatile field: calling synchronized `isStopped` while
holding the queue would reintroduce the removed lock inversion. Healthy posts
and posts from the recorded worker continue through original add/notify/release.
For other stopped posts, the new Transaction is discarded, the monitor released,
and a thin compatibility helper supplies the original command response shape:
`BasicResponse(TYPE_COMMAND, null, IO_ERR=-102, new CommShutdownException())`.
No connection, firmware, controller command, polling interval or retry parameter
is changed by this milestone. The original JAR remains immutable.

The Code grows 56 to 98 bytes with unchanged stack=6, locals=6, major version 47.
At PC30, original add/pop is replaced by goto56 and an unreachable nop. Both
locked paths are covered by the additional catch-all [56,84) ->47. The refused
helper call starts outside the monitor at PC84. Original handlers, clone,
notification and monitor cleanup are unchanged. Ten appended pool entries
395..404 supply Thread.currentThread and the helper reference. Removing exactly
that pool tail and restoring the original post Code reconstructs the complete
measured audit.19 Manager `cfefcc5b8cb0b0c15b5f63788503c8e41414b01abe2dbcedcc95cdebca8ecc24`.
The existing further audit.18 and audit.17 reconstruction checks also run.
An independent javap gate checks every appended instruction, constant reference,
monitor range and unchanged original instruction/metadata; byte mutations and
unrelated-method changes must fail.

The candidate Manager is
`ddd62642900262d6c99b14777c79ddd22a54b97ef506e7984daff46b3bb7bbfd`.
The candidate JAR is
`f6e545bbd90e7f9616df448f09cc4a889b909fa8e79a8183af8fa96a71d9f859`.
Only that Manager and the two new helper entries differ from audit.19; the
manifest, SyncSender constructor, worker run, connection routine and existing
helper entries are unchanged. Development artifacts are not qualified releases.

## Deliberate behavior differences and limits

- An exact original SyncSender, classified by the existing bytecode class
  reference, receives its refusal on the poster before constructor wait. Its
  existing handled-before-wait check preserves the notification. Public sync
  posting rethrows CommShutdownException, matching its earlier stopped precheck.
- Other nonnull refused handlers are posted to the Swing EDT, preserving absence
  of inline application callback execution and avoiding new caller-lock cycles.
  This is a deliberate callback-thread change for locally refused posts.
  Original handlers can now show an error or update model state after stop
  where the old stranded post provided no callback.
  An EDT poster's event runs after the current dispatch returns; a non-EDT
  poster's event may execute before postMessageAsync returns. These events can
  precede earlier queued worker callbacks. No global FIFO guarantee is added.
- Null handlers require no event and do not start the EDT in the isolated test.
  Worker posts remain queued and drained on that worker, with the original
  callback behavior. Infinite worker callback repost loops remain possible, as before. An external
  handler that reposts on -102 can now create an ongoing sequence of deferred
  EDT events, where the old stopped queue stayed silent. The inventoried original
  handlers have no direct -102 repost path; arbitrary handler extensions and
  native UI reachability remain unqualified.
- Exceptions and LinkageError from refused asynchronous handlers are caught and
  signaled using a constant logging message, with no Throwable, cause, context,
  user input or exception rendering. Logging failure is contained. The production
  SafeLogAppender emits only its existing one-time RAID_ADMIN_ERROR signal; it
  does not print the internal STOPPED_CALLBACK_FAILED literal. Fatal errors and
  ThreadDeath and other non-Linkage Errors are not swallowed.
- Helper linkage and event-scheduling errors propagate to the poster outside the
  queue monitor. A disposed AppContext can silently drop queued Swing events.
  Native GUI/model ordering and arbitrary third-party callbacks are unqualified.
- An abnormal worker exit leaving stopped=false, an interrupted synchronous
  wait's orphaned transaction, and shutdown racing an already held/sendable
  transaction remain separate open gaps. Active network operations are not
  bounded by this fix; see [timeout correction](TRANSPORT-TIMEOUTS.md).

## Evidence and development exclusions

Actual Claude's design review found wrong proposed handler-local indices and a
proposed layout lacking cleanup around add. Both were corrected before the
implemented layout. The first development bytecode used pop instead of pop2;
it was corrected before the current candidate identity and independent gate.
These initial drafts are excluded from qualification. A first admission-gate
run rejected an incorrect fixture-class allowlist; it was fixed to match the
then-measured three anonymous fixture classes (the added boundary case
now brings the exact allowlist to four). A regression run exposed missing or
wrong worker identity in constructor-free fixtures. Fixtures now assign the
actual running worker; the application constructor and worker identity are
unchanged. Failed or dirty development runs are not clean acceptance evidence.

The earlier development admission run covers 34 observations on the pinned
arm64 runtime and x64 runtime under Rosetta, with interpreted and compiled
execution and full JVM verification. It includes stopped/exited async posts,
synchronous precheck races, worker repost/drain identity, 32 concurrent contexts,
EDT deferred delivery, null/clone failure, hostile exception rendering, restored
Manager controls and missing-helper propagation/monitor release. Original
Manager/thread creation is bypassed and no production connection exists.
No Main/native window, saved profiles, controller, production or mounted volume
was tested. Real Intel hardware remains unqualified.

Subsequent Claude refinements require no EDT for a synchronous refusal, an EDT
barrier after concurrent posters, and a boundary case verifying contained logging
failure/handler LinkageError and an actual EDT uncaught non-Linkage Error. The
uncaught handler is installed before all cases and separately records unexpected
escapes so a later expected Error cannot overwrite a failure. Each observation
requires empty JVM stderr without exposing unexpected diagnostics. The
expanded gate expects 40 observations, including a compiled helper mutant
that removes logging containment and must positively observe exactly two
appender exception identities escaping on the EDT; its results are pending. Historical
connection extras retain their late_async_stranded=1 line because that fixture
artificially records its own calling thread as the worker even after run exits.
That is the preserved worker exemption, not evidence that an external late post
in the audit.20 candidate strands. The dedicated admission fixture records a
different worker thread and observes the external refusal.

A dirty development expanded-gate attempt was invalidated when its locked source
metadata changed during review refinements. The source guard rejected it; its
results are excluded. Clean qualification must use one unchanged source commit.
