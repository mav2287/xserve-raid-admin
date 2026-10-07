# RaidSystem diagnostic credential redaction

Status: development fixture passes; integrated clean builds and regression
qualification are pending. The qualified audit25 artifacts and ledger remain
immutable. No installed application or controller is modified or contacted.

## Measured problem and minimal repair

**Fact:** original `com/apple/xsr/som/RaidSystem.class`, SHA-256
`870f5f3ee880f1bfa1875a87f1dd3b4904f24cbd016a2eb4742c2cf4d627c632`,
reads both password fields into public `paramString()` diagnostic text.
`toString()` delegates to that method. The original class has 109 fields,
139 methods, class version 47 and constant-pool count 1184.

The override changes exactly two four-byte instruction windows in
`paramString()`: PCs 156–159 read `monitoringPassword` and PCs 190–193 read
`managementPassword`. Each becomes `ldc_w #1185; nop`. Two appended constants
define the fixed `<redacted>` token, and the pool count becomes 1186. The
patched class SHA-256 is
`f2b2c2f5b7c3e3eb941c16436cb41f2a64b0630a6dabf722fb36470e11858f2c`.
No new runtime class or dependency is required.

**Deliberate security semantics:** both diagnostic fields show the token even
when their actual value is null or empty. Labels and all other diagnostic text
remain unchanged. No password is cleared or changed. Getters, setters, saved
flags, observers, copying, serialization, crypt functions, transport, controller
commands, polling and retries retain their existing bytecode.

## Local evidence

The initial expanded development gate is
`build/model-diagnostic-development-1/observations.json`; it is explicitly
`qualification:false`, with no integrated build source claim. Its overlay JAR
SHA-256 is
`7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158`.
Only RaidSystem differs from the hash-pinned qualified audit25 JAR. These are
development records, not release acceptance.

- Exact reverse reconstruction pins the entire original class. Mutations to
  every individual patched byte must be refused, including changes elsewhere
  in the class, incomplete windows, wrong constants and wrong instruction order.
- Fresh explicit-class-file `javap` output independently compares the entire
  original and patched classes. Only the two appended constants and exact
  instruction windows are normalized. Fields, methods, other instructions,
  stack/local frames, exception tables and attributes must compare equally.
- Both bundled architectures run interpreted and requested compiled modes:
  four runs, each with 40 cases. x64 runs through Rosetta.
- Actual candidate diagnostic methods are compared against actual original
  diagnostic methods with token-valued fields. Synthetic null, empty, distinct,
  punctuation and Unicode password cases combine both saved flags and empty
  or populated maps. Public text fields differ from null defaults; the fans
  map contains two controlled children to exercise separators.
- Both a child SOM loader and the product loader are exercised. Child
  RaidSystem and AbstractSystemElement bytes and archive origins are checked
  using child `findResource`, avoiding parent-first resource lookup. Parent
  product/probe identities are separately pinned.
- Actual saved-flag setters generate exactly one observer notification in
  the manually initialized Observable. Actual getters preserve the original
  String references and saved flag.
- Eight interpreted behavioral controls (four per architecture) retain both
  original reads, either individual read, or substitute an incorrect token.
  All fail at the fixed differential assertion. Verification errors, unrelated
  exceptions and timeouts are not accepted as negative-control successes.
- AbstractSystemElement, SystemController, RaidController, PowerSupply,
  Battery and Fan are freshly disassembled and hash-bound. Direct diagnostic
  field reads of the five concrete children contain no password field. This
  is static evidence; arbitrary nested object diagnostics are not qualified.

Earlier prototypes failed because the SOM superclass is package-private and
constructor bypass leaves Observable's observer vector null. The fixture now
loads the complete SOM package in each child loader and initializes that vector
explicitly. Product code was not altered to repair fixture setup.

## Review and limits

Actual Claude CLI design and prototype reviews requested the independent
disassembly, loader-resource identity, observer, public-field, single-loader
and negative-control checks above. The follow-up static QA review found no blocker in the patch or overlay gate. It identified the missing baseline integration, comparator updates and clean commits; those are being completed before qualification. Additional checks now target both candidate loaders with sixteen behavioral controls, recheck the complete build artifact at the end, and inventory the named nested model diagnostics.
Static review is not execution evidence. The manifest itself does not carry the audit version, so the audit26 JAR remains byte-identical to the exact audit25-plus-model overlay while the app plist version changes.

Constructors are bypassed with Unsafe. Five synchronized model maps and the
Observable vector are fixture-initialized. Map children are fixed stubs; no
agent is constructed and no original child model constructor is exercised.
Reference loaders source the SOM package from audit25; parent net/log4j code
continues to come from the candidate. Cross-loader agent/net operation is not
tested. Default Log4j initialization is disabled in this fixture.

This repair prevents credential rendering through these two model diagnostics.
It does not prove every credential path safe: passwords remain Strings in
memory, public getters and copy constructors remain, saved credential handling
is unchanged, and heap/reflection access is unchanged. Direct password-getter
logging elsewhere is outside the repair. A development static inventory of
all 2,869 candidate classes found 83 password-named application member
references across 34 classes; that is a conservative reference inventory,
not exhaustive dynamic data-flow proof. No saved profile or real credential
was read.

No Main startup, native GUI, persistence, real socket, controller command,
mounted/production volume, firmware transmission or installed-app modification
is involved. Physical Intel behavior is not established by Rosetta. HTTP
remains plaintext. Hardware acceptance stays deferred until actual operational
need, as instructed by the user; it is not converted into a pass.
