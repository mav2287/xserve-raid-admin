# Private descriptor experiment — not shipping

This directory is excluded from `tools/baseline.py` and the two architecture
packages. The application remains audit27. No real preference, credential,
controller, installed app or production/mounted RAID volume is used here.

The experiment preserves the original XML serializer, UTF-8 writer, explicit
flush and noninterruptible FileOutputStream writes. The Java stream attaches to
an empty FileDescriptor before native opening. Darwin checks the anchored parent
for file-inheritable ACL entries, then opens without truncation, rejects final
symlinks, nonregular/foreign-owner/multiply linked files, file ACLs and filesystems
that ignore ownership. It sets mode 0600, clears O_NONBLOCK, and only then
truncates and transfers the descriptor to Java. Native field IDs are checked at
library loading. Unavailable native libraries become IOException. The fixture
boundary and metadata getter are test-only and must never ship.

Development execution `build/private-descriptor-development-10/observations.json`
passes 12 differential variants: two runtimes, Xint/Xcomp and umask 022/077/0277,
34 cases each; 16 denial/library variants; and 18 interpreted native negatives.
It is dirty-source experimental evidence, not product qualification. Repeated
native outputs match on each architecture. Native compiler/SDK metadata is
recorded; it is not a complete locked toolchain. x64 runs under Rosetta.

Success cases explicitly require successful serialization. Early/late bad-key
cases require ClassCastException; the synthetic Error and mid-serialization
interrupt must actually occur. Existing-file serialization failure preserves the
original partial/truncated output. FileDescriptor counters must be supported,
and no collection occurs during measured save loops. Permission/library denials
cover an existing sentinel and a missing file. Raw directory-entry bytes require
the exact ASCII, BMP, NFC, NFD and supplementary UTF-8 inputs on APFS. Surrogate
and NUL filenames reject with the exact expected exception and unchanged listing.

Native negatives cover early truncation, symlink following, omitted link/mode or
parent-ACL checks, a leaked rejected fd, early descriptor publication, retained
O_NONBLOCK and missing CLOEXEC. A suppressed double-close failure is rejected.
The repeat-close case tests Java idempotence; it does not prove native close
ordering. Both runtime src.zip and FileDescriptor bytecode hashes are bound in
the record; vendor native fileClose/initIDs source is not verified.

## Security limitation and next milestone

**Do not integrate this in-place experiment as complete profile protection.**
An already-open reader retains access after fchmod and can observe new data
written to that same inode. Unknown parent ACLs may also cause permanent silent
save rejection through the original handler. These are material limitations.
Atomic private replacement needs its own security and preservation acceptance:
successful output bytes unchanged; failed saves preserve the original profile;
old readers retain only old bytes; native ownership, commit/abort and metadata
changes independently tested. No atomic replacement or at-rest encryption is
implemented here. HTTP remains plaintext.

Other limits: same-user/root attackers, intermediate-directory changes, actual
foreign ownership, ownership-disabled filesystems, close/filesystem error
injection, read-only/search-only parents, FIFO with a reader, real GUI/profile
workflows and physical Intel remain unqualified. New-file leftovers after
rejection and retained descriptors opened before mode tightening are documented.

## Reproduction

From the repository root, use the pinned Python 3.14.8 and compiler JDK recorded
in audit locks, with both audit27 bundled runtimes present:

```
/opt/homebrew/bin/python3 -E -s experiments/private-preferences/check.py \
  --jdk /path/to/pinned/compiler/Contents/Home \
  --output build/private-descriptor-new-run --require-clean
```

The output must be new. A clean experimental run remains `qualification=false`:
it does not qualify product integration. Commands in records use `<repo>`,
`<java-compiler>`, `<sdk>` and `<clang-bin>` aliases for the corresponding inputs.
The JVM and native error output is withheld on unexpected failures.

Excluded development results: removing LC_UUID prevented library loading on this
macOS; the linker’s default deterministic UUID is retained instead. An early fd
reuse test assumed no gap from closing the parent descriptor; it now keeps a
bounded set of sentinels open until the actual number is reused. The first nested
fixture used Arrays.asList, which Apple’s serializer rejects; valid input now
uses ArrayList and requires success. Invalid-path setup formerly passed NUL to
NIO before the helper, and filename-test directories lacked owner-write under
umask 0277; these fixture errors are corrected. Earlier development passes with
weaker assertions are superseded by the expanded record and are not qualified.

Actual Claude CLI reviews are archived under audit: the privacy design, native
descriptor design, implementation review and follow-up. They are static reviews,
not executed tests. The current fixes address the follow-up’s six evidence
blockers. The atomic-save design remains a separate next milestone.
