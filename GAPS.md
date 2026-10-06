# Open audit issues

Local issue IDs are stable evidence references; no remote issues were filed.

## G01 — Original provenance and installed/source divergence

Repository original is hash-verified but not authenticated to an Apple download. Installed patches differ from source, including extra MRJ helpers and a different FileManager replacement. The starting EVIDENCE.md JAR digest is only 62 hex characters and cannot authenticate a historical artifact; the launcher hash does match. A transcription error is inferred, not proven. The user has accepted the GitHub JAR as the project baseline: historical digest investigation is closed for this work. Installed/source behavioral divergence remains relevant. See AUDIT-BASELINE.md and entry-diff JSON.

## G02 — Runtime and classloading

Upstream had no bundled JRE and selected arbitrary external Java with a predictable icon path. The pinned packaging path now includes an architecture-specific, vendor-verified Corretto 8 runtime and fixed icon. Runtime FileManager shadows the packaged replacement on tested Corretto 8/11, but the guarded probe confirms its preferences-folder result works. This is a loading fact, not itself a functional defect. Supported OS/CPU/JRE combinations are unqualified. The audit launcher remains historical; the bundled launcher selects only its pinned runtime.

## G03 — OS lifecycle and menus

audit.3 repairs Java 8 EAWT vs Java 9+ Desktop selection and binds About, Preferences, Quit and OpenFiles to original callbacks. Headless adapter tests pass on five runtime/architecture configurations. Object methods no longer invoke callbacks; failures use bounded fixed codes. Print/open-application registration remains an unused original stub. Real native registration, menu delivery, preference persistence and Finder events remain unqualified. A failing original quit/save callback cancels quit; fixed stderr/status codes exist, but a visible in-app failure dialog remains open.

## G04 — Credential-bearing logging

Original AbstractRequestMessage.toString includes password, and AcpxRequestTemplate.toString appends the entire payload. audit.4 replaces exactly these two diagnostic methods with a fixed redacted string, including password-change fixtures. ACP headers still carry plaintext credentials; root logger OFF hides errors. Harness allowlisting does not fix app logging. No real credentials were read or emitted. Application-wide confidentiality and visible-error acceptance remains open.

## G05 — XML external resolution

Original, installed and earlier audit JARs resolve the known Apple DTD locally but permit external file entities and unknown-DTD network attempts. audit.4 substitutes only the resolver method: the exact original embedded DTD is retained and other external identifiers are rejected. Reader/InputStream fixtures, malformed/truncated inputs and external general/parameter entities pass without file or network access attempts. XML expansion/size/depth limits and real controller response fixtures remain open. Legacy external DTD variants outside the original Apple prefix are intentionally blocked and need real-data compatibility assessment.

## G06 — Controller and UI qualification

Discovery, roles/authentication, polling, timing, persistence, reconnect, sleep/wake, dual-controller behavior and terminal UI states are untested. Static catalogs do not prove feature operation. Real sanitized read-only fixtures and controlled hardware environment are absent.

## G07 — Firmware and mutation safety

No known-good firmware package or hardware maintenance context supplied. Preflight, visible errors, confirmation, transfer, acknowledgement, restart and final-version validation remain unqualified. Original updater bytecode also disables/restores disk and controller caches; firmware approval must explicitly cover these ancillary restricted actions. Array/cache/network/power/diagnostic mutations are not authorized for execution without immediate confirmation.

## G08 — Release engineering

Upstream ZIP timestamps prevented exact rebuilds and signing failures were swallowed. The single build entry point is now deterministic and never signs or installs. Separate pinned runtime bundles reproduce on this host; they remain unsigned and lack independent-host reproduction, signed distribution, notarization/Gatekeeper qualification and resolved dependency licenses.

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
