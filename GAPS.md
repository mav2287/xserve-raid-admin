# Open audit issues

Local issue IDs are stable evidence references; no remote issues were filed.

## G01 — Original provenance and installed/source divergence

Repository original is hash-verified but not authenticated to an Apple download. Installed patches differ from source, including extra MRJ helpers/native FileManager. Resolve source chain before release. See AUDIT-BASELINE.md and entry-diff JSON.

## G02 — Runtime and classloading

No bundled JRE. Launcher selects arbitrary external Java and uses a predictable icon path. Runtime FileManager shadows the packaged replacement on tested Corretto 8/11. Supported OS/CPU/JRE combinations are unqualified. Baseline builder pins an old observed compiler only, not a release runtime.

## G03 — OS lifecycle and menus

Source Java 8 handler lookup uses absent Java 9 interfaces and suppresses failure; quit/open-document/open-application registration is a no-op. Installed source differs. Test save/quit/default window behavior, then repair through a narrow bridge with regression tests.

## G04 — Credential-bearing logging

Original AbstractRequestMessage.toString includes password; ACP headers carry credentials; root logger OFF hides errors. Harness allowlisting does not fix app logging. No real credentials were read or emitted. Application-wide confidentiality and visible-error acceptance remains open.

## G05 — XML external resolution

All three JARs resolve the known Apple DTD locally but expand a disposable external file entity and attempt unknown-DTD network access. Fixture guard prevented the network connection. Preserve legitimate DTD behavior while blocking external resolution; test malformed/oversized/truncated XML and real response fixtures before release.

## G06 — Controller and UI qualification

Discovery, roles/authentication, polling, timing, persistence, reconnect, sleep/wake, dual-controller behavior and terminal UI states are untested. Static catalogs do not prove feature operation. Real sanitized read-only fixtures and controlled hardware environment are absent.

## G07 — Firmware and mutation safety

No known-good firmware package or hardware maintenance context supplied. Preflight, visible errors, confirmation, transfer, acknowledgement, restart and final-version validation remain unqualified. Array/cache/network/power/diagnostic mutations are not authorized for execution without immediate confirmation.

## G08 — Release engineering

Upstream ZIP timestamps prevent exact rebuilds; signing failures are swallowed. New audit content is deterministic on this host but unsigned, has no runtime, and lacks independent-host reproduction, signed distribution, notarization/Gatekeeper qualification and resolved dependency licenses.

## G09 — Native credentials and integration fidelity

No bundled JNI PasswordManager library, no modern Keychain helper. Menus, chooser, Finder document opening, Retina/accessibility/help, metadata behavior, notification and event export/printing are unqualified.
