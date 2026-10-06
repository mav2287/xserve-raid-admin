# Remaining worker and synchronous-session safety findings

This source audit follows the clean audit.15 no-replay qualification. It changes
no application bytes. It is not controller or GUI qualification.

Facts below refer to the immutable original JAR, its selected complete method
bodies in [bytecode](next-session-safety-selected-bytecode.txt) and
[class/reference identities](next-session-safety-source-identities.json).
The preserved audit.15 run method is independently pinned by its fixture and
clean artifact. [Claude design](claude-review/NEXT-SESSION-SAFETY-DESIGN.txt) and
[refinement](claude-review/WORKER-FAILURE-STOP-REFINEMENT.txt) are actual CLI reviews;
corrections to initial review inferences are recorded here.

- Fact: prefix IOException gives -103; MalformedInputException and generic
  Exception give -102. These paths retain session connectivity and continue queue dispatch. A queued
  write can reach the wire when the connection is reusable; an outstanding
  response can instead make the next request fail before writing. Audit.15 removes automatic resend for other I/O failures only.
- Fact: SyncSender queues before waiting. Its interrupted wait fabricates -102
  but leaves the transaction active. Synchronous posting from a callback queues
  before throwing IllegalStateException. Both can leave work executable after
  the caller reports failure. Runtime/concurrent cancellation qualification is open.
- Fact: the stopped check precedes synchronous enqueue. A worker exit between
  check and enqueue can strand the synchronous waiter. Late async posts are not
  checked for stop. Queue/exit atomicity and callback-throw cleanup remain open.
- Fact: run takes queue then manager locks; shutdown/exit take manager then queue.
  The opposite order creates an existing deadlock risk. RaidSystem.disconnect
  invokes agent shutdown then manager shutdown from its caller thread.
- Fact: SyncSender accepts TYPE_CONNECT replies without distinguishing operation
  completion. doConnect can report -101 and keep trying, then send the held request
  after connecting. The failed-call/later-send consequence follows source control
  flow; real reconnect timing is unqualified.

The poll-refresh inference in the initial Claude design was too broad.
updateImmediately interrupts only when polling is enabled **and sleeping**.
The run method marks sleeping only after synchronous updates and clears it in a
finally block after sleep. This does not prove routine refresh interrupts an
active synchronous request. An interrupt arriving after sleep returns but before
sleeping is cleared may remain pending into a later wait; external interrupts
also remain possible. That race is an inference, not a measured controller event.

The manager getter returns the existing field. Within RaidSystem the String constructor is the
only direct field assignment; a jar-wide Fieldref scan finds comms references only
in RaidSystem, whose field is private; the copy constructor does not initialize a manager.
The agent retains its own manager reference. No automatic stopped-manager
replacement occurs in these methods. Complete GUI
recovery and other reflective/state-replacement paths are unresolved.

AcpxConnection.close calls HttpConnection.close/disconnect, which closes the
Socket; neither invokes the request OutputStream.close/send. Its send finally
closes the response input and may disconnect, but does not close the request
output. Worker-side retirement therefore adds no application writes. Bytes already
written may still drain from kernel buffers; close cannot undo a controller action.

The selected classes use major version 47 and no run StackMapTable. A jar-wide
constant-pool scan finds the shim class reference only in Manager, whose
run catch table uses it. This is
not a proof about reflection or runtime libraries. The compatibility shim is
CharacterCodingException-derived and its String constructor discards the message.
Modern-runtime shim production throw sites remain unestablished.

The proposed next milestone stops on worker failures before logs/callbacks while
preserving original result codes, exception objects and successful commands.
Generic failure can include a throwing connection callback or null connection
before transmission; this is a deliberate availability restriction, not solely
ambiguous response handling. The next synchronous post must reject without enqueue;
the same faulted synchronous call still wraps its exception as plain IOException.
Null-handler queued requests receive no callback. Logger and shutdown failures,
interrupted waits, enqueue/exit races, GUI recovery and controller behavior require
separate evidence. No caller-thread shutdown or interrupt policy is changed here.

The Claude reviews cite on-session ignored build dumps and their original line
numbers. Complete relevant method bodies and class identities are archived in the
linked files; those reviewed source facts can be checked from the commit.

The characterization clears requestOutstanding before its scripted response faults
to model a reusable connection. It is not evidence that every real failure leaves
a reusable connection. The zero-first-send proxy fault occurs in getPath before
request creation; it is not a real serializer throw site. Initial development
records are dirty and excluded from clean qualification. After audit.16 every
IOException path is terminal; healthy negative controller replies remain a
continuation control. A throw from the original prefix logger at PC374 can still
kill the already-stopped worker before callbacks and strand waiters.
