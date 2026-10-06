# audit.9 terminal security rejection recovery

**Fact:** audit.7–8 guarded queues establish that new body/header ceiling rejection
leaves the legacy persistent connection outstanding and the next command fails
before transmission. The user authorized safe security closure. audit.9 deliberately
retires this unsafe connection while preserving the failed command's terminal
-102 result, callback context and absence of resend.

## Narrow changes

Only new compatibility body/header ceilings throw the final, package-constructed
UntrustedResponseException subclass of IllegalArgumentException. Original invalid
numeric/negative response lengths and ordinary IO/runtime failures keep their
original exception types and paths. XML failure handling is unchanged.

AcpxConnection.send retains every original instruction and exception entry. Its
major-47 Code appends a five-byte handler; one exact-marker catch entry for the
original [32,271) response-processing region precedes the original catch-all
finally. The handler closes the connection and rethrows the same object. Cleanup
IO/runtime/linkage failure is contained, so it cannot replace the marker with an
IOException and cause the legacy queue to replay the transaction. Normal requests
still execute the original finally. Marker throw sites occur before the local
response stream is assigned, so bypassing that finally loses no assigned stream.

CommunicationsManager.run changes exactly its ten-byte generic-error logging
window at offsets 464–473 to a compatibility reporting call and four nops. All
other instructions, offsets, branches, handlers, frames, jsr/ret and methods remain
unchanged. Ordinary errors log through the same category and retain measured caller class/
method. LoggingEvent caller-FQCN metadata differs; no line-number table exists in
the pinned run Code, and custom layout behavior remains unqualified. Only the exact marker also sets connected=false under the manager lock
and closes outside that lock. The closed host-bearing reference is retained so
the original doConnect controller alternation remains available. The next distinct
queued command enters the unchanged connect path; the failed command is never
requeued by this new path. No polling/backoff constants are altered.

Private-field metadata is type/modifier checked lazily and cached. Metadata or
runtime-manager-class mismatch stops this manager using its public shutdown
method; queued transactions take the original stopped-manager failure path. Marker
logging exceptions cannot skip cleanup or callbacks. Fatal VM errors/ThreadDeath
are not swallowed. Complete helper inclusion and public descriptors are checked
against the built artifact; these measures do not claim recovery from a corrupted
or missing helper JAR at runtime.

## Deliberate semantics and evidence limits

Closing happens before the queue reports the marker, so a socket-close debug event
can precede the original terminal error event. The shipped appender emits only
bounded fixed codes. The callback observes connected=false on the normal security
path; that differs deliberately from the original stale state. If new metadata
cannot be linked, the manager stays stopped rather than continuing unsafely.

Memory-only fixtures exercise all four ceiling violations, persistent/nonpersistent
transport, the legacy body-codec branch before decryption, close IO/runtime failures, synthetic shutdown/restart *connection flags*
on ordinary getters, marker identity, a throwing marker appender, metadata failure
shutdown, ordinary logger category/location parity, and two distinct queued reads
with retained contexts. The reconnect seam uses an invalid-address callback to
inject a fresh in-memory connection; it is not real network or backoff validation.
The original is never supplied oversized inputs. No real shutdown/restart command,
firmware, hardware, installed app change or production-volume test occurs.

Both source preservation masks and independent javap comparisons verify the new
sites. Exact helper linkage is checked; verification-on fixtures cover both new
markers and ordinary original IO handling. The legacy ambiguous IO replay policy
remains open (G10), as do status/framing interpretation and real socket recovery.
Physical Intel, native GUI, actual controller responses and full release acceptance
are not implied. The actual CLI review found no implementation defect. Direct CLI callers
(CommandDispatcher DefaultHandler and handler 15) also take the new close-and-rethrow
path; their lifecycle/error UI is unqualified and they were never run. The normal
poller gates on pollingEnabled/stopped, then posts a power-state request regardless
of isConnected; these are static facts from the immutable bytecode, not elapsed-time
or real-controller tests. An idle manager stays disconnected until another command
is queued. No immediate reconnect is added.

**Open security gap for follow-up:** invalid numeric and negative lengths retain
the original terminal exception path in audit.9 and can still deny subsequent
commands on that manager. A separate parse/negative-size refinement is next.
The metadata fixture forces a cached failure; first-time access denial and exact
manager-class mismatch are checked in source only. Clean evidence follows below.

Legacy body-codec fixtures do not imply encrypted HTTP: headers and transport
remain plaintext. The ordinary failure callback checks zero premature closes.


## Clean evidence

Application source `82acf2c`, packager `12c3e4a`; repeated clean builds match
bytes, modes and inputs. JAR SHA-256: `14e210d66e8f9feb1c107e253c2363a76d177fd1e7a5ce6c8e63fd9fe96adfdb`.
Audit bundle digest: `fdeab0726ce2b0cf8bf6137a6a5c5212c4ee5b0d3763b122833b26ec9e7f0d43`.
Repeated runtime package digests:

- arm64: `8a15c91494b01454a4851bfbd0450b71e2feb1ebcbeee22143a57b1ce7612d2d`.
- x64: `f31d0e8d31ee2dfca8ea426341d1a5412f1619cb545a58c18fc2e70c9479ee43`.

[Independent preservation/linkage](recovery-clean-security.json),
[ordinary transport and security queue regressions](recovery-clean-transport.json),
[reviewed runtime/recovery fixtures](recovery-clean-runtime.json),
[XML quota regressions](recovery-clean-resources.json),
[static polling/CLI scope](recovery-clean-static-scope.json),
[source provenance](recovery-clean-provenance.json),
[package repetition/diagnostics](recovery-bundle-results.json) and
[installed/original integrity](recovery-final-integrity.json) remain separate evidence.
43 Python tests pass. Final reviewed fixtures at `50f1d7b` include 49 recovery output
lines on each architecture, ordinary logger parity and legacy body-codec guards.
All are offline and bounded; x64 uses Rosetta. Claude implementation review found
no defect and prompted explicit scope refinements. Malformed/negative lengths
are still an open security gap in this candidate and are next in scope.
