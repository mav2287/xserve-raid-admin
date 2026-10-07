# Audit28 secure preference preservation — offline scope

FACT: the secure product was built twice at clean source
`e005b9a2877133d98af4cf86fd5b625532b06fcb` from the preserved audit27 build.
The common JAR SHA-256 is
`bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e`.
Its exact inverse restores audit27 SHA-256
`e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62`:
one replaced `compat/PreferenceIO.class`, seven added helper classes. Original
Apple classes, controller commands, polling and retry timing do not change in
this milestone. Original XML serialization and the original
FileBasedPreferences.synchronize monitor, counter and exception semantics remain.

FACT: ABI `0x58415204` native helper hashes are ARM64
`2a402a2e2cd98e22fc31c9c4499c75b720d06cbf2826e2bb9aa0c9d77a872284`
and x86_64 `2485d8f66b2c480a94d309ba1f16028f1fa1e0edb957f85063eb28a107834f42`.
Native helpers load only from the actual application CodeSource-relative
Frameworks directory, validate binding/ABI, link only macOS libSystem, and have
macOS 11 binary floors. There is no insecure in-place fallback.

## Deliberate, bounded security changes

Preference saves use an exclusive private 0600 temporary file in the destination
parent, verify ownership/ACL/parent/device/inode policy, then atomically replace
the intended filename. Symbolic links are rejected. Replacing a hardlink splits
that link rather than modifying the other linked file. Old metadata is not
copied to the private replacement. Malformed Java UTF-16 names fail closed;
File/kernel dotdot resolution is retained without lexical normalization.
These are documented security restrictions, not claims of exact legacy parity.
Raw case/NFC/NFD directory-entry spelling passed on the local APFS volume;
other filesystems remain unqualified. Remote files require fsync before commit;
local atomic replacement is not a crash-durability guarantee.

Native handle ownership transfers after native entry; abort/commit consume the
session once. An interrupted rename is never retried because its outcome can be
uncertain. Fixed diagnostics distinguish failed, committed-but-cleanup-failed,
and unconfirmed saves. At most one signal per category is emitted per process;
no path, XML, credential or exception text is rendered. GUI-mode feedback is
deferred to Swing; that native dialog remains unverified. The launcher enables
GUI feedback only for the zero-argument application entry after one canonical
legacy process-serial argument is removed; all other arguments remain exact.

## Evidence and limits

Clean source passed 185 Python units, 40 actual-JAR preference/caller/path/binding
runs, sixteen 37-case native matrices, 76 actual-caller fault variants, 26 unsafe
native negatives, eight raw-name/hardlink observations and two wrong-destination
negative controls. JNI checks used the actual library/JAR with four empty-loader
controls and four interpreted functional/lifecycle variants. Only the two exact
vendor Corretto loader-warning prefixes observed in the empty baseline were
accepted; no arbitrary JNI output was filtered. ARM execution was native;
x64 execution was Rosetta, not physical Intel.

The prior audit27 release, original JAR, installed application and frozen audit27
integrity ledger remain untouched. Failed development runs, partial packages,
and modified-driver prototypes are not silently promoted to committed-source
qualification. Product, packaging and evidence commits are recorded separately.
Actual Claude CLI reviews cover the design, owner lifecycle, reporting, native
name handling, qualification and packaging provenance bridge; review text is
archived in audit/claude-review.

UNRESOLVED/DEFERRED: full native interface/menu/browser/error-dialog acceptance,
physical Intel, real controller/firmware behavior and production-volume tests,
other macOS/filesystem combinations, Developer ID/notarization/Gatekeeper and
original Apple redistribution rights. Hardware tests are deferred until actual
operational need; restricted operations still require immediate confirmation.
No full application launch, profile access, hardware operation or installed-app
modification was performed. HTTP remains plaintext. These offline results do not
establish 100% operational qualification or guaranteed future-macOS support.
