# Stopped-post admission — audit.20 candidate

Status: clean fixture qualification complete at source/fixture/package commit
`b600ad3` after actual Claude code and evidence reviews. Audit.20 is the current
qualified local compatibility candidate; native GUI, hardware and release
acceptance remain open.
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
The qualified candidate JAR is
`f6e545bbd90e7f9616df448f09cc4a889b909fa8e79a8183af8fa96a71d9f859`.
Only that Manager and the two new helper entries differ from audit.19; the
manifest, SyncSender constructor, worker run, connection routine and existing
helper entries are unchanged. Local fixture qualification is not full application or release acceptance.

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
that removes logging containment and positively observes exactly two
appender exception identities escaping on the EDT. The clean run passed. Historical
connection extras retain their late_async_stranded=1 line because that fixture
artificially records its own calling thread as the worker even after run exits.
That is the preserved worker exemption, not evidence that an external late post
in the audit.20 candidate strands. The dedicated admission fixture records a
different worker thread and observes the external refusal.

A dirty development expanded-gate attempt was invalidated when its locked source
metadata changed during review refinements. The source guard rejected it (dev-admission-3); its
results are excluded. A separate dirty dev-admission-4 run then passed all 40
checks before the clean run. Neither development run is acceptance evidence. Clean qualification must use one unchanged source commit.


## Clean qualification and archive

[Eleven gates](stopped-post-run-results.json) passed with actual outer exit code
zero and empty parent stderr from unchanged clean `b600ad3`. The gate records
are [security](stopped-post-clean-security.json),
[transport](stopped-post-clean-transport.json), [runtime](stopped-post-clean-runtime.json),
[resources](stopped-post-clean-resources.json), [shared stream](stopped-post-clean-shared.json),
[factory](stopped-post-clean-factory.json), [synchronous posting](stopped-post-clean-posting.json),
[connection stop](stopped-post-clean-connect.json),
[historical characterization](stopped-post-clean-characterization.json),
[stop lock ordering](stopped-post-clean-lock.json), and
[stopped admission](stopped-post-clean-admission.json).
The historical characterization artifact remains audit.17 at `47166ed`, with
current `b600ad3` fixtures; it is not the audit.20 application.

[124 Python tests](stopped-post-clean-tests.json) passed. Their non-empty stderr
is the normal unittest progress/summary, not an empty-stderr claim. Runtime
records contain 143 recovery lines for each freshly identified runtime Home
digest; factory records contain four original/candidate × arm64/x64 pairs of
116 rows. Ten synchronous posting observations, 42 connection observations
(36 positives and six controls), and 20 lock observations (eight positives,
ten exact deadlocks and two site-attribution cross-controls) pass. Admission
records contain 32 candidate positives, four restored-Manager controls, two
missing-helper controls and two logging-containment controls. Every candidate
admission row is tied to the current JAR and Manager hashes and the complete
mode/architecture/execution combination set. JVM stderr is explicitly empty
for every admission observation; Claude's earlier stderr caution is resolved.

[Duplicate packages](stopped-post-bundle-results.json) match application files,
file modes, directory modes and verified vendor signatures on each architecture.
Their metadata differs only in source_provenance_sha256: package 1 comes from
clean-3 and package 2 from clean-4, whose separate source provenance contains
its own timestamp. Both hashes are independently bound to those source files;
entire metadata JSON is not claimed byte-identical. Arm64 and x64
[diagnostics](stopped-post-diagnostics-aarch64.json)
[records](stopped-post-diagnostics-x64.json) pass their source/architecture/tree
and reviewed-artifact assertions. An initial package orchestration attempt per
architecture selected an unpinned Python through the isolated PATH and was
rejected before copying. Selecting sys.executable corrected orchestration with
no source change; those failed attempts are excluded.

[Final integrity](stopped-post-final-integrity.json), SHA-256 `dfb3a801123c95e459e3c0f7f05ae5fbda2e0acb46ec49454de9bf355f5ab87f`,
records exact gate/archive hashes and verifies reported source hashes against
committed bytes. The source-hash-entry count includes repeated files across
records; it is not a unique-file count. Bundle/run summaries are ledger outputs,
not additional behavior tests. Fresh runtime file-only, Home-only and
files-plus-modes digests use explicit scope definitions. The installed app's
content map is pinned independently to tracked intake digest `192c2d06…`;
its modes match the preserved external copy, whose original modes were not
separately hash-pinned in intake. Original JAR mode 444 is retained. No-controller,
no-production-volume and no-installed-modification statements are action-scope
attestations from the reviewed fixture/orchestration and OfflineGuard results,
not a global packet capture. Interpreter metadata is freshly measured at final
ledger verification; the path was not captured at each gate's start. Each
qualification entrypoint enforces the pinned Python version.

The archived [ledger generator](source/stopped-post/finalize-evidence.py) was
executed before archival from the clean qualification commit; it requires that
source state and local build outputs. [Claude code review](claude-review/STOPPED-POST-CODE-REVIEW.txt),
[boundary follow-up](claude-review/STOPPED-POST-BOUNDARY-FOLLOWUP.txt),
[clean review](claude-review/STOPPED-POST-CLEAN-EVIDENCE.txt) and
[evidence follow-up](claude-review/STOPPED-POST-CLEAN-FOLLOWUP.txt) distinguish
record comparisons from machine-executed hash checks. The latter's evidence
refinements are incorporated above and in the generator/ledger. These archive
updates change no qualification input. The historical audit.19 stdout mismatch
remains unexplained; audit.20 does not claim to have diagnosed or fixed its cause.
