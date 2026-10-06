# audit.6 XML parser security compatibility layer

## Decision and scope

The user explicitly prioritized safely closing the XML security gap on 2026-10-05.
The immutable Apple JAR is unchanged. Only the Code attribute of the original
protected static `PropertyListUtilities.getParser()` method is redirected to
`compat.SafePlistParser.create()`. Original class version, access flags, non-Code
method attributes, fields and other methods remain. The build gates exact original
and transformed hashes and independently checks the bytecode with javap.

**Fact:** the original bundled Xerces provider ignores the tested JAXP resource
controls. The new helper selects the bootstrap JDK provider explicitly, enables
validation and secure processing, disables XInclude, denies external DTD/schema
access, and sets and reads back nine quotas. Ambient provider and quota settings
cannot select a different provider or disable these quotas. Configuration failure
has no permissive fallback. The original plist Handler, local embedded Apple DTD,
serializer and controller code remain. The validation provider is replaced.

The policy deliberately tightens the measured JDK defaults: custom entity expansion
count 4096, total entity size 1048576, general entity size 262144 / parameter entity size 65536,
and entity replacements 100000. Attribute, occurrence and name limits retain the
pinned defaults. These are security bounds, not observed maximum controller sizes. Depth is explicitly 32: the original accepts
30 nested plist containers with a leaf, then fails at 31 because of a validator
array-bounds defect. The candidate reports an ordinary depth-limit rejection.
This is an intentional change in failure diagnostics. External resources and
excessive entity expansion are intentional security rejections.

## Validation

Development builds are labeled dirty and are not release qualification. The source
commit and clean evidence are recorded separately after the implementation commit.

- Original/candidate, Reader/InputStream, both pinned architectures and default /
  lowered ambient properties: canonical hashes for accepted cases; exact original
  array-bounds versus candidate depth-limit categories for arrays, dicts, mixed
  containers and empty terminal containers.
- Candidate policy: explicit readback, fresh instances, 70,000 predefined/numeric
  references accepted, 4,000 internal references accepted, 4,100 rejected with
  JAXP00010001; 1,040,384 expanded characters accepted, bounded total-size overflow
  rejected with JAXP00010004, and a 262,145-character general entity and 65,537-character parameter entity rejected
  with JAXP00010003, with small parameter entities accepted, and concurrent small parsing. Default, lowered and
  hostile ambient settings produce the same policy result.
- Additional accepted-value differential: text around 4K/8K/16K boundaries, empty
  values, integer bounds, floating-point values, date, comments/PI, duplicate keys,
  nested containers, and roughly 48 KiB of base64 data with/without line wrapping, sibling containers
  near the depth boundary, PUBLIC DTD identifiers and XML encoding declarations
  for UTF-8. The original InputStream constructor explicitly uses UTF-8 before
  handing the Reader to SAX; a UTF-16 byte fixture fails on both original and
  candidate. Non-UTF-8 byte autodetection is not introduced by this change.
  Parse failure never counts as accepted-value parity.
- Queued malformed, depth-limited, entity-limited and external-resource responses
  retain result -103, one callback/context and no requeue; credential-safe logging
  remains bounded. Existing protocol/queue fixtures remain unchanged.
- Offline guards prohibit network, writes, execution, app preference reads and
  termination. The application entry point is never launched.

## Limits and unresolved questions

Fixtures use small bounded documents, a 64 MiB heap / 1 MiB stack for resource
probes and subprocess timeouts. They do not search for an exhaustion threshold.
They do not establish real controller response sizes or all parser-provider
semantics. Java 11 observations exercise the public bootstrap-factory branch;
the release runtime remains pinned Java 8. x64 execution here uses Rosetta rather
than a physical Intel host.

Unchecked VM/linkage failures still fail closed; recovery from a damaged JVM is
not qualified. The separate `com.chaotic.PropertyList` legacy implementation is
not redirected. Its confirmed static caller is `com.chaotic.Preferences`; active
XSR preferences use `com.apple.util.prefs.Preferences`. Reachability outside the
active path remains under audit. HTTP body allocation/framing, production hardware,
native UI and release signing remain separate open work. This layer is not a claim
that the application is fully secure or operational. Legacy controller HTTP is
unencrypted.

Claude follow-up identified an excessive inherited 50 MB total entity allowance.
It was tightened before finalizing the candidate; earlier audit.6 hashes are
intermediate artifacts, not the final security policy. See the review disposition.

Additional independent policy probes cover near-boundary accepted general and
parameter entities and rejection above their respective bounds; entity replacement
accepts 40000 nodes and rejects a bounded 104000-node expansion, under count and
total-size quotas, with JAXP00010007. Hostile flags cover every tightened quota.
