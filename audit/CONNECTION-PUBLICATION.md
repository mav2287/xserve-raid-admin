# Failed-open connection publication — development audit24 proposal

Audit23 remains the qualified application baseline until the clean build and
regression evidence for this proposal is recorded. This is a private compatibility
repair, not an application rewrite or controller qualification.

## Facts

Original AcpxConnection.createConnection stores a new HttpConnection in its
connection field before calling open. The send call to createConnection precedes
its try/finally. Failed open therefore retains a socketless cached connection.
The actual audit22 and audit23 classes reproduce three explicit calls: first a
SocketTimeoutException, then a custom-timeout NullPointerException after
newRequest marks requestOutstanding, then IllegalStateException before another
socket is constructed. These are trusted JVM-local memory SocketImpl observations,
not real controller traffic. No request reaches native socket output.

The proposed private override constructs a local candidate, forwards the original
host and persistent flag, invokes open once, and only then stores the candidate.
It adds no handlers, retries, delays, commands, fields, methods or constant-pool
entries. Failure escapes before request creation and leaves no cached candidate.
All other class bytes can be reconstructed exactly to the audit23 predecessor.
The original public timeout setter and the existing send override are preserved.

## Deliberate exceptional behavior change

Repeated explicit caller attempts after an initial open failure now each attempt
one connection, instead of dereferencing a socketless cache or stranding the
requestOutstanding flag. Default-timeout reconnect failure also moves earlier,
before newRequest and the send try/finally. This removes the legacy HttpRequest
error-log/finally path for that failed open. Manager classification and automatic
retry policy are unchanged. No atomic cancellation/concurrent-close guarantee is
introduced; the original Acpx object is not made thread-safe.

## Scope and unresolved evidence

Static caller review indicates current Manager/CLI paths retire or discard the
failed object. Reuse is therefore a latent direct-API gap, not a demonstrated
user-facing controller failure. Reflection/extensions are not fully qualified.
Memory tests cover normal/failed construction, the preserved already-open warning branch, three failed explicit attempts,
initial timeout setup failures, SecurityException/Error identity and a security-manager denial, successful open
followed by a marker writeTo failure, timeouts 0/30000/7301, and both persistent
flags. The original outstanding-request bookkeeping after writeTo failure is
intentionally retained; this is not successful response recovery coverage.

Four verifier-valid mutations run with Xint on each architecture; Xcomp positives verify the actual candidate. They test early/missing publication, omitted open and
omitted persistent forwarding. Missing-open and missing-publication share the
constructor assertion; they are distinct mutations, not independent traces.
The positive gate counts 26 cases and 34 explicit failed-send attempts per runtime/mode. A warning/error counting appender never reads or renders event payloads. Failed JDK construction with Error retains the original zero-close observation; this override does not promise cleanup for arbitrary JDK fatal failures. Both bundled runtimes are tested with -Xverify:all and requested Xint/Xcomp.
x64 execution is Rosetta, not physical Intel. No app Main, native GUI, controller,
production/mounted volume, credentials/profile, or installed-app mutation occurs.
The legacy HTTP protocol is plaintext.

Failures after newRequest may still strand a direct persistent Acpx caller (for
example live setTimeout or writeTo failure). Source also retains the original
Connection: close response handling. Those paths are deliberately unchanged;
current Manager/CLI retirement is not complete extension/API recovery proof.
Reverification of historical audit23 artifacts uses commit 68a84a5 and its own
goldens/records. Current gates require the new private override and must not be
used to relabel an old artifact as the current baseline.
