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
