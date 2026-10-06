# G10 request-factory and enqueue-state characterization

This step changes no application bytes. It qualifies object construction,
body-only serialization and bounded enqueue state, not controller functions or
an IO retry classifier. All arguments are synthetic. No worker, socket, firmware
transmission, profile, full GUI/CLI or production volume is exercised.

## Coverage and facts

The immutable original contains 59 instance factory overloads returning
RequestMessage. [Signature catalog](request-factory-signatures.json) pins all 59.
The fixture invokes 58 at factory timeout 0 and 123, producing 116 rows. The
filename-based newUpdateFirmwareRequest is explicitly excluded because it opens
a file. Its stream counterpart remains separately characterized by the existing
memory-only firmware fixture; this sweep does not qualify firmware operations.

[Expected table](request-factory-expected.json) records class, path, command,
default target identity, connection flags, timeout state, body shape, parameter
keys, capped synthetic body size/digest and shared/copied/absent clone states.
Original and audit.13 produced that exact table on both pinned Java 8
architectures during development; clean qualification is recorded separately. Body digests detect serialization differences;
metadata presence alone is insufficient. Default target is null in every row;
real callers' target selection remains a separate audit.

Each timeout sweep contains:

| Body shape | Count | Plist clone | Parameter clone |
|---|---:|---|---|
| RPC | 25 | shared | shared |
| Command dictionary | 26 | copied | copied |
| Property array | 4 | copied | absent |
| Property dictionary | 2 | copied | absent |
| No-op | 1 | absent | absent |

All share the header map. Only newRestartSystemRequest sets shutdown; all restart
values are -1. The 26 command dictionaries add body timeout only when the factory
timeout is nonzero. Other shapes' body digests remain unchanged. RPC getCommand
equals its body method: the earlier hidden-method inference is disproved.
Property get/set and no-op commands are null, so command alone cannot classify them.

Six enqueue cases call actual postMessageAsync on constructor-bypassed managers
without starting a worker. They overwrite existing parameters and add parameters,
change a synthetic header, target and timeout after posting. RPC body changes reach
the queued clone; command/property body changes do not. Headers remain shared;
target and timeout fields are snapshots. Separate property data tests isolate Date
and byte[] mutations. A caller-owned LUN-mask list remains shared through RPC.
This is deterministic sequential mutation, not concurrent stress or mutation
between actual send/retry attempts.

## Source refinements and limits

Full bytecode confirms deepCopy recursively copies ArrayList/Map, clones Date and
byte[], and shares supported immutable leaves. Copied maps become HashMap; arbitrary
ordered-map serialization need not remain byte-identical. The fixture uses HashMap.
isValidElement accepts Float and general List types that deepCopy/writeXMLLevel do
not support. This is a source API mismatch, not a demonstrated GUI failure.
The TestEmail constructor only builds maps; synthetic credentials are left null.
The enqueue method only clones/adds/notifies and does not start the worker.

One argument set per overload does not cover conditional/default schemas: null
dates/arrays, optional stripe sizes, operation flags, truncation and range errors
remain separate cases. Some null arguments would introduce current time and make
digests nondeterministic. HashMap order is pinned-runtime evidence, not portability
proof. x64 uses Rosetta; physical Intel and real controller semantics are unqualified.
Bodies are capped at 65536 bytes, heap at 64 MiB, processes at 20 seconds; logging
is disabled and captured application stdout/stderr must remain empty. The offline
guard must report zero actions. No header/body values or request toString are emitted.

## Qualification and actual review

[Claude design review](claude-review/REQUEST-CLASSIFICATION-CHARACTERIZATION-DESIGN.txt)
corrected RPC/clone assumptions and required a 58+1 gate before a broader policy.
[Implementation review](claude-review/REQUEST-FACTORY-IMPLEMENTATION.txt) checked
all 116 initial rows and required strict qualification gates and tri-state clone
labels. Those fixes are incorporated: clean tree, both pinned runtimes, candidate
bound to the current expected-build digest and distinct from the original, pure
expected-table comparisons with negative tests, resolved/exclusive bootstrap path,
development-only bootstrap labels. The focused review added explicit assertions
that the overwritten parameters already exist.

[Focused review](claude-review/REQUEST-FACTORY-REVIEW-FOLLOWUP.txt) accepted the
116 rows and six cases on content. Bootstrap-4 provenance was checked against its
recorded Java source hash by reversing only the two added overwrite assertions;
bootstrap-5 reran the updated fixture and exactly matched the reviewed table.
Both remain development observations, not clean qualification. Duplicate JSON
keys, numeric substitutes for sharing booleans, and missing existing overwrite
keys now fail closed. Catalog/table parsing binds the parsed bytes to recorded
hashes; qualification also rechecks the commit and clean tree at completion.
74 Python tests pass. [Final gate review](claude-review/REQUEST-FACTORY-FINAL-GATES.txt)
found no code blocker and required bootstrap completion before committing. That
completion and four-observation equality were checked after the review, before
commit. Clean qualification follows the committed fixture.
Caller/wrapper/control-flow, dual-target writes, chained UI operations and direct
CLI outcomes remain open. Shared RPC bodies and headers mean measured identical
replay bytes cannot be generalized. No retry policy changes are made here.
