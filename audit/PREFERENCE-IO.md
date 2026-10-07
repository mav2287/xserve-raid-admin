# Preference save-stream preservation milestone (audit27 development)

Status: development gate passed; clean full candidate qualification and release
artifact assembly are pending. Qualified audit26 artifacts and their frozen ledger
remain unchanged. No real preference file, credential, controller, installed app
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
