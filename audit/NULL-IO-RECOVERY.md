# audit.13 terminal null-message IO recovery

The original dispatch handler dereferences IOException.getMessage() before its
retry decision. A null message kills the worker, loses the current transaction
without a callback, and leaves later asynchronous posts stranded. This was measured
with bounded memory connections on both pinned runtimes; a real socket origin was
not established. This change replaces that worker death with a terminal failure.

## Narrow compatibility change

The immutable Manager class remains hash-pinned and version 47. Original run
PC339..343 becomes a same-length goto_w to appended PC553. The 25-byte block
evaluates getMessage once, duplicates its result, and resumes original PC344
with the same String when non-null. When null, it replaces only local exception 5
with a fresh exact security marker and jumps to the existing report hook at 464.
The normal -102 response and callback sequence remain original.

The marker says `Response transport failed; outcome is unconfirmed`. It carries
no original exception/cause; a null-message exception can still contain unsafe
peer text in its cause. Recovery closes the old connection and sets connected=false.
The failed command is not requeued. A distinct subsequent request uses the original
reconnect path. **The controller may have acted; this failure is not evidence that
the command was not applied.**

All non-null IO classification, PropertyListException-prefix handling, ordinary
requeue behavior, polling/retry constants, original byte offsets and stack/local
limits 6/9 remain unchanged. run code length grows 553 to 578. All twelve original
handler rows and the empty sub-attribute table are pinned byte-for-byte. The actual
table has twelve rows; Claude's preliminary nine-row wording was corrected using
the complete Code tail. No direct AcpxConnection.send contract is changed here.

## Bounded evidence

On both pinned runtimes, injected null IOException, EOFException, and a null
exception with a synthetic peer-text cause produce a fixed marker, no cause,
one failed send and one callback. A distinct next getTime succeeds on a fresh
injected source. The daemon worker stays operational until explicit fixture shutdown.
A synchronous caller gets the fixed IOException without a cause after one send.

Changing-message subclasses test one evaluation at the decision: null then text
fails terminally; text then null retains the original identical-command retry.
These call-count tests disable logging; they are not a global claim that log
rendering never calls an exception's message method.

Recovery tests cover null EOF with a synthetic cause under close IO/runtime
failure, a throwing logger, and missing reflection metadata. Rendered logger and
throwable text contain no sentinel. Metadata failure shuts the manager down;
queued terminal callbacks finish without another send, then original worker exit
closes the old source. Immediate retirement is claimed only for normal metadata.

Independent javap checks exact entry/appended instructions, unchanged non-null
classification, stack/local limits and original exception table. Mutation tests
reject every changed trampoline byte and linkage/metadata changes. A bounded
temporary JAR copy with a goto into an instruction operand must raise VerifyError
on the application classpath under -Xverify:all. The real artifact is never mutated.
Explicit --null-io-policy requires fixed candidate results; original controls still
show worker death. Prior ordinary IO, XML and framing regressions remain required.

## Limits and actual consultation

[Claude design consultation](claude-review/NULL-IO-DESIGN.txt) found no blocker,
verified stack/branch math, recommended cause removal, changing-message/EOF/sync
tests, exact tail preservation and a verifier negative control. These are incorporated.
Implementation review and clean evidence follow separately.

This fixes only dispatch of a null-message IOException. Other IO failures can
still replay mutations. Throwing getMessage overrides and fatal VM/linkage errors
while creating the marker can still escape the worker. Repeated failing polls may
each reconnect; no real reconnect/backoff or polling rate is measured. Direct CLI
IO behavior, full GUI flow, real sockets, sleep/wake, controller outcomes, physical
Intel and production-volume behavior remain unqualified. x64 runs under Rosetta.
No controller, profile, installed application or production volume is exercised.
Legacy HTTP remains plaintext; this is neither encryption nor peer authentication.

[Claude implementation review](claude-review/NULL-IO-IMPLEMENTATION.txt) found no
bytecode/helper blocker and required correcting stale record scopes, method-specific
preservation labels, exact recovery vectors and fresh source hashes. These are
incorporated. Additional gates pin close counts, nonthrowing logger capture,
fixed/legacy null modes, Code lengths and handler rows. The review's suggested
logger location was refined using the existing FQCN boundary: recorded location
remains CommunicationsManager.run, rather than the compatibility helper. Original
null MalformedInputException uses its earlier separate handler and is unchanged;
IOException(cause) normally has a nonnull message and retains ordinary retry.

The tightened logger check exposed a fixture expectation error: the original
invalid-address reconnect seam logs a second fixed synthetic event. The final
gate requires exactly one marker event at CommunicationsManager.run plus exactly
one original reconnect event, and checks both rendered messages/throwables for
sentinels. This does not alter application logging or weaken cause containment.

Claude's [focused follow-up](claude-review/NULL-IO-REVIEW-FOLLOWUP.txt) confirms
no blocker: the exact two-event logger gate, source close counts, original twelve
handlers, 141-line recovery and six fixed null variants are consistent. Optional
exact marker-class checks are added. Logger capture is not combined with close
failure or metadata-stop variants; their cleanup signal event counts are unqualified.

## Clean artifact record

Clean application source `f2ec1cf`, fixture/package anchor `a3a1687`. Two app
builds produce JAR SHA-256
`3f39352faf7b0fe0b117d04af0b2455efd81b4511fc522617743f7d169793175`
and audit bundle digest
`919d8ded52a986c7defc0d08257ca1318b1c4914bd471e022d5210d7559a4fe4`.
Repeated arm64 bundle digest:
`5a83905a232cee9b83504a637b9fce9aeac9be552542dec1c9092ab297a752ef`;
x64: `55ec1febbc3fdd4a6e03c6af7baf74c1a277ea8da07095fa9d7bebefc588ee6d`.
Vendor runtime signatures remain verified; exactly 25 JAR entries differ.

Clean [security](null-io-clean-security.json), [transport](null-io-clean-transport.json),
[runtime](null-io-clean-runtime.json), [XML resources](null-io-clean-resources.json),
[shared-stream](null-io-clean-shared.json) and [packages](null-io-bundle-results.json)
qualify this artifact locally. [Integrity](null-io-final-integrity.json) confirms
committed tool/fixture hashes, 64 passing Python tests, immutable original and
installed reference contents/modes unchanged. Local diagnostics inspect
[arm64](null-io-diagnostic-arm64.json) and [x64](null-io-diagnostic-x64.json) packages
without launching Java or reading preferences. Java 11 was not rerun.
