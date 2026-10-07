# Post-audit28 credential persistence boundary

This additive record refines the credential-persistence unknowns in the frozen
[audit28 report](SECURE-PREFERENCES.md#credential-path-evidence-correction).
It changes no shipping application code or release artifact.

FACT — At clean fixture commit `e74d373`, four actual-JAR runs passed on the
packaged audit28 ARM64 and x64 runtimes, each in `-Xint` and `-Xcomp` modes.
The record captures macOS 26.6.2, Python host `arm64` and asserted Java `os.arch`
values `aarch64` / `x86_64`. These establish native ARM and imply Rosetta x64 on
this host; physical Intel is untested. Each run performed 80 original/original,
original/current, current/original and current/current XML readbacks: 320 total.
The original JAR remains read-only, SHA-256
`5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449`.
The packaged common JAR remains
`bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e`.

FACT — The actual `SOMLocalizer.toPrefsContainer` emits `Name`, `Rate` and
`IPAddress`, plus `Attributes` when the monitoring value is non-null. It includes
neither the management value nor the management-saved flag. Null, empty, Unicode
and punctuation-containing synthetic monitoring values survived both readers.
The in-memory rate is `Integer`; the original XML reader restores it as `Long`.
The original registry constructor's bytecode explicitly expects `Long`.

FACT — Calling the actual `setManagementPasswordSaved(false)` retains the
management value in memory and leaves this persistence map unchanged. Changing
only the management value also leaves the map unchanged. The original Forget
action invokes this setter. The actual current writer produced mode 0600 files.
Repeated synchronizations preserved the tested serialized bytes.

FACT — Eight deliberately altered-JAR runs changed the unique constant-pool
getter name in `SOMLocalizer` from the monitoring getter to the management getter.
Both the original and current JAR were independently mutated, each occupying
the fixture's reference slot. Exactly one entry differed in each. Every run
failed at the exact `monitor-source`
assertion before writing a profile. Synthetic files were deleted; no profile
contents, encoded values or credential-value hashes were archived. This tests
the sensitivity of the monitoring-source assertion, not every fixture assertion.
Two separate actual CLI controls reject existing outputs and nesting inside a
frozen bundle before Java execution; their original `27bb482` attribution is
recorded separately. Mutated Apple-derived JAR copies remain ignored build-only
artifacts and are not included in evidence archives, packages or handoff.

FACT — Static inspection covers all 2,844 original and 2,877 current class entries
for constant-pool references to the three named credential fields and literal
strings equal to their field names. Field references in both JARs occur only in RaidSystem;
no exact field-name string literals were found. This is a narrowly defined scan,
not proof that assembled reflection or native lookup cannot occur. The whole-JAR
scan also records references to the six credential getter/setter names; it does
not cover other runtime JARs. Detailed
selected method/field references and class hashes are in
[observations.json](credential-persistence/observations.json).

FACT — In the selected path, original authentication code calls `Utilities.crypt`,
which uses `SimpleCryptCoder` and Base64. The coder contains XOR operations; those
classes and the localizer are byte-identical in original and current JARs. This
legacy obfuscation is not a confidentiality boundary. The fixtures seed opaque
synthetic field values directly; they do not execute the crypt/authentication
listener pipeline. Mode 0600 is access control, not stored-credential encryption.
Pre-existing files are not proactively migrated or tightened; the private writer
applies on a successful save. HTTP remains plaintext.

INFERENCE — These results support preserving the existing controls rather than
adding duplicate Keychain UI or replacing JNI merely because its library is
unavailable. The management value appears session-scoped in this registry path;
actual process restart and GUI/authentication workflows remain untested.

UNRESOLVED — Full registry observer/factory integration, real saved profiles,
actual checkbox/action/listener execution, authentication response handling,
native Keychain access, dynamic/reflection paths and broader credential lifecycle
or memory confidentiality. These tests exercise the model-to-file boundary only.

Safety: model and agent constructors are bypassed with Unsafe. An initialized
empty Observable supports the actual flag setter; agent state supplies the
actual polling getter. Backends receive explicit disposable paths. No registry
constructor, preferences factory, Main, GUI, controller or native AppKit path is
called. A reviewed Java guard rejects network, exec, real preference reads,
writes outside the disposable directory and unapproved native libraries. It is
a guard for trusted fixtures, not a general sandbox. Core/heap dumps and JVM perf
data are disabled. Exceptions are replaced with fixed codes; raw diagnostics
are withheld. Full packaged bytes/modes and runtime signatures are checked
before and after execution. Package provenance hashes are independently pinned
to the frozen audit28 manifests, rather than trusting mutable local manifests.

Reproduce from fixture commit `e74d373` with a clean tree and both pinned local
packages present (this host has Rosetta; this command is not physical Intel QA):

```sh
/opt/homebrew/bin/python3 -I -S tools/check_credential_persistence.py \
  --jdk /Users/mav2287/Library/Java/JavaVirtualMachines/corretto-1.8.0_362/Contents/Home \
  --output build/credential-boundary-new
```

Actual Claude CLI design, fixture and correction reviews are archived separately
under [credential-persistence](credential-persistence/). Implementer resolutions
are labeled separately from Claude's findings. The first attempt at `16e8947`
passed the first actual fixture but failed report assembly on a nonexistent
vendor `release` file; it is excluded from qualification. The complete `27bb482`
run is retained separately; the final `e74d373` run strengthens host, provenance,
accessor and current-JAR-negative evidence. Both bind verified runtime-tree
digests. Frozen audit28 records are unchanged. Additive record hashes and actual
Git input proofs are in [integrity.json](credential-persistence/integrity.json).
Read-only verification uses `python3 -I -S audit/credential-persistence/verify.py`.

The first additive archive assembly emitted an incomplete two-proof ledger due
to an indentation error. The standalone verifier rejected it. Its full directory
is preserved in ignored `build/post-audit28/failed-assembly-archive` and excluded;
the corrected assembler requires 20 unique proofs before creating a ledger.
