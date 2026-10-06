# Audit.21 ownership and worker-exit qualification

This is a local software qualification, not release or controller qualification.
Application source is clean commit `ccf069f242418b1c99d74a99397f4da7bb7c8610`;
fixtures are individually bound to that commit or clean QA commit
`f0ca15633410b9d4cb34ef770e353592db167394`. The candidate JAR SHA256 is
`9f3f521dab9f696e46612875157f2dbc2ae112a57fd479813914db5192b9b562`.
The [integrity ledger](worker-exit-final-integrity.json) binds the twelve gates,
133 passing unit tests, paired deterministic builds, repeated packages and
metadata-only diagnostics. All 169 gate source hash entries were checked against
their recorded commit and current source. x64 execution is Rosetta on an arm64
host, not physical Intel.

Facts: interrupted synchronous callers cancel only before claim; after claim
they wait for the actual outcome. On ordinary terminal worker failure the Manager
stops admission before cleanup. Started operations receive an unconfirmed result;
queued unsent operations receive shutdown. Neither is replayed. Exact SyncSender
completion precedes cleanup needing the Manager monitor. Async terminal cleanup
uses the EDT with independently contained callback failures. Connect callback
failures are contained before original transport classification or logging can
render arbitrary throwable data; only a fixed failure signal is emitted.
Original normal stopped-worker drain callbacks still execute on the worker.

Only five JAR entries differ from audit.20: Manager, SyncSender and three WorkerExit
helper entries. The JAR manifest is unchanged. Exact reversible bytecode checks
and independent javap/CFG checks bind the changes. No new third-party dependency,
controller command or successful-reply format is introduced. Exceptions,
exceptional callback thread/order and cancellation semantics intentionally change
as described in [the implementation design](WORKER-EXIT-DESIGN.md).

Coverage includes 120 worker vectors, 46 connection-stop vectors with four positive
assertion-recorder controls, 40 admission vectors and the existing transport,
resource, factory, ownership, posting and lock regressions. Callback assertions
are recorded independently outside containment; historical unsafe controls retain
their original artifacts. The older `worker-exit-clean-characterization.json` is
an unqualified worker-death experiment and is preserved. The separately named
`worker-exit-clean-historical-characterization.json` is the qualified audit.17
transport characterization. Excluded attempts and the unresolved first clean lock
output mismatch are explicitly recorded; no source fix is claimed for that mismatch.

Both repeated runtime packages match bytes and modes. Vendor runtime signatures
were verified after copying; application packages remain unsigned and unnotarized.
Diagnostics inspect metadata and do not launch the application or verify selected
runtime execution. Original JAR remains mode 0444 and hash-pinned; installed app
contents and reference modes remain unchanged. No controller contact, production
volume test or installed-app modification occurred.

Unresolved: stop-versus-active-send admission, unbounded connect/write/whole-operation
waits, mutable outbound data, ambiguous HTTP status/empty acknowledgments, GUI
firmware-file binding, native GUI, physical Intel, hardware and release acceptance.
Completion under VM exhaustion, ThreadDeath, invalid metadata or disposed AppContext
is not guaranteed. Legacy HTTP is plaintext. Original firmware/cache flow is
unchanged and remains unsafe to exercise without the required immediate approval.

The evidence assembler is [audit/worker-exit-evidence-assembler.py](worker-exit-evidence-assembler.py). It consumes ignored
build records at the pinned QA checkout with only allowlisted archival/documentation changes, with the compiler, locked runtimes
and reference artifacts present; it performs no application launch or controller
operation. Recorded product/fixture sources are checked against their clean commits. The assembly checkout permits only explicitly listed archival/documentation changes; it does not claim the archival working tree is clean.

Package provenance: ARM packaging used clean ccf069f and x64 packaging used clean
f0ca156; the packaging source and inputs are recorded per architecture. The two
source_provenance_sha256 values hash the respective source build manifests,
including their different build output paths; those metadata differences do not
change app file bytes or modes. Transport/runtime records bind the application
through the exact JAR hash; they do not independently record its source commit.
The runtime Home-only observation hashes are now independently recomputed against
the complete verified runtime lock. The JAR delta check also rejects removals.

The assembler itself is delivered in the archival commit following QA; its exact
hash is recorded in the ledger. `evidence_assembly_commit` identifies the pinned
product/QA checkout used for assembly, not a claim that this later assembler was
already committed there. Unit tests are rerun with all test/tool Python inputs
verified against QA; archival working-tree differences are explicitly recorded.
The Home-hash verification uses the existing logging-bundled runtime copies,
verified against the same full runtime lock as the audit.21 packages.

Claude evidence followup corrections: the assembler now generates and hashes the
complete candidate SBOM, checks each repeated package against its own source
build and verifies the source manifest hashes and packager commits. The final
133-test run is recorded with every Python test/tool input pinned to QA and
explicit archival working-tree state, rather than asserting a globally clean
execution tree. Historical worker-exit characterization remains byte-identical
to HEAD. Claude reviews are preserved separately from these factual corrections.
