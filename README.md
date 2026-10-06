# Xserve RAID Admin

Compatibility and preservation work on Apple's RAID Admin 1.5.1 for modern macOS, retaining its existing Apple silicon and Intel runtime support. This audit candidate is not yet operationally qualified.

## About

The original RAID Admin was a Java application bundled with Mac OS X for managing Apple Xserve RAID hardware. It was compiled for Java 1.3 and relied on Apple-specific APIs that no longer exist in modern JVMs, making it unable to run on current macOS versions.

This project contains compatibility patches for the original application. Full functionality, UI behavior, protocol parity, and supported runtime/firmware combinations are not yet qualified. See [AUDIT-BASELINE.md](AUDIT-BASELINE.md) for measured results and limitations.

## Patches Applied

1. **`sun.io.MalformedInputException` shim** — The original `CommunicationsManager` catches this exception class which was removed from modern JDKs. A compatibility shim extending `java.nio.charset.CharacterCodingException` supplies the required catch type. Isolated dispatch fixtures pass; controller operation remains unqualified.

2. **`com.apple.mrj.MRJApplicationUtils` replacement** — Selects `com.apple.eawt` on Java 8 and `java.awt.Desktop` handlers on Java 9+; forwards original About, Preferences, Quit and file-open callbacks. Headless bridge tests pass; native menu/event qualification remains open.

3. **`com.apple.eio.FileManager` replacement** — Provides legacy folder mappings, but the runtime class shadows this replacement on tested Corretto 8/11. The verified MRJ caller bridge below handles Desktop lookup.

4. **`Launcher` wrapper** — Applies Swing UIManager fixes for the Aqua Look & Feel tab text rendering on modern macOS before delegating to the original entry point.

5. **`com.apple.mrj.MRJFileUtils` Desktop bridge** — Repairs the null folder lookup used by firmware selection and event-log export. Other stubs remain unchanged. Offline regression and method-preservation checks pass; dialog workflows remain to be qualified.

6. **Plist entity resolver and request diagnostics** — Three hash-locked method substitutions preserve the original embedded DTD, reject external entities, and redact both credential-bearing request diagnostic methods.

7. **Bounded logging adapter** — Emits only fixed ERROR/FATAL signals, at most once per level per process. No message, exception or context is rendered. This is terminal diagnostic support; GUI error handling remains unqualified.

8. **Secure plist parser boundary** — Uses the pinned bootstrap JDK provider with
   explicit verified resource quotas and external-access denial, retaining the
   original plist Handler, DTD and serializer. Custom entity expansion is bounded
   to 1 MiB. These are deliberate security restrictions; real-response compatibility
   remains open. See [audit.6 evidence](audit/XML-PARSER-COMPATIBILITY.md).

9. **Response allocation ceiling** — An operand-only change selects a bounded
   ByteArrayOutputStream subclass. Advertised response bodies above 16 MiB fail
   before allocation through the existing terminal malformed-input path.
   Security rejection recovery is refined in audit.9; framing remains open. See
   [audit.7 evidence](audit/HTTP-ALLOCATION-GUARD.md).

10. **Bounded response headers** — A per-response stream wrapper caps line,
    field-count and aggregate header input while preserving the original parser.
    Unsafe input fails once without resend; audit.9 retires the rejected connection.
    See [audit.8 evidence](audit/HTTP-HEADER-GUARD.md).

11. **Security rejection recovery** — Exact-marker handling closes the rejected
    connection, preserves one failure callback and lets the next distinct command
    use the original reconnect path. Cleanup failures cannot trigger a resend.
    Invalid numeric/negative lengths are refined in audit.10. See
    [audit.9 evidence](audit/REJECTION-RECOVERY.md).

12. **Invalid length rejection** — Malformed, overflowing and negative response
    lengths use the same safe retirement path, with a fixed message and no raw
    header value/cause. Valid runtime numeric parsing remains unchanged. See
    [audit.10 evidence](audit/INVALID-LENGTH-GUARD.md).

13. **Explicit response framing** — Accepts one Content-Length regardless of
    ASCII letter case. Missing/duplicate lengths and unsupported Transfer-Encoding
    fail through the same safe retirement path. This is an intentional security
    restriction with controller compatibility still unqualified. See
    [audit.11 evidence](audit/RESPONSE-FRAMING-POLICY.md).

## Requirements

Pinned runtime candidates include Corretto 8 for the selected architecture and
need no system Java. Their vendor binaries require macOS 11.0 or later; native UI
and hardware qualification across OS versions remains open. Development builds
require the exact compiler and Python versions recorded in the audit locks.

## Building

Use the exact compiler recorded in `audit/jdk-lock.json` and Python version in
`audit/python-lock.json`. Choose a new output directory for each build:

```bash
./build.sh --jdk /path/to/locked-jdk/Contents/Home --output build/audit-local
```

This produces `build/audit-local/RAID Admin.app` and `provenance.json`.
The unsigned audit bundle retains a historical launcher for comparison. For a
self-contained candidate, use the pinned runtime packaging described below.
No build command installs, signs, launches, or deletes an existing output.
Installation and hardware qualification remain separate acceptance work.

## Usage

The original application offers a **+** workflow for discovery or manual IP entry.
That GUI/network workflow has not been qualified in this audit. Hardware testing
of these candidates requires an approved test context.

Original retry behavior is preserved: a dropped response can cause a mutation to
be sent again without a fixed retry limit; exhausted firmware streams can produce
an empty retry body. Firmware and other mutation workflows remain unqualified.
See [G10](GAPS.md#g10--ambiguous-writes-and-queue-retry-semantics).

## Hardware Compatibility

- Apple Xserve RAID (firmware compatibility remains to be qualified)
- Communicates via the ACPX protocol over HTTP to the Xserve RAID coprocessor
- Contains Bonjour/mDNS discovery implementation (`_xserveraid._tcp`); operation unqualified

## Original Software

The `original/` directory contains the unmodified JAR and icon assets from Apple's RAID Admin 1.5.1. The `patches/` directory contains compatibility Java source. `tools/class_patch.py` performs three hash-locked, method-only substitutions documented in `audit/security-patches.json`.

## Audit tooling

`build.sh` delegates to the [hash-locked audit builder](AUDIT-BASELINE.md#build-reproducibility).
Consult [architecture](ARCHITECTURE.md), [protocol inventory](PROTOCOL-INVENTORY.md),
and [dependencies](DEPENDENCIES.md). No audit artifact is a qualified release.

## Pinned runtime packaging

`tools/runtime.py` fetches only the versioned archives in `audit/runtime-lock.json`,
verifies vendor SHA-256, exact file bytes/modes and Developer ID signatures, and
keeps them in a local cache. `tools/bundle.py` adds one pinned runtime to a verified
clean audit build; it never signs, installs or launches the app. Produce separate
`aarch64` and `x64` artifacts to preserve both architectures. The bundled launcher
uses only that runtime and a committed icon, with no temporary icon or PATH fallback.

The pinned vendor Java binaries require macOS 11.0 or later; this binary floor is
not a claim that every OS version is qualified. These remain unsigned local
candidates, not release artifacts.
