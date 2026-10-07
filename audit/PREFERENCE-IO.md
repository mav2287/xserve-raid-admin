# Preference save-stream preservation milestone (audit27 qualified offline scope)

Status: qualified local offline audit27 scope. Seventeen clean candidate gates,
175 units, paired packages/archives/SPDX and clean evidence assembly pass. Frozen
audit26 artifacts and their ledger remain unchanged. No real preference file, credential, controller, installed app
or production/mounted RAID volume was accessed or modified.

## Facts and exact scope

The audit26 reference JAR is
`7c361034ec4deeec1741e49d3963c3dfd8e6dd07ea1b1fb7ab029d2aa3f74158`.
Its original `com/apple/util/prefs/FileBasedPreferences.class` is 1349 bytes,
SHA256 `9a9a41cf9982b5413dddec7f73c84bd644617b417e4602b53a551589de968d6d`,
class version 47, pool count 82, one field, four methods. Both constructors only
initialize inherited fields and the identifier; they do not load a profile.
`Preferences.synchronize()` calls `store()` while holding the original lock when
changeCount is positive. Store never resets that count; load resets it to zero.
The change intentionally preserves these facts.

Original store opens FileOutputStream(File), wraps it in OutputStreamWriter with
the literal UTF-8 charset, invokes the original XML serializer, and flushes. Neither
store nor the serializer closes the stream. Original development measurements,
with explicit disposable identifiers and no GC during measurement, showed 32 extra
descriptors after 32 stores on both pinned runtimes in interpreted/compiled modes.
Valid loads showed no descriptor growth in the same runs. No malformed-load lifetime
claim is made. Under umask 022 the new synthetic file's POSIX mode was 0644; no real
profile mode, parent access or ACL was inspected.

The override replaces only store PCs 7–46 with identifier/dictionary loads and
one helper invocation, followed by 29 NOPs. Six constants are appended. All other
class bytes, including load, constructors, monitor ownership, catch ranges, stack
limits, locals, flags, fields and changeCount behavior, reconstruct exactly to
the pinned original. Patched SHA256:
`76935f031ec1555f7e2f267d74d32be46de8f39257d84f1fc34ae102fbdf3b5a`.

One Java8 helper, `compat.PreferenceIO`, owns the **original FileOutputStream(File)**
with try-with-resources. It preserves the original serializer, UTF-8 Writer and
explicit flush. It closes the raw stream, not the Writer: closing the Writer on
serialization failure would flush buffered partial XML the original never wrote.
Java's resource cleanup preserves a primary Error/Exception when close also fails.
The original handler still swallows Exceptions, and propagates Errors after releasing
the monitor. No controller code, commands, request bytes, polling or retry timing
changes. Development candidate JAR SHA256:
`e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62`.

## Tests and limits

The development gate executed eight candidate variants (both architectures,
Xint/Xcomp, umask 022/077), each with 18 cases, and eight original characterization
variants. It binds whole JARs, fresh probes, class origins/resources, source hashes,
compiler/runtime trees, and a fresh independent full-class javap comparison.
The caller factory, MacPreferences, Main and real profiles are never invoked.
The Java guard denies networking, exec, native preferences and writes outside the
disposable directory. It is a fixture guard, not a general application sandbox.

Cases compare original/candidate bytes for empty, Unicode, nested numeric/boolean/
data/date containers, large payloads, invalid surrogates/control characters, and
early/late invalid-key serialization failures. Existing longer files are truncated
to exactly the original bytes. Existing mode and symlink/dangling-link behavior
remain. Interrupts before and during serialization are preserved with identical
output. Exceptions, Errors, change counts and lock release are checked. Successful,
Exception and Error save loops have zero descriptor growth with no measured GC.
Directory/missing-parent attempts retain original change-count behavior.

Sixteen interpreted negative controls must fail at their exact differential
AssertionError frame, not a verifier error, timeout or unexpected exception. They
change charset, close the Writer on failure, append instead of truncate, omit all
close calls, omit failure-path close, replace the stream with interruptible NIO, leak only on Error, or clear interrupt flags. The mutation compilation pipeline also reproduces the pinned unmodified helper.
Five units test every byte mutation, input stage/window rejection, exact class
reconstruction, independent full-class disassembly and strict helper/backend pairing.
x64 is Rosetta on the ARM host, not physical Intel; Xcomp is a requested mode.
Closing the raw stream can newly throw on success; the original handler swallows that exception. The helper opens before allocating its Writer, unlike the original new-expression allocation order: an OOM at Writer allocation can now leave a truncated file. Arbitrary filesystem races, JVM exhaustion and close-I/O failure injection are not
qualified by the file fixtures. Full GUI and controller behavior remain separate.

## Rejected NIO privacy prototype and unresolved security work

A development prototype used private POSIX creation and refused final-component
symlink writes via Files.newByteChannel. It passed output/mode/link/leak fixtures,
but Claude's review identified interruption semantics that can truncate a profile
and then abort a save the original FileOutputStream would complete. A dedicated
negative control reproduces that regression. This prototype is **not shipping**.
Neither clearing interrupts nor reflective descriptor wrapping was promoted.
Claude recommended the smaller original-stream ownership milestone; reflection
would require separate proof of native close ordering, descriptor reuse and failure
before truncation on both runtime/native sets.

Private new-file creation, existing permissions/ACLs, hard links, symlink privacy,
atomic replacement, fsync and at-rest protection remain unresolved. Existing saved
password representation and flags are untouched; this does not establish encryption
of stored credentials. HTTP remains plaintext. These gaps are retained in the
acceptance record; they are not waived by a successful build or launch.

Actual Claude CLI reviews:
[prototype](CLAUDE-PREFERENCE-WRITE-PROTOTYPE.txt),
[interruption design](CLAUDE-PREFERENCE-INTERRUPT-DESIGN.txt),
[integration](CLAUDE-PREFERENCE-IO-INTEGRATION.txt), and
[follow-up](CLAUDE-PREFERENCE-IO-FOLLOWUP.txt).
The design review describes the superseded NIO prototype at its read time; its recommendation A was applied to the current original-stream helper. The prototype source is retained only in ignored development evidence. The integration review raised a generic version50 verifier concern; the exact original version47/handler evidence and follow-up close that concern. Negative controls bind distinct codes for the assertions they target; remaining general positive assertions are not separate negative-control claims. The clear-interrupt mutation targets a pre-set flag; flags set during serialization are positively tested and structurally protected, without a separate after-flush-clearing mutation. These are static reviews, not executed test evidence. Reviewer questions about
the shipped runtime are answered by audit26's paired packages/ZIPs and vendor
signature checks; the artifacts contain pinned Corretto 8.504.04.1 on each arch.


## Clean-source executions and evidence review checkpoint

All seventeen candidate gates and 175 full unit tests passed from clean product/
build/package/release commit `4735f4165340cbca6dc30a83f200f4a31ac6dc15`.
The two bare builds match, paired bundles match bytes and file/directory modes,
all four archive extractions retain vendor signatures, and repeated SPDX documents
match on each architecture. Each SPDX contains 3306 files and 17 packages and
passes the pinned schema/semantic validator plus twelve negative controls.
Fixed creation input is `2026-10-07T07:00:55Z`, separate from execution metadata.
The evidence assembler still requires its clean QA-commit execution; this note
alone is not a completed frozen-ledger claim.

The [assembler review](CLAUDE-PREFERENCE-EVIDENCE-ASSEMBLER.txt) describes its
first draft, at review time. Its concrete binding requests were applied before
execution; the [follow-up](CLAUDE-PREFERENCE-EVIDENCE-ASSEMBLER-FOLLOWUP.txt)
found no blocking mismatch. Neither reviewer executed any test. Subsequent
nonblocking suggestions were also applied: runtime-tree equality, negative-control
mode/artifact checks and preference-specific limits. All core executions finished
before these QA-only files were committed.

Excluded development/setup results: the earliest preference probe had a nonpublic
main method; its next lifetime loop encountered GC and was invalidated. Fixed
small failure data eliminated GC during measurement. The first negative-control
inspector expected wrong source line numbers; corrected exact codes/frames replaced
that inspector. The private-creation NIO prototype was rejected for interruption
semantics, not promoted. A packaging-help query used a nonexistent filename.
Two ARM archive attempts failed before any archive/record publication because the
new output parent directory was absent; creating that directory and reexecuting
from the unchanged clean commit produced the four accepted archive records.
No failed development/setup attempt is included as accepted execution evidence.


## Frozen qualified evidence and local artifacts

The [frozen ledger](preference-final-integrity.json), SHA256
`f3547d5a17d0fe882417f9bf49d066302d54a9d7e18d854b09331c546aa63bce`,
binds 39 records and 883 proofs to their actual execution commits. Evidence assembly
first passed from clean `c7ea088eb95bc54c32a8be415be17f53c36c65d5`, after all product,
fixture, build, package, archive and SPDX executions completed from clean
`4735f4165340cbca6dc30a83f200f4a31ac6dc15`. The
[archival map](preference-archival-map.json) locates 35 exact small-record copies;
four large ZIPs remain local ignored artifacts. Do not overwrite these records.

Bare bundle digest: `b8d411b10753658f6fb863963e77c2a52d7bdfc826563d310b9ff51d97089d86`.
Paired bundle digests (bytes plus file/directory modes):
ARM `072b273604d0dba0fe76ed96a11b2ca12cea56e3f5859b7c2c89ce0ee157cd18`;
x64 `073b132814311cfbd94ea8d8d32167b4a6d9b224bc9705ed67333952412e7747`.

| Artifact | SHA256 | ZIP bytes |
|---|---|---:|
| ARM ZIP | `94cb49fb06fea3c40b817aec4ae70d32cf831b8895427fbb2be065fac80e853a` | 220529948 |
| x64 ZIP | `eef8054a43373ca5bca7fd5295f2d766f232f8637b4f137a6921b80afd216533` | 217114884 |
| ARM SPDX | `f6a45592c68eb177c61cc6537d81360c943ac2647b5c20ca6698a0b99af28726` | — |
| x64 SPDX | `c80588b7621145d11bc5964a0d4f8580c790a325ffd5735f6a7f4bf75ce6f748` | — |

Each repeated ZIP/SPDX matches its architecture's first copy. SPDX creation input
is fixed to `2026-10-07T07:00:55Z`; 3306 files/17 packages and twelve schema/semantic
negative controls per document pass. CC0 metadata terms do not grant distribution
rights to included software; NOASSERTION rights remain unresolved. Apps are unsigned
and unnotarized. No installation or publishing occurred.

Reproduction requires the recorded source commits, Python/JDK/runtime locks and
historic reference JARs. Use baseline.py/verify_builds.py, the commands in
preference-gate-commands.json, preference-unit-runner.py, bundle.py/verify_bundles.py,
release_archive.py and isolated Python `-I -S` spdx.py `--self-test`, with new output
directories and the pinned validator cache. Run the evidence assembler only from
its recorded clean QA checkpoint, not a later archival/docs commit. The expected
identity was established by paired development builds, then confirmed by two clean
builds and the full clean gate suite; its development-generation metadata is not
being presented as qualified execution. A documentation update initially used a
nonexistent hardware-report filename; the correct existing report was subsequently
updated, with no change to qualification records or artifacts.
