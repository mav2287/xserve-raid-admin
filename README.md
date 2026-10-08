# Xserve RAID Admin

Compatibility and preservation work on Apple's RAID Admin 1.5.1 for modern macOS. The original Java interface and controller application are retained, with a bundled runtime, thin compatibility helpers and narrowly scoped class overrides.

## Download

[Get the audit28 release](https://github.com/mav2287/xserve-raid-admin/releases/tag/v1.5.1-modern.audit.28).

| Your Mac | Download |
| --- | --- |
| Apple silicon (M-series) | [Apple silicon ZIP](https://github.com/mav2287/xserve-raid-admin/releases/download/v1.5.1-modern.audit.28/RAID-Admin-1.5.1-modern.audit.28-aarch64-unsigned.zip) |
| Intel | [Intel ZIP](https://github.com/mav2287/xserve-raid-admin/releases/download/v1.5.1-modern.audit.28/RAID-Admin-1.5.1-modern.audit.28-x64-unsigned.zip) |

**You do not need to download or install Corretto 8 or any other Java runtime.** Each ZIP includes the matching pinned Amazon Corretto 8.504.04.1 runtime inside `RAID Admin.app`. The launcher uses that bundled runtime rather than your system Java. Both packages contain the same application JAR; their runtimes and native helpers differ by CPU architecture.

These are **unsigned, unnotarized prerelease audit builds**. Offline checks passed on native ARM and on x64 under Rosetta; physical Intel, full native interface/startup and real-controller workflows still need qualification. Successful launch is not proof that every feature works. See [completion and remaining acceptance](COMPLETION-STATUS.md).

## Installation and use

1. Download the ZIP for your Mac and extract it.
2. Keep the complete `RAID Admin.app` bundle together; the runtime is inside it.
3. Open the app when you are ready to use it. Installation in `/Applications` is optional. Preserve any existing installation before replacing it.

If macOS blocks this unsigned app as unverified, first verify the downloaded checksum and decide whether you trust the source. Apple documents the per-app **Privacy & Security → Open Anyway** approval path in [Open apps safely on your Mac](https://support.apple.com/en-gb/102445). Availability depends on your macOS/security policy; this project has not qualified Gatekeeper installation behavior.

The release includes `SHA256SUMS.txt` for the uploaded filenames, plus architecture-specific SPDX SBOM, provenance and observations. The unchanged `SHA256SUMS` records the original local metadata paths; the release notes provide the mapping to uploaded filenames.

The original application offers a **+** workflow for discovery or manual IP entry. Discovery uses `_xserveraid._tcp`; controller communication uses the legacy ACPX protocol over **plaintext HTTP**. Monitoring credentials retain reversible legacy obfuscation. Private mode 0600 preference saves are access control, not encryption.

Treat firmware transfer, RAID creation/deletion, disk initialization/erasure, cache or controller network-setting changes, restart/shutdown and rebuilds as actual hardware operations. Do not use them merely to test a feature on production or mounted volumes. These workflows have not been qualified by the offline fixtures.

## Requirements and tested scope

- Choose the package matching your Mac's architecture. Apple silicon uses the native aarch64 package; Intel uses x64. On Apple silicon, choose aarch64 rather than the Intel ZIP; Rosetta x64 testing is an additional offline check.
- The bundled vendor runtime and native helpers have a macOS 11 binary floor. This is not qualification of every macOS version.
- Recorded native checks ran on macOS 26.6.2/local APFS. x64 execution on that host used Rosetta, not physical Intel.
- No external Java installation is required for the downloaded packages. Source builds require the exact compiler and Python versions in the audit locks.
- Signing/notarization, Gatekeeper, additional OS/filesystem combinations and future macOS versions remain unqualified.

## What changed

Compatibility work includes the legacy exception/API bridges, native menu-event adapters, Aqua rendering adjustments, Desktop folder lookup, Help integration, and exact launcher-argument handling. Native user-interface acceptance remains open.

Security and lifecycle work bounds plist/XML and HTTP input, redacts credential-bearing diagnostics, prevents unsafe failed-session continuation on documented paths, and fixes connection-publication, request-ownership and worker-lifetime problems. Those intentional security restrictions differ from legacy behavior; the audit records describe their scope. Healthy controller command formats and polling behavior are preserved within the verified boundaries.

Preference saves use a CodeSource-bound native helper for private atomic replacement, with no insecure in-place fallback. Symlinks and unsafe destinations fail closed; hardlink replacement does not change the other linked file. Existing profile files are not proactively migrated. The original serializer and caller synchronization/error semantics are retained within the tested scope.

Synthetic model-to-file tests exercised the original/current writer and reader combinations. They preserve monitoring values under `Attributes`; management values and their saved flag are absent from the tested registry map. Forget changes the saved flag while retaining the in-memory management value. Actual GUI authentication, full registry/factory integration and broader credential confidentiality remain unverified.

This is compatibility and preservation work, not a rewrite of Apple's interface or a claim of comprehensive security.

## Build and artifact provenance

The public audit28 packages are the frozen unsigned artifacts recorded in [audit/SECURE-PREFERENCES.md](audit/SECURE-PREFERENCES.md), not a new build attributed to later documentation commits.

- Product source: `e005b9a2877133d98af4cf86fd5b625532b06fcb`.
- Isolated package/release tooling: `fd94ee9e3efc4d80e0b0cfba02f77555a4fd0cf8`.
- Corrected runtime gate: `00209235ab05b6398ecd5fba4403d8d29fe3532e`.
- Release tag: `v1.5.1-modern.audit.28`, at `15b4957480269298bff56686bb6e3c4877938fff`, adds the later credential-boundary evidence and completion handoff.
- Common application JAR SHA-256: `bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e`.

Two builds, repeated architecture-specific packages/ZIPs and packaged-code fixtures passed within their documented offline scope. The full record/Git/ZIP/reference verifier is read-only:

```sh
python3 -I -S audit/credential-persistence/verify.py
```

This verifier requires the recorded local build artifacts to be present. It is not an end-user installation step. For source/package reproduction, use the recorded release tooling commit and [reproduction commands](audit/secure-release/reproduction.txt), or create a fresh clean-source build and new qualification evidence. Historical qualification is not relabeled at a later HEAD.

## Project records

- [Source and artifact baseline](AUDIT-BASELINE.md)
- [Architecture](ARCHITECTURE.md)
- [Protocol inventory](PROTOCOL-INVENTORY.md)
- [Dependencies and licensing evidence](DEPENDENCIES.md)
- [Acceptance matrix](ACCEPTANCE-MATRIX.md) and [documented gaps](GAPS.md)
- [Audit28 implementation/release evidence](audit/SECURE-PREFERENCES.md)
- [Credential persistence boundary evidence](audit/CREDENTIAL-PERSISTENCE.md)
- [Current completion and remaining acceptance](COMPLETION-STATUS.md)

The `original/` JAR remains an immutable reference artifact. `/Applications/RAID Admin.app` and real controller data were not modified during the audit.

Apple authored RAID Admin 1.5.1. This project does not imply Apple endorsement. Publication is authorized by the repository owner; original Apple and unresolved legacy dependency redistribution rights remain unresolved, and no legal determination is made. Vendor runtime notices are retained in the bundles. Historical documents describe the pre-publication local handoff; the release notes record the subsequent publication.
