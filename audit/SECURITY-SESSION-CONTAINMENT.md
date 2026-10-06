# audit.14: stop a rejected communication session before dependent writes

## Scope and reason

The user authorized closing security holes safely. The caller audit disproved
that a terminal failure plus successful next read demonstrates safe operation
sequencing: several original UI workflows pre-enqueue dependent writes without
handlers. [Caller evidence](REQUEST-OPERATION-SEQUENCES.md) and
[actual Claude design review](claude-review/SECURITY-SESSION-CONTAINMENT-DESIGN.txt)
require containment before a broad retry policy can be attempted.

For the exact UntrustedResponseException class only, RejectionRecovery.report
now calls the original CommunicationsManager.shutdown before logging, transport
retirement and callbacks. This stops a local Java dispatch session; it sends no
controller shutdown command. The original stopped-worker path drains queued
transactions with -102/CommShutdownException without reconnecting or sending.
The failed request retains its fixed, cause-free rejection. Its controller outcome
is unconfirmed. This deliberate security restriction affects framing/length/header
markers and null-message IO; valid operations and ordinary nonnull IO retry code,
command bytes, target selection and polling/backoff constants remain unchanged.

A stopped manager cannot be revived by RaidSystem.connect. Establishing another
manager requires a new RaidSystem; the exact UI recovery procedure is not yet
qualified. Do not label this as automatic or ordinary manual reconnect.

## Evidence and limitations

The development candidate has JAR SHA256
fe14078408670f4fd28ca53b2dccc48366338e37fbd5bda4ab01d7eee3761b4c.
Only RejectionRecovery.class differs from audit.13 inside the JAR. The original
class operand patches are unchanged. The version advances to audit.14.
A development gate initially omitted javap's rendered `= true` field initializer;
its pattern was corrected and eight negative prefix mutations now pass unit gates.
The successful independent security fixture checks the candidate bytecode.
An independent javap gate requires the exact marker branch and shutdown before
security-path logging, while preserving ordinary exception reporting.

Both pinned runtime architectures passed 143 recovery lines each: all 15 security
violations stop the session and block a queued synthetic restart after a synthetic
set-time request. Close IO/runtime failures, throwing/nonthrowing loggers, metadata
failure and original logger-location behavior are retained in the fixtures. Two
throwing-callback cases prove no later sends; remaining callbacks may be stranded.
The transport fixture also tests three null-IO variants, a late async mutation
post and stopped-before-post sync rejection. All requests use capped fixtures and
memory transport; zero guarded operations, no controller contact or production
volume test. x64 runs under Rosetta, not physical Intel.

A fixture close-count assumption initially failed: successful AcpxConnection.close
clears its inner connection, so a subsequent close does not re-close the memory
source; a throwing close retains it and can be attempted again. The expectation
was corrected from source and runtime evidence; application code was unchanged.
81 Python tests pass with the development audit.14 artifact anchor. The anchor is
not clean qualification. Clean builds, committed-source regression records and
[Actual implementation review](claude-review/SECURITY-SESSION-CONTAINMENT-IMPLEMENTATION.txt)
found no code blocker and required regenerated records and explicit historical
supersession. Older development records are not cited as qualification; only
committed-source reruns will be accepted. Its recommended handler-table exclusion,
stop-before-logger assertion and ordinary-path non-stop assertion are implemented.
If shutdown throws, the worker can escape before logging/retirement; no further
worker sends occur, but cleanup/callback completion is not guaranteed.
Clean committed-source evidence follows before acceptance.

**Open:** ordinary nonnull IO can still replay writes. Async posts after worker
exit remain queued without callbacks. Concurrent sync post vs worker exit can
still wait indefinitely; queued and stopped-before-post cases alone are qualified.
Throwing callbacks may strand other callbacks. Direct CLI send behavior and whole
GUI workflows remain unqualified. No packet/hardware semantics are inferred from
fixture launch or synthetic success. This is containment of the demonstrated
security-marker sequencing regression, not completion of the broader replay fix.


[Final Claude follow-up](claude-review/SECURITY-SESSION-CONTAINMENT-FOLLOWUP.txt)
found no blocker to committing the code/matrix and qualifying clean builds.
Current build input hashes were checked against the development anchor before
commit; no development observation is committed as clean evidence.


## Clean qualification

Application commit `028165a` and fixture/package anchor `e8a83ad` were clean.
Two baseline builds matched JAR, files and modes. The reviewed JAR digest remains
fe14078408670f4fd28ca53b2dccc48366338e37fbd5bda4ab01d7eee3761b4c.
The audit bundle tree is 64627bc03d2d9f0d77730207c08b5475bd671d063182ae6e0a36f988153a1709.

- [Independent bytecode/XML/security check](session-containment-clean-security.json)
- [Full transport/security-policy regression](session-containment-clean-transport.json)
- [Both runtime architecture/API/parser/header/recovery regressions](session-containment-clean-runtime.json)
- [Bounded parser resource regressions](session-containment-clean-resources.json)
- [Shared-stream association regression](session-containment-clean-shared.json)
- [Strict 116-row/six-case factory regression](session-containment-clean-factory.json)

Both packaged architectures reproduced files, file modes and directory modes:
aarch64 tree 304e4d754ad037a9054c6c2d036b887fc06ade4385caef852b56a8c577aa716b;
x64 tree 49e966a87bc553183877fd661dc229630c5f0e912271dd78dfb72c7af02bc1c8.
[Package records](session-containment-bundle-results.json) retain vendor signature
verification before/after byte-only copying. Application signing/notarization was
not performed. Allowlisted diagnostics matched both manifests and reviewed output,
and the [tooling-only version-label correction](DIAGNOSTIC-VERSION-LABELS.md)
now reports audit.14 with explicit artifact-version agreement.
[Integrity record](session-containment-final-integrity.json) verifies source hashes,
81 Python tests, immutable original JAR and installed application bytes/modes.
No controller contact, installed-app modification, firmware transmission or
production-volume test occurred. All earlier development observations remain
excluded from clean qualification. Broader IO replay and operational acceptance
remain open.
