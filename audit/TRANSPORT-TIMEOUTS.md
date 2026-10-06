# Transport timeout correction — original bytecode

Facts from the immutable original JAR, SHA-256
`5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449`:

- `AcpxMessageFactory()` and `(int)` initialize `defaultTimeout` to zero.
  Factory-golden rows at 0/123 explicitly set that value; they alone were not
  evidence of the product default.
- `HttpConnection.setTimeout(0)` maps zero to 30000 milliseconds; other values
  are passed to `Socket.setSoTimeout`. This bounds each blocking socket read
  when successfully installed, rather than an entire response or operation.
- `createSocket(int)` never reads its parameter. `new Socket(host, 80)` has no
  explicit application connect deadline. The earlier approximately five-second
  connection-timeout claim is disproved.
- `createSocket` catches and logs `SocketException` from its subsequent
  `setSoTimeout(this.timeout)`, then returns. If that setup fails on a new socket,
  the socket can retain its default unlimited read timeout while the cached
  field still says 30000. A later equal-value `setTimeout(0)` returns early.
  This is a source-supported possible path, not an observed real-socket failure.
- No write or whole-operation deadline is established by these methods.
  Repeated reads can extend the response duration beyond thirty seconds.

The archived selected disassembly contains complete methods and an identity
index; the full original class hashes are recorded alongside it. Inspection was
read-only. No sockets, controller commands, credentials, app launch or production
volumes were involved. Runtime timing and native UI behavior remain unqualified.

Claude reviewed the source in `SYNC-INTERRUPTION-SOURCE-FOLLOWUP`. Its suggestions
about future interruption handling are not implemented or qualified here. Its
references to older SyncSender/Manager behavior are superseded by audit.17's
pre-enqueue guard and audit.18's terminal published connection failures; those
remarks are not evidence that the current candidate still has those old paths.
