# audit.8 bounded response headers

**Fact:** the original HttpResponse constructor reads lines into an unbounded
StringBuffer and accepts an unbounded number of fields before getBody or XML
parsing. The previous body and XML quotas do not bound this earlier stage.

The user explicitly prioritized safe closure. The candidate applies a fresh
per-response budget: 65536 non-ending bytes per line, 128 header fields plus the
status line, and 1048576 total header bytes including endings. These are deliberate
security ceilings, not measured controller maxima. Actual controller compatibility
at these ceilings remains unresolved.

## Narrow implementation and preservation

The immutable original JAR is unchanged. A hash-locked transform inserts only a
three-byte invokestatic compat.BoundedHeaderStream.wrap immediately before the
original constructor stores its input stream at offset 36. The original 44-byte
Code becomes 47 bytes; stack/locals, the earlier branch, exception table, Code
subattributes, and original instruction bytes remain unchanged. The previously
approved getBody allocation operands are retained. All other HttpResponse methods
remain byte-identical. Independent javap instruction and attribute checks verify
both edits, and mutation tests reject changes in preserved prefix/suffix bytes.

The wrapper tracks the actual legacy readLine automaton: the second CR or LF ends
a line, even with intervening non-ending bytes; EOF finishes the current line;
an empty line after the status line ends headers. The unchanged parser still
makes its own syntax decisions. Blank line 130 is accepted after 128 fields;
the first non-ending byte of a 129th field is rejected. Once the parser reaches
body mode the wrapper stops counting; a subsequent response receives a new
wrapper. Null streams remain null. Closing delegates to the underlying stream.

Rejection throws a fixed IllegalArgumentException before any further reads;
subsequent wrapper reads reject without accessing the source. The original queue
maps this to terminal -102 with one callback/context and no resend. No controller
command serialization, polling interval or original retry delay is changed.

## Evidence and limits

The bounded corpus contains 174762 short sequences over CR, LF, a and colon,
both with a header terminator suffix and directly at EOF. Original and candidate
constructor outcomes, header maps and consumed positions match. Because short
inputs alone cannot expose a premature switch out of header counting, the
candidate also checks wrapper bytes, phase, line count and reset fields against
actual unchanged private parseHeaders/readLine invocations on isolated Unsafe
shells for every case. Claude identified this original test blind spot; it was
fixed before acceptance.

Both pinned runtime architectures cover exact line/count/byte acceptance,
body pass-through exceeding 1 MiB, two responses on a shared in-memory source
with fresh budgets, and rejection one byte/field over each limit. Rejection
fixtures check exact source consumption, sticky failure and close delegation.
Queue tests cover all three violations with logging disabled and configured.
The original is never supplied oversized header fixtures. Strict offline guards,
64 MiB heap, subprocess timeouts and synthetic inputs bound the tests.

**Confirmed open gap:** the two-command queue observation returns -102 for both
the rejected response and the next command, sends only the first command and
leaves outstanding true with zero reconnects. Cleanup/recovery remains separate
work; no claim of recovery or indefinite behavior is made. HTTP status handling,
framing ambiguity, live shared-socket synchronization, real controller data,
physical Intel, native UI and release qualification also remain open. x64 on this
Apple silicon host uses Rosetta. No hardware or production volume is contacted.

Claude reviewed the design and implementation using the actual read-only CLI.
The implementation review's line-count concern referred to an earlier snapshot;
the tested fresh-response case supplies the seventh common output line. Its
candidate-attribute checking concern was fixed in the independent verifier.
Clean-build and final evidence links will be added after the clean run.
