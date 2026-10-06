# audit.12 terminal malformed-header rejection

The user authorized security closure. Colonless headers and headers whose colon
is the first character now raise a fixed terminal security marker rather than
an IOException containing the peer's line. The dispatch path returns -102 once
without replaying the affected command. **The controller may already have applied
that command; -102 does not mean it was not applied.**

## Exact change

The immutable original HttpResponse hash remains pinned. Only parseHeaders
PC130..156 is replaced: a static invalidHeader() call, athrow, and 23 NOPs.
The helper returns a fresh exact UntrustedResponseException with fixed message
`Response header is invalid`, no arguments and no cause. All original offsets,
branch targets, stack/local limits, class version 47 and Code metadata remain.
Old constant-pool entries are retained but no patched instruction uses the old
ProtocolException/message constructor. Existing audit.6–11 edits are preserved.

The marker uses audit.9's send retirement and dispatch recovery paths. Cleanup
failures cannot turn this rejection into an automatic resend. Controller command
serialization, successful replies, polling and ordinary IO retry timing are unchanged.

## Evidence and deliberate policy difference

Both pinned Java 8 runtimes pass direct-send, queued read and synthetic set-time
rejection tests: fixed message, no cause, one send; queued callers receive exactly
one -102 callback with retained context. Original controls still show peer text in
the ProtocolException and two identical sends after a malformed response. A
synchronous candidate caller receives a fixed IOException, no peer text or cause,
and one send. Fixture worker shutdown is explicit and bounded.

Recovery adds both colonless and empty-name lines after a valid Content-Length.
All 15 security cases retire the old source and allow a distinct next request on
a fresh injected connection. Malformed-header controls also cover shutdown/restart
flags, close IO/runtime failure, legacy body codec presence and a throwing logger.
Rendered logger/throwable text is checked for synthetic sentinels without emitting it.

The 174762 short header/EOF cases still match original parsing and byte consumption.
Only the exact fixed marker is normalized to the original ProtocolException label
for that parser oracle; unknown unchecked failures are rejected. Independent javap
comparison checks every remaining instruction and all original branch targets,
the new terminal block, fresh-marker helper and unmodified Code metadata.
Python mutation tests reject changes throughout the block, padding, linkage and
neighboring Code data. --invalid-header-policy explicitly requires candidate
terminal results, so method self-detection cannot silently accept legacy behavior.

[Reference inventory](direct-send-reference-inventory.json) scans constant-pool
references in all 2844 immutable classes. HttpResponse construction is referenced
only by HttpConnection. Direct ACP send references occur in Manager and two CLI
handlers. Their local send sites do not catch IOException or RuntimeException.
This is static evidence, not reflection reachability or CLI entry/exit testing.
Direct callers now receive an unchecked fixed marker, consistent with prior
security restrictions; full CLI exit behavior remains unqualified.

## Limits

This is one rejection boundary, not complete protocol security. Whitespace before
a colon can still yield an empty trimmed name through the original valid-header
branch. Status interpretation, wrong single lengths, trailing bytes, ordinary
lost-response mutation replay and null-message IO worker death remain open.
Fatal VM/linkage errors during exception creation can still escape the worker.
No real sockets, controller, profiles, installed app, production volume or full
GUI/CLI entry point are exercised. x64 runs under Rosetta; physical Intel and
controller firmware compatibility remain unqualified. Legacy HTTP is plaintext.

## Actual review and reproduction

[Claude design review](claude-review/MALFORMED-HEADER-DESIGN.txt) found no blocker
and identified explicit policy gates, the empty-name case, fixed helper linkage,
sync-caller behavior, flag/close/codec/logger regressions and CLI limits.
These are implemented or explicitly scoped above. Application builds remain
offline, deterministic and separate from /Applications. Clean artifacts and
review disposition are recorded after the implementation commit.

Claude's [implementation review](claude-review/MALFORMED-HEADER-IMPLEMENTATION.txt)
found no blocker. Its narrow fixes are incorporated: the header corpus rejects
legacy ProtocolException when the fixed method exists; architecture policy
requires the header corpus; IO comparison unit tests require explicit fixed/legacy
vectors; metadata describes sync/CLI/outcome limits. Colonless-only flag/codec/
logger variants are distinguished from empty-name pair/direct coverage. Clean
qualification reruns all prior candidate-only transport restrictions.

## Clean artifact record

Clean application source `53e902e`, fixture/package anchor `e22e837`. Two app
builds have identical JAR SHA-256
`744efeba288e16aac97cf5bd53b2b87300fe7469bda59e16533df8e20fd63f6b`
and audit bundle digest
`27f28438190bc844c345463a2b8bb5d73efc084858e670f7e30120d44234b2ed`.
Both repeated runtime packages match, including modes and vendor signatures.
Arm64 bundle: `20f197766d5a582bbbd93dcc30fccdaded59a2ed5ce51ae593e61e696f32f56e`.
x64 bundle: `808f6f7729f97613d62d5ad24b250d893a997f8ae49f08067cd046ca8679163c`.
Exactly 25 JAR entries differ from the immutable original.

Clean [security](invalid-header-clean-security.json),
[transport](invalid-header-clean-transport.json),
[runtime](invalid-header-clean-runtime.json),
[XML resources](invalid-header-clean-resources.json),
[shared stream](invalid-header-clean-shared.json) and
[packages](invalid-header-bundle-results.json) qualify this artifact locally.
[Integrity](invalid-header-final-integrity.json) confirms fixture/tool hashes,
60 passing Python tests, immutable original digest and installed reference
contents/modes unchanged. Java 11 was not rerun for this milestone.
