# Filename and save-site characterization — nonshipping

This probe invokes the pinned audit27 `compat.PreferenceIO.write` helper in a
null-parent loader. It characterizes the raw FileOutputStream(File) path shared
with the original Apple store; it does not execute the original backend, factory,
Main or GUI. Those caller semantics have separate evidence under `../caller`.
No native atomic helper is invoked here and no release or installed app changes.

Twenty-two labels run under ARM and Rosetta x64, both interpreted and compiled,
with synthetic empty dictionaries. Each JVM runs in a new disposable directory
with fake home, exact String write allowlist, networking/exec/native-preferences
tripwires and zero denied operations. Exactly one checkWrite of File.getPath is
required per label. Malformed paths never go through Paths in the guard. Every
`..` stays in its case directory; no links or external paths are introduced.

Python enumerates raw byte names and asserts exact entries, contents and actual
file modes. Java separately records input UTF-16 units, File-normalized units,
toPath exception class and File.list units. Encodings, forced file.encoding,
requested locale, requested umask and filesystem case/normalization sensitivity are recorded.
Filesystem metadata queries are read-only; only filesystem labels are retained,
not disk identity, mount paths, encryption state or unrelated metadata. Compiler,
runtime, reference, source/probe and metadata-tool bytes are checked before/after.
Clean source mode checks all recorded source bytes against Git.

Observed on this case-insensitive, normalization-insensitive APFS workspace:

- Interior dot and real-directory dotdot succeed. Missing/file components before
  dotdot fail; Java must not lexically normalize them away.
- File removes repeated and trailing slashes; the trailing-slash nonexistent
  target succeeds. Empty, NUL and directory basenames fail with
  FileNotFoundException. No underlying errno classification is claimed.
- NFC and NFD names retain distinct requested byte forms when created in separate
  folders. File.list presents the NFD entry as NFC. Raw bytes are authoritative.
- Non-BMP characters use four-byte UTF-8. Lone high/low surrogates become `?`;
  reversed surrogates become `??`. NIO toPath rejects those strings. This differs
  from the strict experimental encoder. No insecure in-place fallback is planned.
- 255 ASCII units succeed and 256 fail. Both 85 and 86 copies of a three-byte
  character succeed (255 and 258 bytes); there is no universal 255-byte limit.
- All successful synthetic empty XML files have the same pinned 151-byte content
  hash and mode 0644 at requested umask 022. This is original-helper behavior,
  not the private mode promised by the atomic experiment.

Development run 6 passes after the final review refinements. Run 1 failed because its expected XML declaration used
an incorrect PUBLIC DTD rather than Apple's SYSTEM DTD; run 3 had a label-order
mismatch. These harness failures are excluded. Run 2 (15 cases) and run 4 (22 cases
without the later guard/filesystem checks) are superseded. All development records
are dirty-source observations, `qualification=false`.

`inventory.py` is a separate read-only static selection. It checks the immutable
Apple JAR and cached inventory entry hashes, selects all preference classes,
classes referencing changeCount and synchronize/getPreferences caller methods,
then disassembles without executing app code. It records 22 selected classes,
23 methods matching selected call names and seven original putfield instructions. The latter include three
writes in separate `com.chaotic.Preferences`; they are not Apple counter writes.
Among selected audit27 entries only FileBasedPreferences differs. Call presence
does not establish runtime frequency or reflective/native call completeness.

Reproduce after committing sources, with new output directories:

```
/opt/homebrew/bin/python3 -E -s experiments/atomic-preferences/paths/check.py \
  --jdk /path/to/pinned/compiler/Contents/Home \
  --output build/path-new-run --require-clean
/opt/homebrew/bin/python3 -E -s experiments/atomic-preferences/paths/inventory.py \
  --jdk /path/to/pinned/compiler/Contents/Home \
  --output build/path-sites-new-run --require-clean
```

Excluded: existing-name case/NFC aliases, overall PATH_MAX, other filesystems and
locales, original backend filename execution, physical Intel, Main/factory/GUI,
real profiles, arbitrary native code, external symlinks, native atomic binding and
hardware. The earlier caller/atomic tests cover other synthetic target/failure
scenarios separately; this record does not absorb those scopes. No independent
physical Intel or hardware qualification is implied. HTTP remains plaintext.
