Worker-exit followup design (not implemented)

Keep ownership experiment outside baseline until terminal completion is proven. Baseline remains audit.20. Current ownership Manager revised Code623, all four original-window handlers copied; earlier617 references superseded.

Prefer Claude's direct bytecode wrapper: private dispatchLoop()V plus public run()V invoking it via invokespecial, catch any; helper exit(manager, queue, active, activeStarted, cause). No reflection invocation of original loop. Add private Object active and boolean activeStarted. Track active under original queue lock immediately after removeFirst before lock release; reset activeStarted=false at same seam. Track sent/claimed exposure conservatively by setting activeStarted=true at successful ownership check/nonSync path, immediately before preserved original getter and send; no replay, no deadline change. Active before claim is unsent shutdown, not unconfirmed. Claimed/sending active is unconfirmed, never fabricate successful controller outcome.

Clear active BEFORE every terminal callback, including run callback PC509 (all outcome paths489) AND doConnect failed callback sites409 and586. Do not redeliver to a handler whose invocation already began even if it throws. This also prevents two async callback attempts on thrown initial connect-error publication. DoConnect's only handleResponse sites are409/586; source checker verifies all. Clear active on cancelled skip/no-handler outcome at489. activeStarted stale when active=null ignored.

Wrapper/helper on normal loop return also sets local stopped=true, connected=false so worker InterruptedException exit cannot admit later posts. Existing shutdown order manager->queue retained; helper takes individual locks with no nesting. On abnormal worker exit, retired state BEFORE queue snapshot/callback/close. Exact-shape metadata transaction getters resolved before dispatch; metadata failure must fail closed before any command (not continue normal dispatch with inability to complete requests). Bytecode links field values directly to helper; reflection only private Transaction getters/class identity. Do not make raw throwable a response or log it.

Synchronously complete exact original SyncSenders first (first-reply guard rejects duplicate), active first then queued. All terminal async callbacks in this exceptional exit path are deferred to EDT using dedicated callback with fixed signal/no cause. Do not invoke fatal-cleanup async callbacks on the worker thread: the existing audit20 worker admission exemption allows reentrant queued posts, and a drain cap would strand newly posted sync requests. EDT causes those posts to take normal stopped refusal; no fresh queue growth on dead worker. Normal healthy callbacks and normal original stopped queue drain are unchanged. Exceptional exit callback order/thread is explicit security behavior change; EDT scheduling failures/disposed AppContext remain visible availability limitation, not guaranteed arbitrary GUI delivery.

Connection close last after synchronous callers completed. Source AcpxConnection.close simply HttpConnection.close -> Socket.close, clears fields; no firmware/commands/cache etc. No transport output flush. Socket close is not assumed whole-op deadline or universally bounded. Original epilogue normal close may block before wrapper helper starts; transport deadline/quit-bound gap remains explicit. Abnormal helper close not before sync completion. Original18/19 recovery paths can close earlier and remain separate unbounded-gap.

Helper failure/callback policy needs careful review: contain Exception/LinkageError and ordinary non-VM Error with fixed nonrendering signal on fatal cleanup path; never re-invoke a callback already invoked. ThreadDeath silent rethrow after best-effort cleanup; VirtualMachineError no terminal-completion guarantee. No arbitrary exception stack/strings at new boundary. Allocation failure and monitor/thread teardown cannot be promised safe under OOM.

Blockers/tests: prove retry CFG380..459 dead with new wrapper normalization, class-hash roundtrip includes rename/access/new field/new method/exact tails/exception tables; no dropped dequeued txn; all send/connect/log/callback/queue-interrupt exit sites; postrace; first reply; normal command/callback parity; both architectures -Xint/-Xcomp. Build/qualification scripts updated after local code review, not now.

Source-based refinements after Claude followup:
- Pin doConnect clear seam immediately before callback dispatch. Both original invokeinterface instructions (409 and586, five bytes each) can redirect to an appended clear-and-call trampoline that preserves the already stacked handler/system/response/context, clears active just before actual invokeinterface, reexecutes original callback and jumps to414/591. Earlier retire/log failure retains active; no early clear at718/740. Tail handler coverage must replicate all original covering handlers (409 has none;586 has none in doConnect).
- Resolve Transaction getters and SyncSender identity in Manager constructor BEFORE original Thread.start at60. Constructor seam35..41 original aload0/newThread/dup can be displaced to a tail calling static WorkerExit.prepare then restoring those instructions; verifier/preservation checks mandatory. Failure throws a fixed no-cause startup exception before thread creation/start, so ordinary production Manager cannot admit pre-start posts. Unsafe fixtures must explicitly prepare; wrapper can check cached readiness but never continue dispatch with invalid metadata.
- All helper drains, including normal InterruptedException returns, defer async terminal callbacks to EDT. Original healthy dispatch and stopped-worker drain unchanged. New helper is a single ordered runnable with per-handler containment; synchronous completions finish before scheduling. No callbacks run on dead worker, so audit20 worker exemption cannot enqueue behind the cleanup snapshot.
- Stop must not depend on possibly throwing shutdown(). Public run wrapper writes private volatile stopped=true directly before calling helper. The helper then updates connected=false under Manager lock, and takes/releases queue lock while snapshotting/clearing; this supplies original shutdown queue admission barrier without invoking shutdown or nesting locks. Ordinary worker already stopped and empty queue remains no-op cleanup. Reflective metadata failure can never prevent stopped write.

Additional unresolved callback path:
Clearing active at doConnect callbacks prevents wrapper redelivery for an Error, but a RuntimeException from those callbacks is caught by the original run [215,304)->462 Exception handler. That path creates another BasicResponse at474 and calls the same handler at509 even though active was cleared. Proposed narrow guard: redirect original PC474..479 (new BasicResponse/dup/iconst2, five bytes) to an appended tail which checks workerActiveTxn == null. If cleared, jump489 with existing local4=null; otherwise replay original five bytes and jump479. RejectionRecovery.report at467 still stops and logs fixed-redacted signal; no command replay or second callback. This guard applies only to a already-begun doConnect terminal callback (the only pre-474 clear path); independent checker must prove that invariant. Alternative callback shim to convert thrown callback into dedicated non-Exception sentinel Error is more invasive to throwable semantics and class inventory. This is not coded; needs Claude/source/fixture review.


Latest correction (supersedes the earlier constructor35 seam and guard474 proposal):
Use constructor30..35, restoring only the system field assignment and resuming35;
never carry uninitialized Thread objects over a backward branch. Route actual run
callback509 through a test-and-clear trampoline, suppressing already-attempted
doConnect callbacks for every failure path including sneaky prefix IOException.
Route514..519 through clear-active plus original connectionFailureSent reset for
all no-callback/cancelled paths. The original context getter may still run before
the skip; it is a pinned simple field getter. No guard around new/dup is needed.
DoConnect409/586 clear immediately before original invocation; each original
five-byte invokeinterface seam is preserved in its tail. All helper drains defer
async responses via invokeLater; sync completions precede manager-lock cleanup.
Fields active/activeStarted are worker-only. Constructor metadata initialization
must be checked against original RaidSystem construction/publication paths before
integration; fixture readiness caching needs safe synchronized/volatile publication.
No code for this combined worker-exit design is integrated yet.


Startup source intake underway: complete original RaidSystem constructor methods,
Transaction class and ten relevant child/registry/action constructor methods have
been extracted into local ignored build source records with original-class and
bytecode hashes. No constructor or profile loader was executed. Original registry
and add-system callers need fail-closed propagation review before a constructor
hook is accepted; no assertion about that behavior is made here yet.


2026-10-06 implementation update (supersedes design-only statements above):
The combined guard is integrated in development audit.21. Actual constructor seam
30..35 invokes prepare before Thread creation. Metadata reads exact private/package
Transaction fields, not getters. The wrapper directly invokes private dispatchLoop,
sets volatile stopped before cleanup, and clears active immediately before actual
run and doConnect callbacks. Ordinary exits complete synchronous waiters before
acquiring the Manager monitor, then defer asynchronous terminal responses to EDT.
The abnormal close is in finally, including entry-preparation failures. Whole-class
reverse reconstruction and an independent javap check pass. Both build copies have
identical bytes/modes; 133 unit tests passed in development. Runtime gates are pending;
audit.20 remains the last fully qualified baseline.

Startup source facts: NetworkInterface(int,SystemController) initializes only local
fields and obtains its controller ID; RaidSystem.addFan performs only a local map
insert. Earlier extracted SystemController/RaidController/Fan/base constructors
establish child/back references. The inspected construction path contains no global
registry publication before Manager creation. DefaultSystemRegistry constructs
RaidSystem before applying loaded credentials, connecting, and adding it. Failure
at the new prepare hook propagates and can abort the remaining registry load.
AddSystemAction constructs before registry add/connect but increments systemsAdded
before construction. A prepare failure can therefore affect that UI counter. These
are bytecode findings, not native GUI or profile-loader runtime qualification; no
profiles, saved credentials, registry constructors or original Main were executed.

Claude correction: the CODE-FOLLOWUP review's statement that an interrupt during
all doConnect paths necessarily reaches run PC525 with activeStarted=true is not
established. doConnect has its own InterruptedException handler, and an Exception
from a connect callback can be intercepted by the run generic handler. Before the
claim/exposure seam activeStarted is false. Only the actual tracked value governs
unsent versus unconfirmed classification; the mistaken review inference is not
accepted evidence. The actual callback509 guard suppresses second attempts after
doConnect409/586 for runtime, prefix/plain/null IOException, shim malformed and
ordinary Error paths in the memory fixture. New clean qualification remains pending.

Limit: virtual-machine exhaustion, ThreadDeath, metadata/allocation failures,
blocked close/read/write, disposed AppContext, native GUI behavior and production
transport are not terminal-completion guarantees. The normal original epilogue may
block before helper cleanup starts. stop-versus-active-send is still open.


Claude integrated review found and required a further security boundary: connect
callback exceptions must not enter original transport classifiers, which call
getMessage and pass throwable payloads to logging. Both original doConnect
callback tails now invoke WorkerExit.connectCallback with the original four
stack arguments (same worker, response and context), catch non-ThreadDeath
throwables, and emit only the fixed signal. ThreadDeath escapes to the terminal
wrapper without rendering. This supersedes the earlier direct connect callback
invocations and reliance on the application log appender. The original ordinary
command callback remains direct and is guarded against repeat delivery.

Latest bytecode: Manager pool433, run wrapper58, dispatchLoop709, doConnect784,
constructor77; exact predecessor reconstruction still required. Current Manager
SHA bc6ff5078249e584dd81f102799b0c10870d8e37b194b48c3e39dd722c45eda6.
Independent complete dispatch CFG proves no reachable legacy requeue and only the
three added dead padding offsets68,246,617. Fixture changes include positive WARN
observers, hostile callback IOException getMessage/toString traps, sneaky callback
interrupt, actual sender wait-lock identity, and mixed async/sync exit drain where
a queued caller holds the Manager monitor. New clean evidence remains pending.

Prior reported-connect continuation negative control now restores the exact
reviewed audit.20 Manager and Sender before bypassing the reported-stop window.
Restoring that window alone on audit.21 no longer sends: the ownership/first-reply
guard independently cancels the completed Sender. No-host and late-stop controls
retain current worker edits and remain positive unsafe stop-order observations.


Claude boundary followup verifies callback argument/stack/pool preservation and
requires the positive WARN fixture to account for the original no-host ERROR
message. The fixture now accepts exactly that known synthetic message without a
Throwable (one in nohost, zero in single), plus exactly one fixed failure signal.
This is not permission to render arbitrary payloads. Followup limitations are
recorded with corrections: the cited legacy reconnect/requeue range is proven
unreachable by the expanded CFG; it is not a reachable audit.21 duplicate path.
Every run_jdk invocation already clears java.ext.dirs and endorsed.dirs; the
architecture gate's explicit vendor-extension mode includes only the pinned
runtime vendor directory, never ambient /Library/Java/Extensions.

A batch caller must acquire the Manager lock after the active send has begun;
holding it before dispatch blocks the original synchronized isConnected getter.
The corrected fixture positively observes active onSend, then queues the caller
holding Manager, observes its wait, and releases the synthetic send fault. It
proves synchronous release before cleanup takes Manager; the earlier fixture
setup failed and is excluded. Async EDT checks plus source show helper callbacks
hold neither lock; Thread.holdsLock on EDT alone is not cross-thread lock proof.
Native GUI/runtime-exhaustion guarantees remain excluded. Constructor preparation
placement is locked independently by bytecode; runtime constructor success alone
would not distinguish its prepare call from ensurePrepared in run.
