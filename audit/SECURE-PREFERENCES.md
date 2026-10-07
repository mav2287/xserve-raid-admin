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

## Final local release handoff

Offline product implementation, regression and unsigned release preparation are
complete within the available environment. This is not full operational acceptance.
Product remains clean `e005b9a`; corrected additions-only release tools, isolated
packaged tests, seven real CLI negative controls and 185 current units run at clean
`fd94ee9`. The committed corrected runtime gate runs at `0020923`; other fifteen
secure gates and all seventeen rebuilt-audit27 gates retain their clean e005
attributions. Original tools/source are unchanged; new release tools use the
unmodified full artifact checker with historical Git input proofs. No source
hash is substituted. Full commits/hashes and all selected passing records are in
[the final ledger](secure-release/final-integrity.json). Actual Claude closure
review and implementer resolutions are [archived](secure-release/claude-closure.txt).

Current packages and metadata are under `build/releases/audit28/`:

- `RAID-Admin-1.5.1-modern.audit.28-aarch64-unsigned.zip`, SHA-256
  `e3701f62b03824b3b206c46c759b43fe3edd291f24ce4d1c40436e5f239611a7`.
- `RAID-Admin-1.5.1-modern.audit.28-x64-unsigned.zip`, SHA-256
  `743f6a724ce743b2fc71ab3594085af0d7d9d49b73edfe9573dc54a995a80e02`.

Each architecture directory supplies SPDX, provenance and release observations;
`SHA256SUMS` binds the handoff files. Independent packages over both independently
reproduced common builds match files, modes and ZIP bytes. Isolated actual-packaged
fixtures pass ten runs plus five exact-launcher argv-stub runs per architecture.
These fixtures run against the unpacked package. Their manifest SHA links to
the measured bundle and the release record; ZIP extraction was independently
verified identical, and final archive copies are hash-bound. No actual Main or
launcher application start is implied by the stub tests. ARM64 execution is
native on macOS 26.6.2; x64 is Rosetta, not physical Intel.

All records are frozen at their execution commits. Read-only verification after
the final evidence commit uses:

```sh
/opt/homebrew/bin/python3 -I -S audit/secure-release/verify.txt
```

For fresh package/fixture qualification, check out the recorded release tooling
commit or create a fresh clean-source package and new evidence; old package
fixtures intentionally reject a later HEAD rather than relabel prior execution.
Reproduction commands are [archived](secure-release/reproduction.txt). Use the new
`secure_release.py`, `check_secure_release.py` and `secure_release_gate.py`; the
old incomplete orchestration tools remain historical and are not the release path.
Failed/partial/nonisolated and derived-driver development attempts are explicitly
excluded in the ledger. The two early lock output mismatches remain unexplained;
the separate exact canonical run passed without filtering or an internal retry.

### Credential-path evidence correction

A raw-name scan covers all 2,844 original class entries; the earlier method-call
inventory covers 656 selected application classes. Only PasswordManager and its
nested exception contain that name; no statically identifiable app caller was
found. The original already has Save Password and Forget Password behavior via
RaidSystem and reversible SimpleCryptCoder/Base64 obfuscation. Those controls
remain in code; actual behavior through the new preference writer and any
persistence remain unverified. No duplicate Keychain UI or migration is added. The native library class
catches its own link failure, not a verified app caller. Earlier top-level EVIDENCE/PLAN/GAPS/acceptance copies, audit/requirements
and triage inferences tying that failure to the save/forget UI are superseded.
[Exact scope, class/method hashes and unresolved questions](secure-release/keychain-scope.json)
and [one-off source](secure-release/keychain-scope-driver.txt) are hash-checkable.
Replacing the unused JNI is not automatically necessary for preservation (inference).
Dynamic reflection/native lookup, actual password persistence and confidentiality
remain unverified. No stored-credential encryption or comprehensive security claim
is made. No real credentials, saved profiles or Keychain entries were accessed.

Final assembly used an ignored one-off orchestrator at execution time; its exact
source/hash is [archived](secure-release/assemble.txt). Boundary records supplement
17 audit27/16 secure gates; they are not extra gates. The current unit run uses
-E -s (185 tests, zero skips); package QA and final packaged fixtures use -I -S.
Final documentary corrections modify only nonproducer top-level Markdown and add
a sidecar to the immutable requirement snapshots. They do not alter the application
or qualified release-tool execution. The historical additions-only bridge therefore
intentionally rejects rerunning the frozen-product release path at this final
documentation commit; use the standalone verifier above, the recorded release
commit for a rerun, or a fresh current-source build and new qualification.
