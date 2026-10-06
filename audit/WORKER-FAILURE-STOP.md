# Audit.16 worker-failure session stop

Status: development only; clean qualification pending. The original JAR and the
installed app are unchanged. This follows the clean audit.15 no-replay fix and
closes additional worker-failure continuation paths, not every session-safety issue.

## Behavior and deliberate availability restriction

Facts: audit.15 still continued after prefix parsing -103, typed
MalformedInputException -102, and non-marker generic Exception -102. Dependent
queued writes could be dispatched when the connection remained reusable.
The source and scripted differential are described in
[source findings](NEXT-SESSION-SAFETY-FINDINGS.md).

Audit.16 stops the local manager before logging/callbacks for these worker faults
and retires the connection. It preserves their original result codes and exception
objects, including the original prefix log. This includes generic failures before
transmission: null connection and a throwing -101 connection callback. A successful
reply carrying a negative controller result code remains a successful transport
reply and permits the next request. No controller shutdown command is sent.

This is a permanent stop for that RaidSystem instance. The getter does not recreate
its manager, and the polling agent retains its own reference. Complete GUI recovery
is unresolved. A healthy controller that triggers the legacy -103 path now loses
its session; this is the accepted security cost. An error never proves a mutation
was not applied. Retirement adds no application writes; bytes already written may
still drain from kernel buffers and an applied controller action cannot be undone.

Queued requests with a non-null handler receive the original stopped-session
-102 CommShutdownException. Null-handler requests are discarded with no callback.
The same synchronous call that failed still produces the original plain IOException
wrapper; the next synchronous post rejects before enqueueing. This does not fix
interrupted waits, failed-connect replies followed by later transmission, the
post/exit race, or the original manager/queue lock-order deadlock.

## Narrow implementation

- Keep all successful-command bytes and timers unchanged.
- Change only the typed handler target 307 to 462, preserving its position, type,
  start/end offsets and original -102 exception instance.
- Change PC 573 from goto_w 344 to goto_w 578. Append a 17-byte tail that repeats the
  original prefix test, sends non-prefix I/O to the existing fixed marker block,
  and retires a prefix failure before the original -103 response/log instructions.
- Code length is 595, stack 6/locals 9, class major 47; no run StackMapTable. New dead
  regions are 307–336 and 344–351, in addition to the retained 380–458 retry region.
- The helper's report stops before logging, contains logger failures and retires.
  Prefix retirement does not itself call the Manager error logger; the original
  prefix logger remains at 374. The transport may log a socket-close debug event.
- shutdownRequired permits only the exact manager class. A shutdown failure throws
  a fresh fixed causeless IllegalStateException rather than returning into dispatch.
  That can kill the worker and strand callbacks; it prevents further worker sends
  and does not establish liveness or successful retirement after a failed stop.

Only Manager.run and RejectionRecovery differ from audit.15 JAR entries.
SyncSender, postMessage*, shutdown, exit, doConnect, AcpxConnection, request factory
and caller workflows remain unchanged. The independent gate pins binary edits,
handler change, exact helper stop/log ordering, required-stop rethrows and the CFG's
complete reachable/unreachable sets.

## Tests and scoped evidence

[Actual design](claude-review/NEXT-SESSION-SAFETY-DESIGN.txt) and
[refinement](claude-review/WORKER-FAILURE-STOP-REFINEMENT.txt) approved worker-only
retirement. [Characterization review](claude-review/WORKER-FAILURE-CHARACTERIZATION-REVIEW.txt)
required complete cited method bodies, field-reference evidence, precise memory
seams, literal golden vectors and clean proof. Those source/fixture changes are
combined with this patch; dirty audit.15 characterization is not promoted as clean.

The memory fixture asserts original exception identity for prefix, shim and generic
faults and a proxy getPath fault before request creation. For three response seams
it explicitly clears requestOutstanding to model a reusable connection; it is not
proof that every actual failure has that state. The proxy fault is not a serializer
throw site. Candidate callbacks see stop/disconnection, exactly one retirement
close, blocked queued restart, and rejection of a callback's next synchronous post
without enqueue. Original continuation counts and actual serialized restart bodies
are compared. No header values or request bodies are emitted.

Additional cases cover null connection and throwing -101 callback with zero
request attempts, a null-handler queued restart with no extra callback or send,
a healthy -27 result followed by another successful request, and a faulted
synchronous call's wrapper followed by a stopped next post and bounded worker exit.
Both interpreted/compiled execution and full verification are required on arm64
and x64. Verifier-valid mutations bypass prefix retirement, omit report stop,
restore the typed handler, or restore the original tail; each must observe the
specific unstopped callback state and fail the sequencing fixture. Mutant helper
source is compiled with the pinned compiler, and the unmodified source must first
compile to the exact candidate helper bytes.

The retained 143-line security-marker matrix changes only its first ordinary-fault
logger/session line. Logger owner/method stay Manager.run. The full parser, header,
allocation, resources, shared-stream and 116-row body/metadata factory regressions
remain required; no application launch is feature evidence.

Unresolved: prefix logger throws can kill an already-stopped worker before its
callback; callback errors and message-getter failures can kill other workers;
interrupted synchronous transactions, TYPE_CONNECT completion semantics, queue
exit/late-post atomicity and lock-order liveness; whole agent/GUI recovery; real
socket timing and controller operations; HTTP status and response association;
firmware preflight/transmission binding; physical Intel and release signing.
Legacy HTTP is plaintext. No production/mounted-volume test, controller contact,
firmware transmission or installed-app modification is performed.

The jar-wide superclass scan finds no Manager subclass among all 2844 original
classes. Unsupported subclasses or failed shutdown cause worker death without
exit cleanup and can strand waiters; that path is statically checked, not runtime
qualified. The whole RaidSystemAgent termination sequence remains unmeasured.
All four verifier-valid worker-stop mutants, including restored handler and tail
bytecode, are now exercised rather than inferred from helper mutations. Historical
audit.14/15 helper-prefix fixtures are explicitly labeled historical; current
helper gates and snapshots are separate.

[Implementation review](claude-review/WORKER-FAILURE-STOP-IMPLEMENTATION.txt)
and [follow-up review](claude-review/WORKER-FAILURE-STOP-FOLLOWUP.txt) found no
blocker to committing the combined source audit and patch. Their requested
handler, helper, subclass-scan, mutation and historical-fixture checks are
implemented. The recorded subclass scan is static evidence, not regenerated by
the runtime gates. Clean qualification will independently pin committed inputs.
