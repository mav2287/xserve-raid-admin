# Release checklist

The current artifact is an unsigned audit build, not a qualified release.

- [x] Preserve installed reference and record source/artifact hashes.
- [x] Hash-lock original-JAR candidate and exact local compiler runtime.
- [x] Demonstrate deterministic unsigned app content on this host.
- [x] Separate compatibility identity in audit bundle and diagnostic report.
- [x] Record file-complete dependency inventory with explicit provenance/license unknowns.
- [ ] Authenticate original Apple distribution and resolve redistribution rights/notices.
- [ ] Independently reproduce on a second machine with a documented obtainable toolchain.
- [ ] Select, bundle and qualify a maintained runtime; remove release PATH fallback.
- [ ] Resolve runtime-shadowed FileManager, menu/quit/open-document behavior and Keychain boundary.
- [ ] Provide visible failures and credential-safe application logging.
- [ ] Harden XML while retaining legitimate local plist DTD behavior.
- [ ] Validate firmware preflight without transmission, then qualify transfer only with immediate approval.
- [ ] Complete every acceptance row with observable results or evidence-based unsupported status.
- [ ] Obtain safe real response fixtures and full sanitized wire parity, including timing/reuse.
- [ ] Qualify Intel separately if supported; otherwise document exclusion.
- [ ] Minimize entitlements; sign with Developer ID, notarize/staple, and validate clean-install Gatekeeper behavior.
- [ ] Generate standard release SBOM/provenance and deterministic distributable archive hashes.
- [ ] Publish compatibility matrix, rollback procedure, Apple credit and remaining limitations.

No signing identity, notarization credential, release upload or installation change was used.
