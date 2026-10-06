Stop versus active send: source intake, not qualification

Fact (audit.21 Manager bytecode): public synchronized shutdown writes volatile
stopped=true, then notifies the queue while holding Manager followed by queue.
It does not close the current connection, wait for a command, or revoke a claim.
The dispatch loop calls synchronized isStopped at235, releases that monitor,
performs SyncSender claim at606 and records exposure at646, then calls send255.
No stop check or shared admission lock spans the claim and send call. A stop can
therefore race between the read, claim, serialization and write. Source presence
alone does not measure which race windows occur on real transport.

The existing original retry range380..459 is unreachable in the candidate,
verified by complete dispatch control flow. An already claimed command remains
unconfirmed if the worker fails, never reported as safely unsent. Synchronous
caller interruption after claim does not cancel or replay the command.

Proposed next safe characterization: actual Manager and SyncSender with the
reviewed memory connection shadow, a synthetic request whose writeTo pauses
before completing serialization, and an external shutdown after claim. Positively prove
claim and caller wait, stopped flag, exposure identity and serialization pause, final exact
command bytes/outcome and zero replay. Test both pinned JVMs, interpreted/compiled;
no controller, profiles, mounted volumes, firmware file or original Main. This
characterizes local software ordering only, never controller receipt timing.

Implementation decision remains unresolved. Holding Manager across blocking
network writes would change shutdown/UI liveness and is not a safe default.
Closing a socket during a write cannot prove the controller did not receive or
apply the command. Define and test a precise claim/admission boundary, preserve
honest uncertain-outcome reporting, and obtain Claude review before changing it.
A complete secure transport policy still needs explicit connect, write and whole
operation deadline evidence. Existing per-read timeout is not an overall limit.

Claude reviewed the memory characterization and proposed a final direct volatile
stopped read after successful claim, before workerActiveStarted and send. Both
synchronous and asynchronous dispatch reach this seam. A stop observed there
would use the original shutdown response path; after that last read an admitted
operation retains its real outcome or unconfirmed failure. This narrows admission
and does not make stop atomic with TCP writes or prove cancellation after admission.
No Manager lock may be held across network writes.

Correction to Claude's recommendation: routing to the original stopped branch
keeps its callbacks on the worker, not the EDT. Only terminal helper cleanup uses
the EDT. The memory shadow records its request/body after writeTo returns, so
empty recorded lists while parked cannot prove zero network/header bytes. The
refined characterization explicitly asserts active transaction/handler identity,
workerActiveStarted and independent serialization assertions, and labels the
window as before serialization completion. Async and pre-admission race fixtures
remain required before implementing/promoting this change.
