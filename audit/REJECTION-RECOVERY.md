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
unchanged. Ordinary errors log through the same category and original caller
location. Only the exact marker also sets connected=false under the manager lock
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
transport, close IO/runtime failures, synthetic shutdown/restart *connection flags*
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
are not implied. Clean evidence will be recorded after implementation review.
