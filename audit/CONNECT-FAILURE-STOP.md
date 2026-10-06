# Audit.18 reported initial connection failure

Status: clean qualification passed at source/fixture/package commit `7aa02c5`.
The scoped current candidate is audit.18; native GUI, hardware and release
acceptance remain open. Actual Claude clean-evidence review and follow-up are archived below.

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
scenario. Original controls include a byte-identical compatibility shim. Two
verifier-valid mutants restore the stop windows and one reverses stop/callback ordering. All must demonstrate unsafe
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

[Claude code review](claude-review/CONNECT-FAILURE-CODE-REVIEW.txt) requested in-callback single/dual assertions, a stop-order mutant, independently archived audit.17 class derivation, and explicit disclosure of synchronous enqueue/exit hanging. Those checks and disclosures are implemented; follow-up review and clean qualification completed below.

[Claude follow-up](claude-review/CONNECT-FAILURE-CODE-FOLLOWUP.txt) confirmed callback and mutant arithmetic. Its metadata tuple blocker was already fixed by the time the review returned; the historical characterization now also asserts the measured audit.17 Manager class equals the reconstruction pin. Earlier failed metadata and development runs remain excluded.

## Clean qualification

Two clean source builds reproduce the candidate JAR. Nine gates passed with exit 0
and empty stderr at `7aa02c5`: [security](connect-stop-clean-security.json),
[transport](connect-stop-clean-transport.json), [runtime](connect-stop-clean-runtime.json),
[resources](connect-stop-clean-resources.json), [shared stream](connect-stop-clean-shared.json),
[request factory](connect-stop-clean-factory.json), [posting](connect-stop-clean-posting.json),
[connection stop](connect-stop-clean-connect.json), and
[historical characterization](connect-stop-clean-characterization.json).
The last gate intentionally uses the clean audit.17 reference from source `47166ed`
and current `7aa02c5` fixtures. It asserts the measured Manager class against the
reconstruction pin. Original and audit.17 controls expose the held command's later
execution; the current candidate blocks it. Current gate results use 36 interpreted/
compiled positives and six semantic controls, three per architecture. The added
callbacks prove stop ordering from inside single/dual notices and preserve the
reported-callback Exception identity. The reorder control is verifier-valid and
observes the notice before stop. [112 Python tests](connect-stop-clean-tests.json)
include every stop-window/tail byte and other-method/frame mutations.

The unchanged 143-line recovery matrix and 116-row factory table pass.
[Package evidence](connect-stop-bundle-results.json) reproduces files, file modes
and directory modes twice per architecture while preserving verified vendor
runtime signatures. [Arm64 diagnostics](connect-stop-diagnostics-aarch64.json)
and [x64 diagnostics](connect-stop-diagnostics-x64.json) identify the reviewed
candidate. x64 executes under Rosetta, not physical Intel.

[Final integrity](connect-stop-final-integrity.json), SHA-256
`3e59d807f3ac22fef16eeba047b7414b125fd247c00a584604b70262d9532b67`,
maps archive filenames to hashes, checks committed fixture sources and preserves
original mode 444 plus installed-app files/modes. Only Manager.class and the
recovery feature constant class differ from audit.17 JAR entries; the manifest
entry is unchanged. No new dependency, controller contact, production/mounted
volume test, installed-app modification, signing or notarization occurred.
Runtime.jdk and Contents/Home hash scopes are recorded separately.

Excluded development runs include the initial guard-triggering experiments,
incomplete fixture identities, a metadata tuple error, and a run whose expected-
build input changed while qualification anchors were being prepared. None is
represented as clean passing evidence. This archival documentation does not change
any `7aa02c5` qualification input.

[Claude clean review](claude-review/CONNECT-FAILURE-CLEAN-EVIDENCE.txt) read the gate
records while final integrity was still being generated; the missing-ledger
finding is resolved by the archived final integrity and JAR-entry comparison.
[Run results](connect-stop-run-results.json) explicitly archive the orchestrator's
observed exit codes, empty-stderr measurements and gate output hashes. The mutant
wording is corrected to two window bypasses plus one stop-order mutant. Diagnostics
contain only filtered local interface names, no addresses/credentials; their hashes
and scope are included in final integrity. Claude compared recorded values;
executed qualification and integrity checks supply checksum verification.

[Clean follow-up](claude-review/CONNECT-FAILURE-CLEAN-FOLLOWUP.txt) requested complete
runtime hash formulas and an explicit audit.17 baseline for entry comparisons.
Final integrity now includes fresh files-only, Home files-only, and files-plus-
file-modes runtime measurements; the last matches the vendor lock and gate/package
records. It records the audit.17 reference JAR hash, each changed entry's before/
after hashes and byte-identical manifest hash. Those changes are evidence metadata,
not new application or fixture changes. All named qualification inputs remain the
committed `7aa02c5` bytes. Interface names in diagnostics are filtered identifiers,
not addresses or secrets. No publication or release deployment was performed.
