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
the unchanged parseHeaders on a wrapped Unsafe shell and unchanged readLine
inside a test-side loop on an unwrapped shell for every case. Claude identified this original test blind spot; it was
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

## Clean evidence

Application source `07d7551`, packager `efa03da`; each build/package starts clean.
Two application builds match bytes, modes and inputs. Candidate JAR SHA-256:
`8e48539c1b2b4414b0ea58cf4a9d39e83f9d3a1fa819a92d54d2f29525a210fa`.
Audit bundle digest: `80bf2ccc688ed83446c579b46f71af814cf40d3ce63a46b3cafb7f3c7cd251a9`.
Repeated runtime bundle digests:

- arm64: `8c45aac36620f76cd695463bb82efcfdae2a4ab295389c0a59cc64bf24afb536`.
- x64: `35546eef4c8a023a7fabab38cfeadae3b66724a262094cf7241d8390c034c546`.

[Independent bytecode/security checks](header-clean-security.json),
[queue and transport fixtures](header-clean-transport.json),
[header corpus and runtime regressions](header-clean-runtime.json),
[XML quota regressions](header-clean-resources.json),
[clean source provenance](header-clean-provenance.json),
[repeated package verification](header-bundle-results.json) and
[installed/original integrity](header-final-integrity.json) record their scopes.
41 Python tests pass after follow-up verifier hardening. These results qualify bounded offline behavior only.

Claude [follow-up review](claude-review/HTTP-HEADER-FOLLOWUP.txt) found no guard
defect and prompted a strict Code-line allowlist, constant checks and valid
Methodref target mutation tests. Long noncanonical line-ending boundary tests
remain unmeasured; the exhaustive short corpus qualifies automaton tracking.
