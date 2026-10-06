# Audit.22 final stop check before send

Locally qualified with pinned source, fixtures and packages. This does not
establish controller, native GUI, physical Intel or release acceptance.

Fact: audit.21 reads stop before SyncSender claim, then marks the transaction
started and calls send. Shutdown can land between that read and claim/exposure.
Audit.22 adds one direct read of private volatile `stopped` after claim and before
exposure. If true, it constructs the original unsent -102 shutdown response at
280. It bypasses the old connection-failure suppression flag only on this new
branch. Original callback-attempt and first-response protections still apply.
If false, original exposure and send continue. A later shutdown cannot establish
that a command was unsent; its actual reply or unconfirmed outcome is retained.
This defines a final admission boundary, not atomic cancellation of TCP writes.
Connection setup, command serialization, polling and retry timing are unchanged.

Only Manager changes within the JAR relative to audit.21. The 17-byte tail adds
four exception-handler rows with the original priority; pool, fields, methods,
stack/locals and all unrelated bytes reconstruct exactly. Current Manager SHA256:
`f2960fbf802500891e23a916441f8b7c586d9ae70d6dba5760d40bc9acf04059`.
The integrated JAR SHA256 is
`202c9e1e0b5a7db39fc7a6ab17c46f0e1511cffbf9dcbdbe0199c1737147e9cd`.
Independent javap/CFG checks validate every instruction and handler row and prove
legacy requeue unreachable. Unit negative controls reject code/pool/member
changes and four semantic mutations. The complete final unit suite passes 137 tests (136 before the fixture regression).

Development evidence: 104 memory-only observations compare the exact audit.21
reference with the integrated artifact. They cover sync/async stop after the old
read, stop after claim, claimed caller interruption, queued requests, artificial
stale suppression flags, synthetic SetTime requests and after-admission actual
memory replies. Send-entry counters distinguish no send from incomplete body
recording. Assertion failures are recorded outside containment. Shutdown
exceptions must originate in dispatchLoop, not terminal helper cleanup. Async
callbacks retain their original worker thread on this normal shutdown path.
The after-admission controls use the actual candidate JAR without a hook and
compare exact body bytes, response identity where applicable, and attempt counts.

Test-only hook JARs are constructed in temporary directories. Builders bind the
immutable original and audit.21 reference, reconstruct the complete hook, and
reject every non-Manager entry difference. The gate compares the unhooked
prototype to the actual packaged Manager, its security golden and the complete
JAR entry delta. No hook class/reference is added to the production artifact.
Targeted Xcomp observations require an installed dispatchLoop nmethod and no
compilation failure; only dispatchLoop is selected by compileonly; other compiled code and VM helpers
are not recorded. Separate
Xint observations use the full interpreter. This is bounded method compilation
proof, not whole-app compiled execution qualification.

Excluded: preliminary evidence before independent assertion and send-entry checks;
PrintCompilation stdout interleaving; a full-Xcomp stale task with no installed
nmethod; pre-integration source maps and initial diagnostics on an old golden.
None is accepted as successful qualification or described as a product fix.
Clean source/build/fixture records must follow the source commit.

Claude consultations are archived as `CLAUDE-STOP-ADMISSION-*.txt`. Corrections:
Sender first-response behaviour was verified by existing independent structure
checks, not by pinning the candidate-sender javap file directly. The new gate now
also records that file. Original normal stopped callbacks remain on the worker;
EDT delivery applies to terminal helper cleanup, not this guard. The original
suppression path remains unchanged for already reported failures. The new guard
constructs a shutdown independently of that flag, with positive stale-flag tests.

Unresolved: connect/write/whole-operation deadlines, controller response/status
and empty-ack interpretation, outbound mutable body/headers, GUI firmware binding,
full caller/GUI retry flows, native GUI and hardware/release qualification. VM
exhaustion, ThreadDeath and invalid-metadata completion remain best-effort. x64
runs use Rosetta. HTTP remains plaintext. No app preview, controller contact,
production-volume test or installed app modification was performed.


## Final local qualification and evidence corrections

Application source is clean `1e659d5f8cf590a912eece9fc6e5ce12a54ae5f9`.
The thirteen regression gates pass. Twelve retain clean fixtures at that commit;
the 104 stop vectors use clean QA `73ffa4efbfbab852c7d6990f5087d180b53751bb`.
The application bytes did not change in the QA commit. The unit suite now passes
137 tests, including a fixture-archive regression varying the clock and entry
order, directory metadata and a non-ASCII name against a fixed hash.

The [integrity ledger](stop-admission-final-integrity.json) binds 217 checked gate
source hashes, all thirteen gate records, complete unit outputs and the exact
[unit runner](stop-admission-unit-runner.py). It also binds the full 3,061-entry
[application inventory](stop-admission-sbom.json), repeated builds and both repeated
runtime packages. The assembler records its exact archival-only dirty state;
this is distinct from the clean recorded application/fixture/packager checkouts.
The generator and runner are archived in the later evidence commit, not claimed
to have existed in the application or QA commit. Their exact bytes are hash-bound.

Stop coverage is 16 admission, 72 exposure and 16 after-admission controls. The
latter are eight actual candidate-JAR vectors and eight actual audit.21 reference
vectors, with matching memory replies. The other 88 use reversible test-only hooks.
The assembler reconstructs those hook archives with the pinned builders and checks
whole-JAR hashes. This proves fixture reproducibility; the separate javap/CFG and
reconstruction checks establish instruction preservation. No hooks enter packaging.
There are 52 targeted Xcomp vectors with recorded dispatchLoop nmethod events and
52 Xint vectors. Exact flags and log-path identities are checked; temporary raw
JIT XML was not archived. Native wrappers or other generated VM code are not
inventoried. The legacy worker controls are Xint only.

Claude's clean review exposed weak assembler assertions. Tightening fixture hash
linkage exposed nondeterministic ZIP timestamps. QA changed only the two test
builders and their regression: fixed epoch, sorted entries and explicit metadata.
The stop gate was rerun in an isolated clean worktree. PASS outcomes, nested counts,
factory Cartesian coverage, exact recovery vectors, reference identity, stop
Cartesian coverage and candidate/reference split are now asserted. Original
pre-review ledger, generator, stop and unit records are preserved under the
`stop-admission-pre-review-*` names, with the renamed-path mapping in the final
ledger; they are superseded evidence, not current qualification.

See the actual Claude [clean evidence review](CLAUDE-STOP-ADMISSION-CLEAN-EVIDENCE.txt),
[fixture review](CLAUDE-STOP-FIXTURE-DETERMINISM.txt) and
[followup review](CLAUDE-STOP-ADMISSION-FINAL-FOLLOWUP.txt). Its last two requests
are addressed by archiving the runner and full outputs, checking exact flags and
narrowing JIT claims. All final record and generator hashes were independently
recomputed against the ledger after assembly.

First verify the frozen archived record and generator hashes against the ledger;
do not run the runner or assembler in place to verify historical bytes. The final
ledger SHA256 is `df1e0ea85687dcabc1248d0abb15dabeb14c67b5c1b62c6e10ea018d978aec57`.

Reproduce only in a disposable QA `73ffa4e` worktree, with the locked inputs and
recorded ignored build outputs. Copy only explicitly allowlisted archival files
into `audit/`, and provide the pinned intake reference at the assembler's
`ROOT.parent/audit/reference/RAID Admin.app` path. Run `python3 -E -s` with the
archived unit runner, then assembler. Both overwrite their output records and
ledger. Unit elapsed time changes, so stderr, derived unit JSON and ledger hashes
are expected to differ; compare the unit result excluding elapsed time and compare
unchanged artifact/gate/package bytes exactly. Do not overwrite the frozen record.
Python version and implementation are enforced; the interpreter binary is not
hash-pinned. The thirteen gate records retain their raw checked bytes; unit JSON is
the assembler's checked augmentation of runner metadata.

Actual assembly occurred in the main checkout at QA `73ffa4e` with only the
explicitly recorded archival files untracked. Documentation and Claude transcript
files were added afterward. The refreshed stop gate ran separately in the clean
`../audit/stop-determinism-qa` worktree. Neither development-mode observations nor
the later documentation tree are described as clean qualification execution.

The [closure review](CLAUDE-STOP-ADMISSION-CLOSURE.txt) confirms the code/evidence
blockers are fixed and requests the reproduction/count documentation corrections
above. Its inference that assembly must have used a separate worktree is corrected
by the recorded chronology: docs were added after main-checkout assembly. Exact
pre-review unit stdout/stderr are additionally preserved under
`stop-admission-pre-review-tests.{stdout,stderr}` and verified against the hash
fields in the preserved pre-review unit record. The frozen final ledger is unchanged.
