# Shared persistent-stream response association

This is offline characterization of G12, not a transport implementation change.
It compares the immutable Apple JAR with audit.10's candidate
`1526b6a5e6cb4be8515c74b8cf36271b405d19c7d9a4266378c5811785b9bdc1`.

## Facts measured

The real `AcpxConnection.send`, `HttpRequest`, `HttpConnection` request/response
flags, `HttpResponse` and plist parser execute. Only socket-facing methods are
replaced by a memory connection. One input source persists across two distinct
synthetic getStatus/getTime requests. Each reply is appended after that request
has been serialized, never preloaded before its request. Exactly one output and
one input acquisition per request are asserted.

Canonical replies produce the distinct first/second plist roots, leaving no bytes
pending. Missing length, lowercase length, duplicate last-zero length and declared
zero with extra bytes all return an empty first result. Exactly 117 bytes of that
first reply's synthetic body remain before the second reply is appended. The next
send parses that prior body as its reply, leaving all 113 legitimate second-reply
bytes unread. Identical outcomes occur for original and audit.10, on both pinned
Java 8 architectures. x64 executes through Rosetta on this arm64 host.

A synthetic chunked-only reply leaves 13 bytes after the first empty result.
The second send raises ProtocolException when interpreting the residual chunk
bytes as HTTP framing. Exception messages and raw requests are never emitted.
Exactly 118 bytes remain. requestOutstanding stays true; a third send attempt
raises IllegalStateException without acquiring output or sending anything.

All successful two-send cases assert zero source closes/disconnects before their
final cleanup. Disconnect makes the source terminal. Reads past scripted bytes
throw an immediate synthetic idle timeout, rather than artificial EOF success.
Independent source controls verify timeout and reads after close.
These controls characterize the fixture, not legacy timeout handling. Peer EOF
and response Connection: close are not modeled.

## Source facts and limits

Independent disassembly of the immutable JAR confirms that the buffered
`HttpResponse$HttpInputStream.close` clears requestOutstanding and does not close
the underlying source. `HttpMessage` uses case-sensitive HashMap lookup and
last-write replacement. `HttpRequest.send` sets requestSent after sendBody.
These agree with the fixture's measured zero close count and flags.

The source is bounded to 8192 bytes per reply and 16384 read calls, with a 64 MiB
heap and 20 second subprocess limit. OfflineGuard rejects sockets, subprocesses,
profile access, writes and exit. Reviewed legacy fixtures are its scope; it is
not a general hostile-code sandbox. No app entry point, controller, saved profile
or installed application is used. No controller commands are changed.

This establishes parser response association on one shared synthetic stream. It
does not qualify real TCP segmentation, timing, backoff, queue retries, discovery,
polling, controller firmware or authentication UI. A forged response body is a
synthetic framing probe, not evidence of authentication bypass.

## Security implication and open questions

**Inference:** missing and ambiguous framing can cause results to be associated
with the wrong command on a persistent connection. Treating these as successful
empty replies does not provide a safe recovery boundary. A narrowly scoped policy
must reject unframeable replies through the existing terminal security marker,
retire the connection and avoid replay of the failed command.

Lowercase Content-Length can instead be supported by canonicalizing only this
field. Duplicate Content-Length and unsupported Transfer-Encoding should be
rejected rather than guessed. Require an explicit length if this legacy parser
cannot otherwise delimit a reply. Preserve valid numeric parsing, canonical
responses, ACP error decoding and legitimate zero-length replies. These are
proposed rules pending the separate Claude framing design review, not implemented
or qualified by this characterization.

**Unresolved:** declared zero or too-small lengths with additional valid-looking
response bytes cannot be fully addressed by header rules alone. A nonblocking
available-byte check would have timing limitations. Connection policy changes
need separate compatibility evidence. Strict framing cannot authenticate the
peer, and the legacy HTTP protocol remains plaintext.

## Review and reproduction

Actual read-only Claude [design review](claude-review/SHARED-RESPONSE-DESIGN.txt)
identified required terminal close/timeout behavior, precise residual-byte checks,
CRLF framing, root-level role checks, original/candidate comparison and a chunked
case. The fixture incorporates these requirements.

The actual [implementation review](claude-review/SHARED-RESPONSE-IMPLEMENTATION.txt)
found no invalidating fixture flaw. Before acceptance it required clean committed
fixture provenance, exact expected output gating and required candidate identity.
All are incorporated. Additional tightening asserts chunked residual counts,
observes the blocked follow-on attempt and distinguishes source controls from
unmeasured peer EOF/Connection: close behavior.

Run `tools/check_shared_stream.py --jdk <locked compiler home> --candidate-sha256
1526b6a5e6cb4be8515c74b8cf36271b405d19c7d9a4266378c5811785b9bdc1 --runtime <pinned
arm64 Runtime.jdk root> --runtime <pinned x64 Runtime.jdk root> <audit.10 JAR>`.
The tool verifies original, compiler and runtime locks before/after, hashes fixture
and harness sources, records commit/dirty state and demands identical complete
observations. Candidate bytecode is unchanged by this work.
