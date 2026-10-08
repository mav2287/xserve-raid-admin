RAID Admin 1.5.1 modernization audit28 — unsigned audit packages for Apple silicon and Intel. Apple’s original Java interface and controller application are retained, with a pinned bundled runtime, thin compatibility helpers and narrowly scoped overrides.

Downloads:
- **Apple silicon (M-series):** `RAID-Admin-1.5.1-modern.audit.28-aarch64-unsigned.zip`
- **Intel:** `RAID-Admin-1.5.1-modern.audit.28-x64-unsigned.zip`
- `SHA256SUMS.txt` verifies the downloads and architecture-specific SBOM/provenance/observations assets.

**No Java installation is required. Each ZIP bundles Corretto 8.504.04.1 for its architecture.**

These are **unsigned and unnotarized audit builds**, not a claim of complete operational acceptance. Native ARM and Rosetta x64 offline fixtures passed; physical Intel, full GUI/startup and actual controller workflows remain unqualified. Legacy HTTP is plaintext, and monitoring credentials retain reversible legacy obfuscation; private preference saves are access control, not encryption. Transport/firmware limitations remain documented. Healthy controller command formats and polling are preserved within verified boundaries; automatic resend after ambiguous failures was intentionally removed on the documented containment paths for safety. Restricted operations and production-volume tests still require explicit confirmation immediately beforehand.

Provenance: product source `e005b9a2877133d98af4cf86fd5b625532b06fcb`; isolated release/package tooling `fd94ee9e3efc4d80e0b0cfba02f77555a4fd0cf8`; corrected runtime gate `00209235ab05b6398ecd5fba4403d8d29fe3532e`; this tag `15b4957` includes the later credential-boundary evidence and completion handoff. The packages are the existing frozen audit28 artifacts, not a rebuild attributed to the tag. Both use common JAR SHA-256 `bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e`; runtimes/native helpers differ by architecture.

See [completion and remaining acceptance](https://github.com/mav2287/xserve-raid-admin/blob/v1.5.1-modern.audit.28/COMPLETION-STATUS.md), [frozen audit28 evidence](https://github.com/mav2287/xserve-raid-admin/blob/v1.5.1-modern.audit.28/audit/SECURE-PREFERENCES.md), and [credential boundary evidence](https://github.com/mav2287/xserve-raid-admin/blob/v1.5.1-modern.audit.28/audit/CREDENTIAL-PERSISTENCE.md).

Apple authored RAID Admin 1.5.1. This modernization does not imply Apple endorsement. Original Apple and unresolved legacy dependency redistribution rights remain unresolved; publication is not a legal determination. Vendor runtime notices are retained in the bundles.

No controller operation, real-profile access or modification of `/Applications/RAID Admin.app` occurred while preparing these packages. This audit release is designated GitHub Latest at the repository owner’s direction. That designation does not establish completed signing, notarization, hardware or controller qualification. Previous release assets remain available.

This publication is explicitly authorized by the repository owner. The source-tag documentation records the pre-publication local handoff; its statements that no public release occurred describe that earlier state and are superseded for publication status by this release. Redistribution rights remain unresolved. Independent second-host reproduction and Gatekeeper qualification remain open. Vendor runtime signatures do not sign the application.

The unchanged original `SHA256SUMS` uses the frozen local layout. Uploaded metadata is mapped as follows; `SHA256SUMS.txt` separately checks the actual uploaded filenames:

| Uploaded asset | Original frozen path |
| --- | --- |
| RAID-Admin-audit28-aarch64-SBOM.spdx.json | aarch64/SBOM.spdx.json |
| RAID-Admin-audit28-aarch64-provenance.json | aarch64/provenance.json |
| RAID-Admin-audit28-aarch64-release-observations.json | aarch64/release-observations.json |
| RAID-Admin-audit28-x64-SBOM.spdx.json | x64/SBOM.spdx.json |
| RAID-Admin-audit28-x64-provenance.json | x64/provenance.json |
| RAID-Admin-audit28-x64-release-observations.json | x64/release-observations.json |

ZIP filenames are unchanged in both checksum files.

