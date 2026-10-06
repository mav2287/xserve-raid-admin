# Audit.15: stop after ambiguous I/O without automatic resend

Status: clean offline qualification passed on commit `6427120`; 93 Python tests
and all six regression gates pass. This closes
one demonstrated resend path. It does not certify the application as fully secure
or operational against production hardware.

## Change and compatibility cost

Fact: original `CommunicationsManager.run` handles a non-null IOException whose
message does not start with the original property-list error prefix by putting the
transaction back at the front of the queue and reconnecting. A lost response can
therefore resend a command that the controller may already have applied. Factory
metadata does not establish idempotency for this behavior.

Audit.15 changes only the two-byte operand of `ifeq` at PC 349: `001f` (PC 380)
becomes `00d6` (PC 563). It reuses the previously verified fixed marker block,
then audit.14's local session shutdown before logging/callbacks. This is a Java
communications-session stop, not a controller shutdown command. No request bytes,
controller commands, polling intervals, initial connection timing or successful
response semantics are changed. The legacy retry region PC 380–458 is retained
byte for byte but is unreachable. Relative to audit.14, code length remains 578, with the same constant
pool and 12 exception handlers. The feature constant is a fixture selector;
qualification independently checks the actual branch, retained bytes and CFG.

This intentionally restricts behavior: failed reads and cleanup I/O after a valid
reply also stop the session. A `-102` result means outcome unconfirmed, never
“the mutation was not applied.” Already queued requests are drained by the
original stopped-session path without sending. A new model/session is required;
the complete GUI recovery procedure has not been qualified. Late asynchronous
posts can remain queued without callbacks. Concurrent synchronous post/worker exit
and interrupted waiters are separate unresolved liveness/cancellation issues.

## Evidence and limits

Actual Claude design and refinement reviews approved this narrow branch change:
[design](claude-review/AMBIGUOUS-IO-TERMINAL-DESIGN.txt),
[refinement](claude-review/AMBIGUOUS-IO-TERMINAL-REFINEMENT.txt).
The refinement's suggestion to forbid all reachable `doConnect` and
`monitorenter` instructions was too broad: initial connection setup and the
ordinary queue monitor must remain. The independent CFG gate excludes the retry
region and reachable LinkedList additions while retaining the prefix branch.

Development transport observations passed on pinned Corretto 8.504.04.1 arm64
and x64 under Rosetta, with verification enabled. Faults are bounded memory seams:
response loss, empty-message IOException, EOF, immediate timeout, failed header
writes before/after 8 bytes, failure before the first body byte, injected prewrite
ConnectException, disconnect failure after parsing a reply, and a synthetic idle
close following a successful operation. Each failed operation makes one attempt
and blocks a queued synthetic restart. Both interpreted and compiled JVM execution
are tested. No fixture opens a socket or contacts a controller. The prewrite seam
is not a real refused TCP connection, and no backoff/real socket timing is inferred.

A verifier-valid mutant targeting PC 464 bypasses marker creation; the containment
fixture must reject it. A separate mid-instruction mutant fails JVM verification.
Python negative controls reject old retry targets, handler reentry, other branch
reentry, unaligned destinations, missing/duplicated/mixed policy vectors, and loss
of the preserved prefix path. The exact 143-line security recovery matrix remains
required for the new artifact. Healthy controller negative result codes remain
original results and are not classified as I/O rejection.

Source corrections: the original `doConnect` path constructs `AcpxConnection`
and ultimately opens a Socket; its connection retries do not themselves serialize
an HTTP request. `HttpRequest.send` contains a loop, but its local attempt counter
starts at 1 and the IOException handler decrements to 0 and throws. Its retry branch
is unreachable for that locked bytecode. `HttpOutputStream.close` calls send when
not yet sent; a separate caller invoking close again can still resend. The original
request/codec stream lifecycle and direct CLI entry paths have not received complete
runtime qualification. The fixture's separate direct firmware-stream resend
characterization is historical behavior, not an authorized hardware transmission.

Unresolved: prefix `-103` parsing failures, MalformedInputException and generic
Exception paths can still allow dependent queued writes. Synchronous cancellation,
UI outcome/recovery, HTTP status handling, response association, firmware chooser
preflight and immutable transmission binding, native GUI behavior, physical Intel,
real controller operations, signing and notarization remain open. Legacy HTTP is
plaintext; the body codec is not encryption. No production-volume or installed-app
test is performed here.

## Claude implementation review disposition

[Implementation review](claude-review/AMBIGUOUS-IO-TERMINAL-IMPLEMENTATION.txt)
found no code blocker. Its qualification concerns are addressed as follows:

- Dirty development records are excluded from clean qualification. A committed,
  clean two-build identity and rerun of every relevant gate are required below.
- The architecture tool's 143-line matrix is explicitly a retained audit.14
  security-marker regression. Its policy flag selects the artifact, and does not
  supply non-prefix I/O qualification; that comes from the transport fault matrix.
- The CFG now requires precisely the retry instructions to be unreachable and
  keeps initial connection, queue monitor, prefix and exit-close instructions
  reachable. Additional negative tests remove those normal paths.
- The semantic negative must observe a non-marker/uncontained exception state;
  unrelated assertions cannot count as success. Healthy HTTP/ACP result callbacks
  explicitly assert the session has not stopped.
- `response_entries` counts calls into the response seam after writing, not a
  completed response. The synthetic idle-close case injects EOF at that seam after
  a successful operation; it does not model a real shared socket. Header/body
  truncation is separately measured in the existing transport corpus.
- Close counts are asserted: response-seam faults have one retirement disconnect;
  write/prewrite/cleanup faults have two calls because the original HTTP cleanup or
  nonpersistent finally path precedes session retirement. These are cleanup calls,
  not repeat request attempts. Both codec and plain body-write faults make one
  attempt. Codec is the legacy body codec, not cryptographic protection.
- Xint/Xcomp cover the fault matrix; the prefix corpus and negatives use normal
  execution with full verification. The worker join bound is 5 seconds; the main-thread idle sequence is bounded only
  by the 30-second outer JVM timeout. No all-mode claim is made.

The source comparison changes only Manager and RejectionRecovery entries versus
audit.14. Although the edited operand is two bytes wide, only its low byte differs
(`1f` to `d6`); the actual Manager class byte difference count is 1. See
[source identities](terminal-io-source-identities.json). Pinned arm64 and x64
FilterOutputStream disassemblies agree; each close path calls the underlying close
once. That source fact and the codec fault test do not qualify every possible
caller or firmware/CLI stream lifecycle.

Real refused connections inside send, complete delete/unmap/restart, Restarter,
create and firmware caller workflows, a real shared-socket idle close, and bounded
concurrent synchronous-post stress are deferred rather than inferred from the
single queued-write containment seam. The existing original/candidate drop
comparison demonstrates the removed resend, while the additional fault matrix is
candidate-only. The strict factory regression must independently verify all 116
successful body serialization rows and metadata; wire headers are not covered. Getter exceptions and shutdown failures can still
kill the worker outside its cleanup handler; GUI/liveness acceptance remains open.

[Final Claude follow-up](claude-review/AMBIGUOUS-IO-TERMINAL-FOLLOWUP.txt)
approved committing this narrow claim before clean qualification. Its remaining
conditions require clean source/fixture identities, full policy flags, both runtime
architectures and independently bound Python test sources in the final record.

## Clean qualification

Source, fixture and package commit `6427120` was clean. Baseline clean3/4 match
the reviewed identity. JAR SHA-256:
`4fb45ef850687309834fd9f082f47819ea7deadc5866108115f8a2ac5c1311bd`.
Audit bundle tree:
`1774aceee45aea35c84311e7aa1f4e081f585fdc6133c09aab020443268f10ac`.

- [Independent source/bytecode/security gate](terminal-io-clean-security.json)
- [Full transport policy and 11-case terminal fault matrix](terminal-io-clean-transport.json)
- [Both runtime API/parser/header/retained-marker regressions](terminal-io-clean-runtime.json)
- [Bounded parser resources](terminal-io-clean-resources.json)
- [Shared-stream association](terminal-io-clean-shared.json)
- [116 body serialization rows/metadata and six clone cases](terminal-io-clean-factory.json)
- [93 Python tests and committed test-source hashes](terminal-io-clean-tests.json)

The transport record includes both architectures, both logging modes for parser,
allocation and headers, interpreted/compiled fault matrices, semantic negative
controls and original/candidate drop differentials. The architecture record's
143-line matrix is retained security-marker evidence, not non-prefix I/O evidence.

Both packaged architectures reproduce files, modes and directory modes:
aarch64 tree `23c0462a4b0f7b449c5f16bbf13b3b35d01d7a10a88d5bbd66d31d361280b3b7`;
x64 tree `fa997ee933b8f314af624be5699cb176b751a51b8f2ac227b1e05160913fc666`.
[Package records](terminal-io-bundle-results.json) retain vendor signature
verification before/after byte-only runtime copying. Diagnostics match reviewed
artifact and manifest and correctly report audit.15 on
[arm64](terminal-io-diagnostics-aarch64.json) and [x64](terminal-io-diagnostics-x64.json).
Application signing/notarization was not performed.

[Final integrity](terminal-io-final-integrity.json) verifies recorded fixture
sources against committed bytes and confirms the immutable original JAR and
installed application files/modes are unchanged. No controller contact, production
volume test, installed-app modification or restricted operation occurred. x64 on
this arm64 host is Rosetta, not a physical Intel acceptance result. Development
records are excluded from this clean proof.

[Claude clean-evidence review](claude-review/AMBIGUOUS-IO-TERMINAL-CLEAN-EVIDENCE.txt)
found no blocker. Its read-only limits are supplemented by the actual successful
gate exit codes, empty stderr checks, record checksum verification and committed
source-hash verification in the final integrity record.
