# Xserve RAID Admin

A modernized version of Apple's original RAID Admin application for managing Xserve RAID storage systems on modern macOS (Apple Silicon and Intel).

## About

The original RAID Admin was a Java application bundled with Mac OS X for managing Apple Xserve RAID hardware. It was compiled for Java 1.3 and relied on Apple-specific APIs that no longer exist in modern JVMs, making it unable to run on current macOS versions.

This project patches the original application to work with Java 8+ while preserving all original functionality, UI, and protocol compatibility.

## Patches Applied

1. **`sun.io.MalformedInputException` shim** — The original `CommunicationsManager` catches this exception class which was removed from modern JDKs. A compatibility shim extending `java.nio.charset.CharacterCodingException` prevents the communications thread from crashing.

2. **`com.apple.mrj.MRJApplicationUtils` replacement** — Bridges the old Mac Runtime for Java handler API to modern `java.awt.Desktop` (Java 9+) with fallback to `com.apple.eawt` (Java 8) for macOS menu integration.

3. **`com.apple.eio.FileManager` replacement** — Maps old Mac OS folder type constants (`kDesktopFolderType`, `kPreferencesFolderType`) to real macOS filesystem paths.

4. **`Launcher` wrapper** — Applies Swing UIManager fixes for the Aqua Look & Feel tab text rendering on modern macOS before delegating to the original entry point.

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

```bash
./build.sh
```

This produces:
- `build/RAID Admin.app` — ready-to-run macOS application bundle
- `build/RAID_Admin.jar` — standalone patched JAR

## Installing

```bash
cp -R "build/RAID Admin.app" /Applications/
```

Or download a pre-built release from the [Releases](../../releases) page.

## Usage

Launch **RAID Admin** from Applications (or the build directory). Click the **+** button to discover Xserve RAID systems on your network via Bonjour, or enter an IP address manually.

## Hardware Compatibility

- Apple Xserve RAID (all firmware versions)
- Communicates via the ACPX protocol over HTTP to the Xserve RAID coprocessor
- Supports Bonjour/mDNS discovery (`_xserveraid._tcp`)

## Original Software

The `original/` directory contains the unmodified JAR and icon assets from Apple's RAID Admin 1.5.1. The `patches/` directory contains the Java source files for all modifications.
