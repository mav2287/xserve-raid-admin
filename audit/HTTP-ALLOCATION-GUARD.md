# audit.7 response allocation ceiling

**Fact:** the original `HttpResponse.getBody` parses the exact `Content-Length`
header and eagerly allocates a ByteArrayOutputStream of that size before reading
the body. A valid positive integer can request an allocation approaching 2 GiB.
This bypasses the XML limits because it happens before XML parsing. The original
artifact is never exercised with these oversized declarations.

The user prioritized safe security closure. The candidate deliberately rejects
advertised response lengths above 16 MiB before buffer allocation. This ceiling
is a security policy, not a measured maximum controller response size. Real data
compatibility remains unresolved. Negative lengths retain the original superclass
failure; zero, ordinary lengths and the original read loop remain unchanged.

## Narrow implementation

The immutable original JAR remains unchanged. The hash-locked transformer appends
constant-pool entries for `compat.BoundedResponseBuffer`, a public subclass of
ByteArrayOutputStream, and changes only the two constant-pool operands in the
original getBody Code: `new` at offset 23 and constructor invocation at offset 28.
Code length, stack/locals, branches, legacy jsr/ret, exception table, subattributes,
original constant pool, other methods and class attributes remain byte-identical.
The subclass calls its size check before the superclass constructor; it overrides
no read/write behavior. The independent javap check compares the complete original
and candidate method text and accepts only those two operand differences.

Oversized rejection uses a fixed IllegalArgumentException. Claude identified that
a ProtocolException would enter the original generic IOException retry path and
could resend the transaction indefinitely. The selected exception instead enters
the existing terminal -102 path, as invalid numeric / negative lengths already do.
No command serialization, polling schedule or original retry delay is changed.

Full-JAR constant-pool scanning finds only AcpxConnection calling the response's
getInputStream, and HttpResponse itself calling getBody. AcpxConnection does not
catch IllegalArgumentException separately; its original finally handling remains.
The observed queue fixture establishes one terminal callback with retained context,
one send and no reconnect for the new oversized rejection.

## Validation and limits

- Boundary gate accepts -1, 0, 1, MAX-1 and MAX without ceiling-sized allocation;
  rejects MAX+1 and Integer.MAX_VALUE with the exact fixed exception.
- Candidate-only actual ACP send and original dispatch code receive empty bodies
  advertising 16777217 or 2147483647 bytes. Tests use a 64 MiB heap and 20-second
  subprocess bounds; they must reject before body reads/allocation, return -102,
  send once, and preserve one callback/context with zero reconnects.
- Original/candidate existing direct response cases, queue ordering and retry
  observations must match. Both pinned architectures and logging OFF/configured
  are covered. Original oversized behavior is established statically, not tested
  by allocating attacker-controlled sizes.
- The original JAR remains immutable and the installed app is not modified.

This closes the declared-body preallocation path only. At the ceiling, buffering,
copying and XML parsing still use several tens of MiB. The original response's
contentLength is assigned before rejection. Persistent connection outstanding state
and unread body handling after terminal rejection retain existing behavior and are
not qualified as recovery. Header line/count bounds, HTTP status/framing and shared
stream desynchronization remain separate open work. No controller, native GUI,
production volume, firmware transmission or full release qualification is implied.
