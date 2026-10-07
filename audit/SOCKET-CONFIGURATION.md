# Initial socket read-timeout setup

Audit23 implements one exact override of private HttpConnection.createSocket(int)
and adds compat.SocketConfiguration. It retains original Socket(host,80), ignored
5000 connect argument, single-address/null-host constructor behavior, commands,
polling, retry policy and successful request/reply behavior. DNS, TCP writes and
whole operations remain unbounded; no new five-second TCP deadline is shipped.

A failed or mismatched initial SO_TIMEOUT installation now closes the returned
socket best effort and refuses publication. Original code logged SocketException
and continued, potentially with unlimited reads. Standard IOException categories
and InterruptedIOException.bytesTransferred are retained. Untrusted IO detail is
replaced by fixed `Connection setup failed`, without cause or suppressed data.
This intentionally changes original error prose in exception-based UI/CLI paths.
SecurityException and setup Error/ThreadDeath retain identity; other setup runtime
errors become fixed IOException. Close Throwable is discarded to retain the
primary failure. Constructor failures retain the original JDK cleanup behavior;
constructor-Error cleanup and VM exhaustion are not guaranteed. Custom IOException
subclasses are unsupported extension behavior, not exact subtype preservation.

Only the Code attribute and five appended constant-pool entries change in the
original HttpConnection class; complete normalization recovers its exact original
SHA256 c8a632a9c5c76e94fe1c3a9e23b6e362d8e50fff75eeb26ee7379ab6c7159303.
All other audit22 JAR entry bytes are retained; one helper is added. Legacy
TARGETS/transform API still reproduces the historical audit20 predecessor.

Local qualification: two clean builds at application source `f9a5edb` produce JAR
2fccbee50eb868a04b415085511e0b52e6a13682543858d6f653b7f1f5fcadad;
140 unit tests pass. The actual candidate's class origins and bytes are checked
before each memory harness. Twenty-nine positive cases run on each ARM/x64
bundled runtime in Xint and Xcomp policy modes; twelve semantic mutants are
rejected by exact fixture assertion/frames on each bundled runtime in Xint.
Verifier errors, timeouts and class-identity failures do not qualify as negative
controls. Compiler/runtime files and modes are independently locked. Xcomp does
not prove that every method compiled. x64 execution uses Rosetta, not physical
Intel. These are software fixtures, not native socket or feature acceptance.
Thirteen candidate regression gates, one historical characterization and repeated
packages per architecture pass. The socket
and consumer checks plus unit run use clean QA `96861bf`; other fixture executions and packages
use clean source `f9a5edb`. The characterization fixture runs at `f9a5edb`
against the historical audit17 candidate `47166ed` / JAR `948c1d…`, not audit23. All 272 gate/inventory source-map entries
match their own commits and current bytes. See [integrity ledger](socket-configuration-final-integrity.json)
and archived complete unit output, static disassembly and archived actual Claude CLI consultations:
[prototype](CLAUDE-SOCKET-CONFIGURATION-PROTOTYPE.txt),
[follow-up](CLAUDE-SOCKET-CONFIGURATION-FOLLOWUP.txt),
[prototype closure](CLAUDE-SOCKET-CONFIGURATION-CLOSURE.txt),
[integration](CLAUDE-SOCKET-CONFIGURATION-INTEGRATION.txt),
[integration closure](CLAUDE-SOCKET-CONFIGURATION-INTEGRATION-CLOSURE.txt),
[evidence design](CLAUDE-SOCKET-CONFIGURATION-EVIDENCE-DESIGN.txt), and
[final evidence review](CLAUDE-SOCKET-CONFIGURATION-FINAL-EVIDENCE.txt).
These static reviews are outside the ledger and are not execution/hash proof.

The reproducible static consumer inventory now includes all eight standard IO
setup categories, including IOException, SocketException and BindException.
It supersedes the earlier prototype's narrower type filter. All 2862 candidate
class constant pools are scanned; 194 getMessage-reference classes and 281
exception-type-reference classes are listed. Full disassembly covers 319 selected
classes and 210 String-returning getMessage invocation sites, including unqualified
CommandLineException.toString. Other library getMessage references are listed;
external extension reachability and actual UI/CLI rendering remain unqualified.
Throwable.toString, getLocalizedMessage, append(Object) and other rendering paths
are not exhaustively inventoried; this scan identifies getMessage calls only.
The configured SafeLogAppender emits fixed codes, never these messages or causes.

AcpxConnection publishes a HttpConnection before open succeeds. A later send with
a changed timeout can dereference its null socket; this predates the patch and
now also follows refused initial setup. Current direct HttpConnection reconnect
coverage does not qualify that cached AcpxConnection sequence. Cached setter
handling is the next separate narrowly scoped repair. Concurrent reflective
mutation, native GUI, physical Intel, controller availability, discovery, firmware
workflows, status/empty-ack interpretation, mutable outbound inputs, native TCP
behavior, signing/notarization and hardware acceptance remain open. HTTP is
plaintext. No app Main, native sockets, production volumes, real credentials,
controller operations or installed-app changes are involved in these fixtures.

Historical audit22 evidence remains frozen at its original commits. Reproduce it
from the documented clean source/QA commits in STOP-BEFORE-SEND.md, not by running
the old assembler against current audit23 source. audit/audit22-expected-build.json
preserves the old golden record; it does not redirect current gates to old inputs.
Admission/exposure fixtures now retain every non-Manager candidate entry while
using exact audit21 or guarded Manager bytes. Active controls retain the actual
unmodified audit21 reference and actual candidate. Both basis entry deltas and
helper identity are validated; historical default fixture hashes are checked
against frozen audit22 evidence. All hooks remain test-only.

The direct failure cases share assertion lines. Negative records identify each
source mutation and its first failing fixture assertion, not independent failure
traces for every positive case. All positive cases remain individually checked.

The first clean lock run returned an unexpected observation under concurrent
qualification work. Its unchanged rerun under reduced concurrency passed all 20
observations; the first cause remains unresolved, and that failed run is excluded.
The unchanged-source comparison relies on tool/session history; the failed
run produced no provenance JSON and its unexpected stdout was withheld and not
retained. Its [stderr](socket-configuration-excluded-first-lock.stderr) is archived.
No product or fixture change was used to make the rerun pass. The Manager bytes
are identical to audit22. This does not establish deterministic scheduling or
production timeout behavior.

Reproduction: check out application commit f9a5edb for the two baseline builds,
existing 13 gates and repeated packages. Check out QA 96861bf for the updated
socket gate, inventory scanner and unit run. Both retain identical product inputs
and JAR bytes. Each gate records its command/runtime flags or tool/source hashes.
The archived assembler and unit runner pin these commits and verify every input;
replay them in a disposable checkout with locked build/runtime inputs and the
recorded build directory names, before adding documentation or archival outputs.
The assembler refuses to overwrite evidence. Fresh elapsed times, temporary
paths and their identity-manifest hashes can differ; product/package bytes,
fixture assertions, coverage, source hashes and runtime identities must match.
Verify frozen ledger hashes before replay; never overwrite historical evidence.

Frozen audit23 ledger SHA256:
`509f54f24919ac99ca0168508c1330410297d667fb000689f132f83954cc5137`.
A [separate rehash invocation](socket-configuration-independent-rehash.json)
verifies all 25 archived record hashes and the frozen audit21/audit22/audit23
ledgers; [verifier source](socket-configuration-independent-rehash.py) is bound
by that record. Its documentation/archival checkout is explicitly dirty, unlike
recorded feature/packaging executions. Do not infer a clean execution from the
later evidence commit alone.

For assembler replay, copy its archived source and the unit runner to the exact
ignored `build/socket-configuration-evidence-assembler.py` and
`build/socket-configuration-unit-runner.py` paths in a clean QA checkout, with no
new audit23 outputs present. Recreate the audit22 reference at
`build/stop-admission-clean-1` from its recorded source and compiler; the historic
audit17, audit20 and audit21 gate references are also required by their individual
gate commands. The assembler's installed-intake check requires this machine's
exact `/Applications/RAID Admin.app` contents; it is not a portable acceptance
claim. Reproduction elsewhere must report that intake comparison unavailable
rather than fabricating it. Gate/consumer/unit archives are byte copies; package
and diagnostic archives are normalized JSON summaries. Python unit inputs cover
tracked test/tool Python sources; other tracked build/fixture inputs are bound by
individual build/gate source maps. Ignored prototype files are excluded.
