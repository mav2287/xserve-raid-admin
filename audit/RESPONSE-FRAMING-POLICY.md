# audit.11 explicit response framing

This security restriction addresses the ambiguous-framing subset of G12. It is
not complete response association or operational qualification. The user
explicitly authorized safe security closure; normal controller commands, polling
and retry constants remain unchanged. The original JAR stays immutable.

## Enforced boundary

`compat.ResponseFraming` recognizes Content-Length and Transfer-Encoding using
ASCII case folding independent of default locale. One Content-Length field is
stored under the original canonical key. Any second length, including identical
or differently cased duplicates, raises a fixed terminal security marker. Any
Transfer-Encoding, including identity, is rejected because the legacy reader
does not implement transfer encodings. Missing length is rejected before body
allocation. Valid numeric conversion still delegates to Integer.parseInt through
audit.10's bounded helper. Valid zero-length replies still return an empty plist.

Other headers delegate unchanged. The original parser still trims header names
and values and handles Connection: close itself. No new entity, command,
authentication or status interpretation is introduced.

## Narrow immutable-class edits

The hash-locked HttpResponse transform adds two same-length instruction changes:

- `getBody` offset 5: original virtual getHeaderField becomes static
  `ResponseFraming.lengthHeader(HttpResponse,String)String`.
- `parseHeaders` offset 93: original virtual setHeaderField becomes static
  `ResponseFraming.setHeader(HttpResponse,String,String)V`.

Both use exactly the existing stack operands. All other original instructions,
offsets, handlers, jsr/ret subroutines and Code attributes are retained, alongside
the previously reviewed audit.6–10 edits. Class version 47 remains unchanged.
Transform checks pin original windows, owners, descriptors and lookup literal;
preservation masks allow only the exact new opcodes/operands. Independent javap
comparison verifies four changed getBody instructions in total, one changed
parseHeaders instruction and the earlier constructor wrapper insertion.

Public get/set methods in HttpMessage were verified by immutable-JAR disassembly.
The header HashMap starts empty. A full immutable-JAR constant-pool reference scan
found HttpConnection.getResponse and HttpResponse.getInputStream references only
in AcpxConnection; HttpResponse itself also acquires the transport input. This
scan establishes reference locations, not an inventory of reflective callers.

The rejection sites lie inside audit.9's exact-marker send handler. They retire
the connection without running a cleanup path that could mask rejection and
resend the command. Dispatch returns -102 once and preserves callback context.
The next distinct queued request uses the original reconnect path.

## Facts from bounded fixtures

On both pinned Java 8 architectures, the shared-source fixture accepts canonical,
single lowercase, uppercase under Turkish locale, and zero-length replies. Each
follow-on response is associated with its distinct request and leaves no bytes
pending. A Connection: close reply retains the original one-source-close result
and cleared requestOutstanding flag; no second socket operation is attempted.

Missing length, identical duplicates, mixed-case duplicates, chunked encoding
and uppercase Transfer-Encoding under Turkish locale reject after exactly one
send, with one close, a null ACP connection, a fixed message and no cause. No raw
headers, bodies, requests or exception messages are emitted.

The dispatch recovery fixture extends the previous eight security cases with
five framing cases. For all 13, the failed getStatus is never replayed, a distinct
getTime succeeds through a fresh injected memory connection, and callback
contexts remain intact. Persistent/nonpersistent and injected close IO/runtime
failure variants pass. Existing logger failure/metadata and connection-flag tests
remain scoped to their earlier cases; they are not new framing coverage.

Ordinary transport comparisons allow exactly seven explicit framing output
differences. Missing/duplicate/chunked cases are rejected, lowercase now parses
its actual plist rather than reporting empty success. Every remaining ordinary
response, ACP error, request formatting and injected IO-retry result must match.
Header boundary controls now include an explicit zero length on both original
and candidate, counting it among their 128 fields. The 174762 short constructor
and EOF cases retain identical outcomes and independently checked counters.

Fixtures are headless, bounded and guarded. No real sockets, application entry
point, saved profile, controller or installed bundle is exercised. x64 uses
Rosetta here, not physical Intel. Real TCP timing and real reconnect/polling
behavior remain unqualified.

## Compatibility gate and unresolved risks

**Unresolved compatibility:** no existing controller capture establishes that
every supported firmware supplies exactly one length even on empty/error replies.
Missing lengths and duplicate lengths previously accepted as empty/success are
now intentional security rejections. This restriction is documented and must be
qualified before a release is called fully operational.

**Measured remaining gap:** a single declared-zero length with extra synthetic
response bytes still causes prior-body association on the shared source. This
case is retained in the policy regression, rather than hidden by the new rules.
Too-small lengths are also an unresolved association risk. An available-byte
heuristic cannot prove absence of delayed bytes; closing every empty response
would alter connection/polling behavior without fully solving that risk. Neither
is part of this change.

HTTP status remains ignored by the original parser. Ordinary malformed-header
ProtocolException/IO failures retain legacy handling and may leave stale state
or cause ambiguous command retries (G10). Strict headers neither authenticate a
controller nor encrypt legacy HTTP. These are separate unresolved boundaries.
Original readLine still ends a line on its second CR/LF byte, even if characters
intervene; the new policy acts on those same parsed fields. Direct CLI callers
may choose their own retry behavior. No whole-program no-replay claim is made:
the measured guarantees apply to actual send retirement and dispatch fixtures.

## Review and reproduction

Actual read-only Claude [design review](claude-review/FRAMING-POLICY-DESIGN.txt)
recommended these two hooks, direct marker throws, locale-independent matching,
zero/close compatibility controls and explicit residual-byte limitations.
The actual [implementation review](claude-review/FRAMING-POLICY-IMPLEMENTATION.txt)
found no patch correctness blocker. Its acceptance fixes are incorporated:
architecture recovery now explicitly requires --framing-policy, evidence wording
distinguishes static and runtime qualification, independent disassembly checks the
original setHeaderField target, and clean artifacts are regenerated after commit.
Recommended fixes also pin the helper's ASCII-only/fixed-message boundary and
add the duplicate-last-zero shared-stream rejection. Locale wording distinguishes
Content-Length casing from Transfer-Encoding's Turkish dotted-I hazard.

Use the locked compiler with baseline.py, then verify_builds.py for two distinct
outputs. check_security.py independently verifies preservation. check_transport.py
requires --length-policy --framing-policy, and check_shared_stream.py requires
--framing-policy plus the exact candidate SHA. check_architectures.py runs folder,
menu, vendor-extension, security, logging, parser, header and recovery checks on
both pinned runtimes. check_xml_resources.py verifies XML resource restrictions.
None of these commands installs, launches the full app, signs or contacts RAID.
