# Synchronous request ownership experiment

Status: source experiment, **not baseline integration or release acceptance**.
The qualified build remains `1.5.1-modern.audit.20`, JAR
`f6e545bbd90e7f9616df448f09cc4a889b909fa8e79a8183af8fa96a71d9f859`.
The original Apple JAR remains immutable. No installed application modification,
controller contact, native GUI launch, profiles, credentials or mounted-volume
access was needed for these fixtures.

## Source facts

The original interrupted SyncSender wait installs a shutdown response even when
the queued transaction has not been removed or has already begun sending. The
worker does not test that completion before sending. An interrupted wait can
also overwrite a real response already delivered while the caller reacquires
its monitor. Original synchronized `handleResponse` replaces prior responses.

`tools/sync_ownership_patch.py` makes exact, reversible edits to the hash-pinned
audit.20 Manager and SyncSender. Before the original send, a synchronized
claim rejects an already answered or claimed sender. The interrupt handler
checks `handled` before `claimed`: an existing answer wins; a claimed request
keeps waiting for the worker; an unclaimed request retains the original
interrupted shutdown response. A first-response guard prevents later replacement.
Normal command serialization, polling and timeout configuration are unchanged.
The claimed wait consumes interruptions without restoring the interrupt flag.
This deliberately changes cancellation and duplicate-completion semantics.

The Manager retains its original pre-send getter/store at the claim trampoline,
and copies all four original covering exception handlers in their original
priority order. Code length is 623, not the superseded exploratory 617. Sender
constructor length is 159, response method 23, new synchronized claim 23.
Whole-class normalization reproduces both audit.20 predecessor hashes. A separate
javap checker verifies instruction targets, fields, methods, constant pool and
exception coverage independently of the transformer.

## Offline evidence and limits

The memory transport serializes requests into bounded buffers; it never creates a
socket. A synthetic restart request is used only as bytes in that substitute.
The queued control proves the legacy request still executes after the caller
receives an error; the patch skips it and preserves the exact follow-on body.
Other controls positively observe an active caller returning failure before its
reply, interruption overwriting a real reply, and a direct synthetic second callback replacing it.
The patched fixtures prove actual response identity and a single claim.

The initial and conservative revised experiments each passed 32 vectors: four
scenarios, predecessor/candidate controls, interpreted/compiled execution and
ARM/x64 pinned runtimes. x64 is Rosetta, not physical Intel. JVM stderr must be
empty. CodeSource and loaded resource hashes bind Manager, Sender, nested transport
shadow and every compiled fixture class. A capture appender rejects application
WARN/ERROR events without rendering payloads. Exact bodies refer to request
serialization, not HTTP wire framing. The compiler is rechecked after execution. Timeouts, verifier failures and unexpected errors cannot qualify.
These are development records, not clean full-build qualification. Final checked
records will name their exact source commit and hashes.

Fact: doConnect occurs before claim; cancellation does not prevent a connection
attempt or the existing terminal connection-failure behavior. No connection,
write or whole-operation deadline is introduced. Once claimed, a caller can
wait indefinitely; abnormal worker death can strand it. Consequently **this
experiment must not replace the baseline until worker-exit completion is fixed
and the complete build/gate suite qualifies it**. Native GUI, controller replies,
and real interrupt timing remain unqualified.

## Claude consultation

The first broad concrete review returned no findings and does not count as
approval. The narrow bytecode review initially guessed that #47 was the send;
source shows it is a dead-store getter and #65 is the actual send. Conservatively
retaining that window and all covering exception handlers removes the discrepancy.
Claude's followup explicitly corrects its earlier send/offset/coverage claims
and finds no new blocker in the revised edit. See the archived
[initial review](claude-review/SYNC-OWNERSHIP-BYTECODE.txt) and
[correction and followup](claude-review/SYNC-OWNERSHIP-BYTECODE-FOLLOWUP.txt).

Claude identified abnormal worker exits and normal queue-wait interruption as
remaining terminal-completion gaps. The direct bytecode wrapper recommendation
and refined design are recorded in [worker review](claude-review/WORKER-EXIT-TERMINAL-DESIGN.txt)
and [design under review](WORKER-EXIT-DESIGN.md). The [fixture/gate review](claude-review/SYNC-OWNERSHIP-FIXTURE-GATE.txt) found no
blockers and suggested additional interruption/count/class/log checks, now included.
Its suggestion to compare request identity with the input is inappropriate because
original postMessage clones requests; exact serialized bytes are compared instead.

That design is not implemented
or accepted yet. Callback thread/order, preclaim versus unconfirmed outcomes,
metadata failure, and fatal VM behavior require explicit source and fixture proof.

Reproduce the isolated experiment:

```sh
python3 tools/check_sync_ownership.py --jdk /path/to/pinned/compiler/Contents/Home \
  --runtime /path/to/arm/Runtime.jdk --runtime /path/to/x64/Runtime.jdk \
  '/path/to/audit20/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
python3 -m unittest discover -s tests
```

### Final instrumentation refinements

Claude's followup caught that an ERROR root level dropped WARN before capture.
The fixture now uses WARN, positively probes the capture with a fixed synthetic
warning, then resets its counter before application work. The pinned reference
configuration defines only the root logger/appender, and fixture directories
contain only allowlisted classes. Both successful interrupted-return scenarios
assert that interruption was consumed. Both tools pin the identical ownership
JAR `05a6ce59ba13a811a1e46478b1b2477bdf575ae66a14bb700933f8e13422aa38`,
recheck source/working-tree state and the compiler after execution, and record
all imported tool sources. See [followup](claude-review/SYNC-OWNERSHIP-EXPERIMENT-FOLLOWUP.txt).

Worker-exit characterization now separately runs 16 vectors: send-Error and
callback-Error, qualified predecessor/ownership candidate, both runtimes and
both execution modes. It positively observes exact fault identity, actual worker
death, stopped=false, and a caller waiting on its exact sender. Manual fixture
completion after that observation is explicitly not a product fix. An initial
fixture allowlist rejection (private implicit constructor generated a synthetic
access marker) ran no observations and is excluded; explicit package-scope
synthetic-fault constructor removes that unnecessary generated class.

129 Python tests pass, including full byte-mutation rejection and independent
javap negative controls. Clean source replay and archived result hashes follow
in separate evidence records; none of these experiments is release acceptance.

### Clean source-bound evidence

The source anchor is `6d26fbea04eb3f9e56b1ce3113430f26f6c3592f` with a clean tree.
[Ownership replay](ownership-clean-experiment.json) contains all 32 Cartesian
cases; [worker-death characterization](worker-exit-clean-characterization.json)
contains all 16 cases; [Python results](ownership-clean-tests.json) record 129
passing tests. Every recorded tool/fixture input matches that committed source,
both records agree on compiler/runtime identities and the ownership JAR, and the
original reference remains mode 0444. The
[integrity record](ownership-experiment-integrity.json) hashes the evidence.
Its `qualification` remains false: these records do not promote a baseline or
prove native GUI/controller behavior. Later worker-cleanup prototypes are
separate development artifacts and are not covered by this source anchor.
