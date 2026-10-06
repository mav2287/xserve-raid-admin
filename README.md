# Xserve RAID Admin

A modernized version of Apple's original RAID Admin application for managing Xserve RAID storage systems on modern macOS (Apple Silicon and Intel).

## About

The original RAID Admin was a Java application bundled with Mac OS X for managing Apple Xserve RAID hardware. It was compiled for Java 1.3 and relied on Apple-specific APIs that no longer exist in modern JVMs, making it unable to run on current macOS versions.

This project contains compatibility patches for the original application. Full functionality, UI behavior, protocol parity, and supported runtime/firmware combinations are not yet qualified. See [AUDIT-BASELINE.md](AUDIT-BASELINE.md) for measured results and limitations.

## Patches Applied

1. **`sun.io.MalformedInputException` shim** — The original `CommunicationsManager` catches this exception class which was removed from modern JDKs. A compatibility shim extending `java.nio.charset.CharacterCodingException` prevents the communications thread from crashing.

2. **`com.apple.mrj.MRJApplicationUtils` replacement** — Selects `com.apple.eawt` on Java 8 and `java.awt.Desktop` handlers on Java 9+; forwards original About, Preferences, Quit and file-open callbacks. Headless bridge tests pass; native menu/event qualification remains open.

3. **`com.apple.eio.FileManager` replacement** — Maps old Mac OS folder type constants (`kDesktopFolderType`, `kPreferencesFolderType`) to real macOS filesystem paths.

4. **`Launcher` wrapper** — Applies Swing UIManager fixes for the Aqua Look & Feel tab text rendering on modern macOS before delegating to the original entry point.

5. **`com.apple.mrj.MRJFileUtils` Desktop bridge** — Repairs the null folder lookup used by firmware selection and event-log export. Other stubs remain unchanged. Offline regression and method-preservation checks pass; dialog workflows remain to be qualified.

## Requirements

- macOS 10.15 (Catalina) or later
- Java 8 or later (Amazon Corretto 8 recommended)

## Install Java (if needed)

```bash
# Using Homebrew
brew install --cask corretto8

# Or download directly from https://aws.amazon.com/corretto/
```

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

Launch **RAID Admin** from Applications (or the build directory). Click the **+** button to discover Xserve RAID systems on your network via Bonjour, or enter an IP address manually.

## Hardware Compatibility

- Apple Xserve RAID (firmware compatibility remains to be qualified)
- Communicates via the ACPX protocol over HTTP to the Xserve RAID coprocessor
- Supports Bonjour/mDNS discovery (`_xserveraid._tcp`)

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
