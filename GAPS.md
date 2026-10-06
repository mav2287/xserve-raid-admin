# Open audit issues

Local issue IDs are stable evidence references; no remote issues were filed.

## G01 — Original provenance and installed/source divergence

Repository original is hash-verified but not authenticated to an Apple download. Installed patches differ from source, including extra MRJ helpers and a different FileManager replacement. The starting EVIDENCE.md JAR digest is only 62 hex characters and cannot authenticate a historical artifact; the launcher hash does match. A transcription error is inferred, not proven. The user has accepted the GitHub JAR as the project baseline: historical digest investigation is closed for this work. Installed/source behavioral divergence remains relevant. See AUDIT-BASELINE.md and entry-diff JSON.

## G02 — Runtime and classloading

No bundled JRE. Launcher selects arbitrary external Java and uses a predictable icon path. Runtime FileManager shadows the packaged replacement on tested Corretto 8/11, but the guarded probe confirms its preferences-folder result works. This is a loading fact, not itself a functional defect. Supported OS/CPU/JRE combinations are unqualified. Baseline builder pins an old observed compiler only, not a release runtime.

## G03 — OS lifecycle and menus

audit.3 repairs Java 8 EAWT vs Java 9+ Desktop selection and binds About, Preferences, Quit and OpenFiles to original callbacks. Headless adapter tests pass on five runtime/architecture configurations. Object methods no longer invoke callbacks; failures use bounded fixed codes. Print/open-application registration remains an unused original stub. Real native registration, menu delivery, preference persistence and Finder events remain unqualified. A failing original quit/save callback cancels quit; fixed stderr/status codes exist, but a visible in-app failure dialog remains open.

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

## G10 — Ambiguous writes and queue retry semantics

Source requeues the same transaction on non-parse IO failure, without a bounded
attempt count. The callback is retained in the transaction; the failed iteration
suppresses an immediate result and later attempts can notify it. A command may
have reached the controller before a connection failure, making a repeat unsafe.
Firmware uses a single-use stream; a retry may fail before sending anything.
The memory-only fixture now observes two identical sends after one dropped response,
five after four drops, and one eventual callback with retained context. Parse errors
produce -103 without requeue. Synthetic single-use firmware streams either throw
before a second send or produce a zero-length second body, depending on stream
behavior. See `audit/transport-observation.json`. Real reconnect/backoff, queue
ordering and actual firmware archive streams remain unqualified. No retry behavior
has been changed.

## G11 — MRJ folder lookup

Confirmed offline: the unpatched MRJFileUtils returns null for Desktop. Firmware
and event-log Save call getPath() on that result. Fixed in audit.2: the used
single-argument overload returns the user Desktop for its singleton constant.
`tools/check_folders.py` verifies unchanged ABI and instructions for every other
method, plus null/custom-type/unused-overload behavior. No directories are created.
The two dialog callers are statically verified; GUI workflows remain unqualified.
See `audit/folder-fix-results.json`.
