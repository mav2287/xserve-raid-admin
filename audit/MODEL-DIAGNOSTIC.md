# RaidSystem diagnostic credential redaction

Status: **qualified local audit26 candidate**, with sixteen candidate gates and
170 unit tests passing. Product, fixtures, both clean builds, packages, archives
and SPDX generation ran from `46dec9e8cfba5b9de9ce49a59b05fd5f61b4b0a6`.
Evidence assembly ran from clean `809bdb21bba93872f71012f2200fcfa6b1fab1bc`;
only the assembler and static review text were added after the product commit.
This is local software qualification, not full operational or signed-release
acceptance. Audit25 artifacts and its ledger remain immutable. No installed
application or controller was modified or contacted.

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

The checks below describe the archived clean qualification; the development
records are historical context and are not counted as acceptance.

Historical development evidence: the initial expanded development gate is
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
- Sixteen interpreted behavioral controls (four mutants, both child and product
  phases, on each architecture) retain both
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
and negative-control checks above. The follow-up static QA review found no blocker in the patch or overlay gate. Its missing baseline integration, comparator updates and clean-commit conditions are resolved by the archived clean executions. Additional checks now target both candidate loaders with sixteen behavioral controls, recheck the complete build artifact at the end, and inventory the named nested model diagnostics.
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


## Frozen qualification and reproducible artifacts

Candidate JAR SHA-256:
`7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158`.
The [frozen ledger](model-final-integrity.json) SHA-256 is
`c44fb23a7eb13d7f2c46d5ce0745c8cd1025057ec93f28347b0768c9ba92a655`.
It binds 38 records and 753 source proofs against their actual clean Git source
and unchanged current bytes. [The archival map](model-archival-map.json) locates
34 exact record copies. The four large ZIPs remain local ignored build artifacts.
All sixteen gates passed on their initial clean runs; no failed run is included
as an accepted result. An ad hoc SPDX comparison initially constructed an
incorrect repeat filename; this inspection error is excluded and did not affect
SPDX producers, records, or successful pair comparisons.

Paired bare app file/mode digest:
`44d99708718839487b7cf40e5954b6d6f5a4eea3cf622c0230a8923dd87b5c4c`.
Paired packaged app file/directory-mode digests:

| Architecture | Bundle digest | Repeated ZIP SHA-256 | ZIP bytes |
|---|---|---|---|
| aarch64 | `c062e67ba4930ec364b265225aa04e0f9682c9a8709b42e59035d4b6475fb571` | `deadf08032822c09bb2694611d6fd09b98a9d50e433f3d63efc6aa4c13d6e4c8` | 220528623 |
| x64 | `91e433e62f7612911b4cf18f59e60358c4ab18bcfb5439a0f826653e91ed2120` | `ff83388bdc1ad9a65c5bc427d7d341e6a17f157b4892e85235a4d8acedfde625` | 217113559 |

Each architecture's repeated SPDX 2.3 documents are byte-identical, with 3,305
physical/virtual file records and 17 packages. All four documents pass the
pinned official schema and semantic checks, including twelve negative controls
per document. The fixed creation metadata input is `2026-10-07T05:40:36Z`;
it is not a run timestamp. Runtime signatures verify after ZIP extraction.
Apps remain unsigned and unnotarized. No new dependency or runtime class is added.

The [model gate record](model-records/model-clean-model-boundary/observations.json)
contains four runtime/mode observations, 40 cases each, and sixteen behavioral
negative controls. The nested static inventory now additionally includes
RaidSet, Disk, HostInterface, DiskSlot and IPAddress. It examines direct field
reads in their paramString/toString methods in the reference, applicable because
those candidate entries are identical. It is not exhaustive recursive data flow
or proof against credentials supplied via arbitrary methods or nested objects.
The copy constructor and monitoring-password setter are preserved structurally,
and are not executed by this fixture. The second development record was also
explicitly unqualified and dirty; neither development record substitutes for
the clean qualification above.

Actual Claude CLI reviews are archived for
[QA](CLAUDE-MODEL-DIAGNOSTIC-QA.txt),
[integration](CLAUDE-MODEL-DIAGNOSTIC-INTEGRATION.txt),
[evidence assembly](CLAUDE-MODEL-EVIDENCE-ASSEMBLER.txt), and
[the corrected assembler](CLAUDE-MODEL-EVIDENCE-ASSEMBLER-FOLLOWUP.txt).
The assembler's four initially missing metadata bindings were corrected before
its first qualified execution. Reviews are static evidence; the tests and
artifact measurements establish execution results.

For fresh reproduction, use the product commit, the exact locked compiler,
Python and cached runtime/reference artifacts recorded in the ledger. The
baseline builder accepts a new output directory; qualification command paths
in [model-gate-commands.json](model-gate-commands.json) assume fresh model-clean
outputs and pinned historical reference builds. Do not overwrite frozen outputs.
The [unit runner](model-unit-runner.py) and
[gate runner](model-gate-runner.py) require a clean checkout. Generate both
packages and repeated archives/SPDX documents while HEAD remains at the product
commit, then use the assembler commit for final metadata binding. Historical
reference JARs are local artifacts with recorded identities; recreating them
requires their recorded historical source checkpoints and compiler. No
independent-host reproduction is claimed.

Full native GUI acceptance remains open. A separate
[Claude native-component design review](CLAUDE-NATIVE-UI-QUALIFICATION-DESIGN.txt)
identified unreviewed transitive constructors/paint paths and native AppKit
preference access outside the Java guard. Existing hidden component probes are
still development-only. No new native UI execution was performed for audit26.
A disposable macOS account or VM without saved systems is needed for full
startup qualification; `-Duser.home` alone is not sufficient isolation.
