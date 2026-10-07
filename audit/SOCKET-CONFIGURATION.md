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

Development evidence: two builds produce JAR
2fccbee50eb868a04b415085511e0b52e6a13682543858d6f653b7f1f5fcadad;
140 unit tests pass. The actual candidate's class origins and bytes are checked
before each memory harness. Twenty-nine positive cases run on each ARM/x64
bundled runtime in Xint and Xcomp policy modes; twelve semantic mutants are
rejected by exact fixture assertion/frames on each bundled runtime in Xint.
Verifier errors, timeouts and class-identity failures do not qualify as negative
controls. Compiler/runtime files and modes are independently locked. Xcomp does
not prove that every method compiled. x64 execution uses Rosetta, not physical
Intel. These are software fixtures, not native socket or feature acceptance.
Clean committed source, full regression and repeated packages remain pending.

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
