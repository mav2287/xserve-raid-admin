# Release checklist

The current artifact is an unsigned audit build, not a qualified release.

- [x] Preserve installed reference and record source/artifact hashes.
- [x] Hash-lock original-JAR candidate and exact local compiler runtime.
- [x] Demonstrate deterministic unsigned app content on this host.
- [x] Separate compatibility identity in audit bundle and diagnostic report.
- [x] Record file-complete dependency inventory with explicit provenance/license unknowns.
- [x] Accept GitHub repository JAR as the project baseline per user direction.
- [ ] Resolve redistribution rights/notices.
- [ ] Independently reproduce on a second machine with a documented obtainable toolchain.
- [x] Pin and bundle Corretto 8 for both architectures; remove bundled-launcher PATH fallback.
- [ ] Qualify that runtime with native GUI, controller workflows and physical Intel hardware.
- [ ] Qualify runtime FileManager behavior; repair menu/quit/open-document integration and Keychain boundary.
- [ ] Provide visible failures and credential-safe application logging.
- [x] Block external entity resolution while preserving the original embedded plist DTD in offline fixtures.
- [ ] Qualify real controller plist responses and XML resource limits.
- [ ] Validate firmware preflight without transmission, then qualify transfer only with immediate approval.
- [ ] Complete every acceptance row with observable results or evidence-based unsupported status.
- [ ] Obtain safe real response fixtures and full sanitized wire parity, including timing/reuse.
- [ ] Preserve existing Intel and Apple silicon support; qualify physical machines separately.
- [ ] Minimize entitlements; sign with Developer ID, notarize/staple, and validate clean-install Gatekeeper behavior.
- [ ] Generate standard release SBOM/provenance and deterministic distributable archive hashes.
- [ ] Publish compatibility matrix, rollback procedure, Apple credit and remaining limitations.

No signing identity, notarization credential, release upload or installation change was used.
