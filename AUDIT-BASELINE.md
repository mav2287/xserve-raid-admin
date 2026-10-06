# Phase 0 baseline audit — 2026-10-05

## Result and scope

**Fact:** repository intake and an offline observation harness are complete. The unchanged upstream build succeeds but is not byte-reproducible. A separate hash-locked audit builder now produces identical unsigned app contents on this machine. **Phase 0 is not closed:** no representative hardware session or packet capture has been taken. No controller was contacted, GUI app launched, production volume tested, firmware transmitted, or installed app modified.

Evidence labels in these reports: **Fact** means directly inspected source/artifact or observed fixture result; **Inference** means a conclusion from that evidence; **Unresolved** means it has not been established. Static method presence is not functional acceptance.

## Source provenance

- Clone: `https://github.com/mav2287/xserve-raid-admin.git`, inside this handoff folder.
- Initial branch `main`, clean tree, commit `ed171c734f98706fd02524306941625603e1a751`.
- One commit, dated 2026-03-18; lightweight tag `v1.5.1-modern` points to it; no submodules.
- Audit work is on `audit/phase-0`. Nothing has been pushed.
- Original handoff records are preserved in [audit/requirements](audit/requirements/).
- Machine: macOS 26.6.2 build 25G83, arm64. Compile toolchain: Amazon Corretto 8 `1.8.0_362`; also observed Corretto 11.0.18 arm64/x86_64 installations. These are observed local toolchains, not a current supported-runtime recommendation.

## Artifact identities

| Artifact | SHA-256 |
|---|---|
| Installed launcher | `71c0a6f20fb54a227c70a1234891aece5e7a141c2b286cc91364d3f5c4b28ea1` |
| Installed patched JAR | `aa5de223d524e9a518b4a8a6a1adcacac066bfe5bc2b96e964ded7716f9b7236` |
| Repository original-JAR candidate | `5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449` |
| Unchanged upstream build 1 JAR | `d218c9ac2182f818056fad0c3168aefc9646ac3e51bab82b102552c158945157` |
| Unchanged upstream build 2 JAR | `e046192e80cd7764ba6b1318ae5ba5b0aa2e6b31d1f2e8866b0b5738e14348b5` |
| Deterministic audit JAR | `e8177fa17ccaf48cebc077e30cc8240abb0ef489dce62fe6f5b796a923375c5f` |
| Deterministic app content-tree digest | `849f1217bb7f2832b5f8d707848e618970cb438702f49a4bfdee5118e15018b9` |

The launcher hash in the starting EVIDENCE.md matches. The recorded JAR value has only **62 hexadecimal characters** (`aa5de223d524e9a518b4a8a6a1adcac066bfe5bc2b96e964ded7716f9b7236`) and is not a valid SHA-256; it differs from the measured 64-character hash above. **Inference:** the missing `ac` suggests a transcription error. **Unresolved:** the malformed historical digest cannot authenticate the historical JAR. Both strings are preserved; no historical artifact corresponding to a valid alternate digest was supplied. An earlier conversational statement that both matched was incorrect. The installed bundle was copied with `ditto` to the parent workspace's `audit/reference/RAID Admin.app`; all regular-file hashes match the installed source. Original-build copies are in parent `audit/baseline-1` and `audit/baseline-2`. [intake-provenance.json](audit/intake-provenance.json) records every file hash, original icon hashes, directory hash definitions and differences. No credential stores were copied.

**Unresolved:** the repository asserts Apple origin, but supplies no original Apple download, installer hash, acquisition chain, release signature, or redistribution grant. The candidate is verified against its recorded repository hash, not authenticated as an official Apple distribution. Its manifest says Ant 1.6.2, Apple Java 1.4.2-50, main class `com.apple.xsr.Main`; app resources say 1.5.1 / 1.5.1GMc5. Preserve it unchanged. The user has accepted this repository artifact as the project baseline; independent Apple provenance is not a prerequisite for the authorized work.

## Installed versus source-built application

The full comparison is in [installed-build1.json](audit/installed-build1.json) and the intake manifest.

- JAR entries: candidate 3,043; installed 3,049; source-built 3,047 (non-directory entries).
- All original `com.apple.xsr` application/controller classes are byte-identical among these artifacts. Changes are confined to compatibility classes and manifest.
- Installed-only classes: `MRJApplicationUtils$3` and `$4`. Installed `MRJApplicationUtils` includes separate EAWT fallback logic absent from checked-in source. Both skip quit/open-document handling.
- Launcher, FileManager, MRJ bridge and exception-shim class bytes all differ between installed and built. For Launcher and shim, disassembly suggests equivalent instructions; class metadata/compiler differences are a plausible explanation, not authenticated source provenance. FileManager entry bytes differ, but the initial native-method interpretation was wrong: javap had selected the runtime class. Direct archive-byte disassembly now shows the installed replacement also uses Java folder mappings and includes extra folder constants.
- Manifest: installed retains Ant/Apple creation metadata with patched `Main-Class: Launcher`; rebuilt manifest replaces it with Corretto creation metadata. Therefore the installed manifest is not evidence of an unmodified JAR.
- Shell launcher differs in comments, formatting, PATH fallback implementation and missing-Java dialog text. Java selection order, JVM flags and fixed icon path remain substantially the same.
- Plist differences: `CFBundleVersion` 1 → 2, and installed `NSSupportsAutomaticTermination=false` is absent from source build. Other parsed values match.
- Both icons match byte-for-byte. Two signature-resource files differ as expected from changed inputs; the other signature files match. The installed signature passes local strict verification and is ad-hoc, no Team ID. This is not Developer ID or notarization qualification.

## Build reproducibility

The complete upstream `build.sh`, all Java patches, README and ignore rules were read before running anything. It compiles four sources, constructs plist/launcher inline, and swallows signing failures with `|| true`. No other packaging, signing, entitlement, test or release logic exists at intake.

Two `./build.sh` runs have identical JAR entry bytes and order but 11 different entry timestamps. Their whole-JAR hashes and dependent signatures differ. There is no JDK pin, dependency hash guard, immutable-input assertion or supported-runtime bundle.

The new builder uses a deterministic **allowlisted transformation**, not an application rewrite. It preserves every original non-allowlisted entry, compiles exactly six patch class files from the existing four sources, and writes a sorted, fixed-date, stored ZIP. Only the manifest payload differs from the unchanged upstream source build. It does not change protocol classes, polling, retry timing or UI patch source. A classpath overlay remains a later option; overlay precedence has not been qualified here.

Run from the cloned repository:

```sh
python3 tools/baseline.py --jdk "$(/usr/libexec/java_home -v 1.8)" --output build/audit-fresh
python3 tools/diagnose.py build/audit-fresh
# Repeat with another new output directory, then compare:
python3 tools/baseline.py --jdk "$(/usr/libexec/java_home -v 1.8)" --output build/audit-repeat
python3 tools/verify_builds.py build/audit-fresh build/audit-repeat
python3 -m unittest discover -s tests -v
python3 tools/check_parity.py --jdk "$(/usr/libexec/java_home -v 1.8)" \
  "build/audit-fresh/RAID Admin.app/Contents/Resources/RAID_Admin.jar"
python3 tools/inventory.py --jdk "$(/usr/libexec/java_home -v 1.8)"
```

Output must be a new directory. The builder fails before compilation if the original JAR or any file in the locked JDK differs. [jdk-lock.json](audit/jdk-lock.json) identifies all 224 local JDK files, aggregate `da86c7dfbdcc7b593e6871732c3a14de55bc410938cde2081d9a136bac21a376`. It does not download anything. Reproducibility is demonstrated for this exact toolchain on this host; independent-host reproducibility is unresolved. Python version is recorded, not pinned.

The audit bundle has identifier `org.xserve-raid-admin.audit` and version `1.5.1-modern.audit.1`; diagnostics report Apple baseline separately. It is unsigned, unnotarized and unqualified. The inherited launcher still selects external Java and uses a fixed temporary icon path. There is **no bundled runtime**, and the original About dialog remains unchanged. Do not mistake this audit artifact for a release.

App digest = SHA256(canonical JSON mapping sorted relative regular-file paths to file SHA256), excluding times, modes and xattrs. This is not a DMG/ZIP hash. Timestamp, source commit/dirty state, builder, toolchain, inputs and signing status are recorded outside the reproducible app payload in `provenance.json`; those records intentionally differ between runs. [Build 1](audit/deterministic-build-1.json), [build 2](audit/deterministic-build-2.json) record the initial implementation run, including its dirty status and exact input hashes.

## Tests and acceptance limits

- Four Python tests pass: immutable-input rejection, deterministic ZIP ordering/metadata, unsafe entry rejection, and diagnostic event allowlisting including sensitive/nested fields.
- Two independent audit builds have identical full app file maps. Every original non-allowlisted JAR entry remains identical; all six generated class bytes match the unchanged upstream build.
- [Offline parity](audit/parity-results.txt): ten read-request serializers and ten in-memory HTTP responses match the candidate, installed and audit JARs on Corretto 8. A JVM guard denies sockets and verifies that denial. No actual ACP credentials are used.
- This harness exercises `HttpRequest`, not `AcpxConnection.addHeaders`, so it does **not** prove ACP authentication/header behavior, transport persistence, timing, retries, UI state or hardware parity. Its synthetic `OK` responses are not real controller plist fixtures.
- [XML observation](audit/xml-observation.txt): known Apple DTD resolves locally; a disposable synthetic external file entity expands; unknown external DTD attempts networking, blocked by the harness. Security acceptance fails for the baseline.
- [Java 8 API probe](audit/java8-api-probe.txt) confirms Desktop exists but modern AboutHandler does not; [Java 11](audit/java11-api-probe.txt) has both. Source inspection shows swallowed reflection failures without EAWT retry after this failure. Menu behavior remains unqualified.
- Diagnostics enumerate interface names and local artifact hashes only; discovered controllers explicitly say **not run**, not “none found.” They never inspect preferences, Keychain, credentials, payloads or legacy logs. Harness event allowlisting is not an application-wide logging fix.

## Highest risks and next milestone

1. Legacy XML permits external resolution; legacy request `toString()` includes the password. Do not enable legacy debug logging.
2. Source and installed compatibility code disagree; Java 8 menu fallback is defective, quit/open-document hooks are omitted, and filesystem bridge API coverage is incomplete.
3. Firmware failure reporting, preflight, acknowledgement and recovery are unqualified. Several diagnostic operations can mutate data despite their names.
4. Discovery/interface behavior, session cleanup, one-hour backoff, saved credentials/JNI and arbitrary JRE selection remain unresolved operational gaps.
5. No hardware qualification, exhaustive runtime feature inventory, authoritative Apple artifact provenance, current-runtime qualification, redistribution conclusion, release signing or notarization.

The completed first implementation milestone is the deterministic audit build plus offline observation tooling. Next: a separately tested, narrow MRJ handler bridge correction preserving original quit/save semantics, followed by pinned runtime evaluation and credential-safe application error reporting. XML hardening must retain the existing legitimate local DTD behavior and pass real sanitized response fixtures. Hardware work needs identified disposable/unmounted targets and immediate approval for every listed restricted operation.

## Additional runtime finding

[Class-origin probes](ARCHITECTURE.md#runtime-class-origin-correction) show that FileManager is supplied by the bootstrap runtime on both installed Corretto 8 and 11; the source replacement is shadowed. The MRJ/shim/Launcher classes do load from the app classpath. This adds a high-priority compatibility gap and means ordinary overlay ordering is insufficient for that OS boundary. XML observations were repeated against both installed and deterministic JARs with the same unsafe external-resolution outcomes. No arbitrary files were read; only a newly created sentinel was used and deleted.

## Reproducing XML and runtime observations

Run from the source repository with the locked Java 8 compiler. These fixtures use no application entry point; XmlObservation prohibits networking and deletes its synthetic temporary file.

```sh
mkdir -p build/fixture-classes
"$(/usr/libexec/java_home -v 1.8)/bin/javac" \
  -cp original/RAID_Admin_original.jar -d build/fixture-classes \
  tests/java/XmlObservation.java tests/java/ApiProbe.java tests/java/ClassOriginProbe.java
"$(/usr/libexec/java_home -v 1.8)/bin/java" -Djava.awt.headless=true \
  -cp build/fixture-classes:original/RAID_Admin_original.jar XmlObservation
"$(/usr/libexec/java_home -v 1.8)/bin/java" -Djava.awt.headless=true \
  -cp build/fixture-classes ApiProbe
"$(/usr/libexec/java_home -v 1.8)/bin/java" -Djava.awt.headless=true \
  -cp "build/fixture-classes:build/audit-fresh/RAID Admin.app/Contents/Resources/RAID_Admin.jar" ClassOriginProbe
```

Repeat XmlObservation with the preserved installed/audit JAR on the classpath to compare them. Repeat ApiProbe/ClassOriginProbe with the explicitly observed Java 11 path to reproduce the second runtime finding. The expected baseline XML result is unsafe external resolution; this observation is not a passing security test.

## Accepted project baseline — user direction

Use `original/RAID_Admin_original.jar` from GitHub source commit
`ed171c734f98706fd02524306941625603e1a751` as the authoritative project baseline,
SHA-256 `5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449`.
The user explicitly accepted this repository artifact. The historical digest
issue is retained only as an audit note and does not block implementation or
require further investigation. Keep the repository JAR immutable and hash-checked.
This records the chosen project reference; it does not assert an independently
verified Apple signature.

## Reviewed tooling correction milestone

The Claude consultation and corrective addendum are preserved under
`audit/claude-review/`. The empty request-call table and platform-class javap
substitution are fixed. Original protocol classes remain untouched.

Builds now use an allowlisted subprocess environment, empty Java 8 extension and
endorsed directories, UTF-8/US/UTC settings, an exact Python version lock, and a
no-symlink file traversal policy. JVM option values are never logged. The JDK lock
is enforced by the builder, inventory, probe and serialization commands.

Schema-2 provenance records file modes. The new app digest includes file hashes
and integer permission modes; the earlier content-only digest remains separately
recorded. `tools/verify_builds.py` checks both artifacts against
`audit/expected-build.json` and the current recorded inputs. Intentional updates
require `--update-expected --reason 'reviewable explanation'`; the previous record
hash is retained, and Git preserves the full prior record. Fourteen unit tests
cover interface extraction, isolation, symlinks, toolchain mismatch, mode loss,
self-consistent-but-unexpected artifacts, non-allowlisted changes and diagnostics.

The original request serializer is still only a limited smoke/regression fixture.
Real ACP header/logging/response/queue failure tests remain the next gate.

User constraints: both Apple silicon and Intel are required. Available hardware
has production or mounted volumes, so no hardware testing or GUI startup with
saved targets is performed. Offline work continues without changing controller
commands, polling or retries.

## audit.2 — Desktop lookup repair and transport characterization

The first application repair replaces only the used MRJFileUtils Desktop lookup.
Two deterministic builds (`build/folder-1` and `build/folder-2`) match with JAR
SHA-256 `bfd58355316a16472a7b030412435f47e3e646de0f52291bebc4a1bf5b0c2d8f`
and mode-inclusive bundle hash
`17cf76a350650b6ac76cefeb57ecfbd07d53bbc9463b1f5fa2b79f5251e348e0`.
All nonallowlisted original entries remain unchanged. The exception shim is
supplied explicitly when characterizing the original dispatch code on modern Java.
See `audit/folder-fix-results.json`, `audit/transport-observation.json`, and the
Claude design/implementation reviews for exact scope and limits. No installed
app, controller, production volume, credential store or GUI was accessed.

## audit.3 — macOS handler bridge

About/Preferences select the correct API on Java 8 and 11. Quit now delegates
to the original save-and-exit callback; a returning/failed callback cancels the
platform quit. Finder file events invoke the original per-file alert callback.
No controller command, polling or retry implementation changed. Headless bridge
results are in `audit/menu-runtime-fixtures.json`; native GUI behavior remains open.
