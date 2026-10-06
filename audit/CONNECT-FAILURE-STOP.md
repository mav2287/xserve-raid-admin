# Audit.18 reported initial connection failure

Status: development; clean qualification pending. The current qualified release
remains audit.17 until the full clean gate and packaging records are archived.

Fact: a single-host constructor failure, or the second failed host attempt on a
dual-host system, produces TYPE_CONNECT -101. The original worker can subsequently
send the held request after the caller has already received ConnectException.
The isolated characterization compares the actual held cloned request identity
and serialized body, with a test-only constructor/send shadow and bounded worker
stop hook. It never opens a socket or instantiates a production RaidSystem.

The thin bytecode patch stops the local Manager before publishing the failure.
It does not restart/shut down the controller. Successful connection instructions,
command bytes, original error codes, exception wrapping, dual-host first silent
fallback delay and null-handler retry instructions remain unchanged. An invalid
address/no-host result also stops, including with a null handler. The failure flag
is set before this branch's original logger/callback, avoiding a held command
response after the connect notice. A throwing Exception callback still takes the
existing generic -102 path; queued commands are drained with CommShutdownException.

Source boundary: audit.17 already makes established-session worker faults terminal.
This change's added availability cost is stopping on a *published initial*
connection failure. The GUI-source review's initial suggestion that this removes
established-session reconnection is superseded by the implementation-design review.
Do not infer native UI recovery from this change. Registry loading and Add System
create a fresh manager in source; reauthentication/refresh use the same manager.
A stopped manager cannot be reused. Remove/re-add workflow and native GUI recovery
are unqualified. Production hardware and mounted volumes have not been tested.

Original doConnect Code is 718 bytes; candidate 754, stack 6, locals 16, major 47.
PC393..400 becomes goto_w718 plus three dead nops. PC578..582 becomes goto_w740.
The appended blocks call the existing required-stop/connection-retirement helper,
copy the overwritten original instructions and return to PC401/583. The no-host
block sets connectionFailureSent first. The six original exception table rows and
all remaining original instructions/metadata are unchanged. Replacing only this
Code attribute with the original reconstructs the exact audit.17 Manager class
SHA-256 7c07f4c31a6104f52ee151e07141296d5b59ef33fa5105b895c6504c58ac2a1c.
The full-mask gate and independent javap gate verify these boundaries separately.

Candidate JAR: d1d09ce03e39b507225eb11c1704925161a03d0440518ef94fab5d97e998bfd6.
Manager class: a928b493ecf796ab90415339a20f8f7cd4914afaa3add052bdff1796cad70893.
Only Manager and the recovery feature constant should change from audit.17 JAR
entries; final qualification must independently check this statement.

Testing scope: real Manager/SyncSender with strict test-only AcpxConnection shadow,
CodeSource and resource-hash checks, exact fixture/shadow class allowlists,
interpreted/compiled verified JVM execution, and a 35-second parent watchdog per
scenario. Original controls include a byte-identical compatibility shim. Three
verifier-valid mutants restore each stop window and must demonstrate unsafe
semantics; errors, verifier failures and timeouts never count as a negative pass.
Fake polling-enable calls do not establish real polling-agent behavior. No fixture
interrupts the worker: original shutdown only sets stopped and notifies the queue.
The x64 runtime here runs through Rosetta; physical Intel remains unqualified.

Residual facts: posts after worker exit can remain queued without a callback;
a concurrent synchronous stopped-check/enqueue/worker-exit race can also leave an
untimed waiter blocked indefinitely. Initial-connect stopping adds exposure to this
existing race; this release does not repair posting/exit atomicity.
Interrupted synchronous waits can report failure while leaving work executable;
throwing callbacks can strand waiters; original queue/manager lock ordering can
still deadlock. These are not fixed by the initial-connect stop. GUI firmware
preflight binding, malformed-but-valid reply schemas/status, true Intel/native GUI,
signing/notarization and restricted real hardware acceptance remain open.
Legacy HTTP is plaintext; the body codec does not encrypt the protocol.

Actual read-only Claude consultations: [terminal design](claude-review/CONNECT-FAILURE-TERMINAL-DESIGN.txt),
[GUI source review](claude-review/CONNECT-FAILURE-GUI-RECOVERY-SOURCE.txt),
[implementation design](claude-review/CONNECT-FAILURE-IMPLEMENTATION-DESIGN.txt),
and [characterization review](claude-review/CONNECT-FAILURE-CHARACTERIZATION-REVIEW.txt).
Review suggestions are checked against executable/source evidence, not treated as
proof by themselves. The nonexistent PropertyListDictionary suggestion was corrected
using the original PropertyList(Object) constructor with a synthetic dictionary.
Failed development runs and tests that hit guards are excluded from qualification.

[Claude code review](claude-review/CONNECT-FAILURE-CODE-REVIEW.txt) requested in-callback single/dual assertions, a stop-order mutant, independently archived audit.17 class derivation, and explicit disclosure of synchronous enqueue/exit hanging. Those checks and disclosures are implemented; follow-up review and clean qualification pending.

[Claude follow-up](claude-review/CONNECT-FAILURE-CODE-FOLLOWUP.txt) confirmed callback and mutant arithmetic. Its metadata tuple blocker was already fixed by the time the review returned; the historical characterization now also asserts the measured audit.17 Manager class equals the reconstruction pin. Earlier failed metadata and development runs remain excluded.
