# Current completion and remaining acceptance

The unsigned local audit28 packages are prepared for Intel and Apple silicon.
The application retains Apple's interface and original Java application, with
thin compatibility helpers and narrowly scoped bytecode overrides. The same
application JAR ships in both packages; runtime/native binaries differ by CPU.
This is completed offline implementation and release preparation, with remaining
operational acceptance below. It is not a 100% working or comprehensive security
certification.

This status refines historical unchecked items in RELEASE-CHECKLIST.md and the
credential unknowns in the frozen audit28 documents. Frozen evidence and
requirement snapshots remain unchanged; their execution commits stay authoritative.

| Work | Current evidence or remaining requirement |
| --- | --- |
| Source/artifact provenance and architecture | [Baseline](AUDIT-BASELINE.md), [architecture](ARCHITECTURE.md), immutable original and installed-app comparison recorded. Historical malformed digest investigation closed per user instruction. |
| Controller and UI inventory | [Protocol inventory](PROTOCOL-INVENTORY.md), [acceptance matrix](ACCEPTANCE-MATRIX.md), [gaps](GAPS.md); static/in-memory results do not prove real operations. |
| Compatibility/security implementation | [Audit28 scope](audit/SECURE-PREFERENCES.md) and preceding linked milestones: pinned runtimes, bounded XML/HTTP handling, diagnostic redaction, lifecycle/connection fixes, native integration helpers and private atomic preference saves. Existing protocol, polling and retry semantics preserved. |
| Deterministic local builds, packages and dependencies | Two builds, repeated architecture-specific unsigned archives, packaged fixtures, file-complete SPDX and provenance completed. [Frozen ledger](audit/secure-release/final-integrity.json); [dependency/licensing evidence](DEPENDENCIES.md). Independent second-host reproduction remains open. |
| Save/Forget persistence | [New source and synthetic boundary evidence](audit/CREDENTIAL-PERSISTENCE.md): final run has 320 reader-combination readbacks and eight original/current altered-getter controls. Monitoring is persisted; management and its saved flag are absent in the tested registry map. Actual interface and authentication flow remain unverified. |
| Full interface/startup, menus, Finder, help, dialogs, accessibility and printing | Requires a disposable account/VM without saved RAID profiles and with networking disabled. None available per last user answer. Full Main/factory startup is not safe against the existing production account. |
| Physical Intel | x64 artifacts and Rosetta runs pass; physical Intel/macOS execution requires an available test host. |
| Real discovery, responses, controller operations and firmware transfer | Deferred until actual operational need per user instruction. Production/mounted-volume and restricted operations still need explicit confirmation immediately beforehand. Offline fixtures and firmware preflight/hash inspection are completed within their documented scope. |
| Retry and ambiguous-write risks | Original unbounded retry and single-use firmware-stream hazards remain documented in G07/G10. No silent changes to controller commands, timing or retries. A production replay-safe solution cannot be asserted from the current offline evidence. |
| Stored-credential confidentiality | Private 0600 atomic writes and diagnostic redaction are verified. Legacy reversible monitoring obfuscation remains; no encryption, comprehensive lifecycle confidentiality or migration claim. |
| Signing/notarization/Gatekeeper | Unsigned local packages per user instruction. Requires Developer ID/account setup and separate acceptance. Vendor runtime signature verification does not sign the application. |
| Redistribution/licensing | Apple and unresolved legacy dependency rights require resolution before public distribution. Inventory/notices are recorded; no legal determination or public release occurred. |
| Other macOS/filesystems and future versions | macOS 11 binary floor is not qualification of every OS. Current native tests are on macOS 26.6.2/local APFS. Future macOS support requires future testing; it cannot be guaranteed. |

Local handoff is `build/releases/audit28/`, with architecture-specific ZIPs,
SBOM/provenance/observations and SHA256SUMS. Exact hashes and reproduction are in
[the audit28 handoff](audit/SECURE-PREFERENCES.md#final-local-release-handoff).
Nothing was installed, published or transmitted. `/Applications/RAID Admin.app`
is untouched. Apple remains the author of RAID Admin 1.5.1; modernization does
not imply Apple endorsement or grant redistribution rights.

Rollback handoff: no installed-app rollback is needed because installation has
not occurred. Any later installation requires the user's immediate confirmation
before modifying `/Applications/RAID Admin.app`. Preserve the current installed
bundle and its recorded hashes before an authorized replacement. Existing profile
files must be treated as sensitive and retained privately, never committed or
included in logs. Returning to a legacy writer can lose private atomic-save
protection; an application rollback is not a controller/firmware rollback. No
profile conversion or controller-state change is performed by this handoff.

Further acceptance depends on the environments, accounts or operational need
listed above. These are explicit open requirements, not passed or waived tests.
Until those exist, no additional shipping rewrite is justified by the present
source and fixture evidence. Ordinary future dependency maintenance remains
ongoing work rather than a guarantee of future compatibility or security.
