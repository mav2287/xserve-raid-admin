# Verified starting evidence

This document records facts established from the installed application. Treat
these as starting evidence, not as a substitute for auditing the source tree.

## Installed bundle structure

The installed application contains a small shell launcher and Apple's compiled
Java application rather than a broad source-level port:

- `/Applications/RAID Admin.app/Contents/MacOS/RAIDAdmin`
- `/Applications/RAID Admin.app/Contents/Resources/RAID_Admin.jar`
- icons, `Info.plist`, and signing resources

Recorded SHA-256 values:

- Launcher: `71c0a6f20fb54a227c70a1234891aece5e7a141c2b286cc91364d3f5c4b28ea1`
- JAR: `aa5de223d524e9a518b4a8a6a1adcac066bfe5bc2b96e964ded7716f9b7236`

Recalculate and compare these before relying on them. If they differ, preserve
both artifacts and determine why.

## Launcher behavior

The launcher searches for Java in this order:

1. Java 8 through `java_home`
2. Java 11 through `java_home`
3. Any runtime returned by `java_home`
4. `java` on `PATH`

It then executes the original JAR. This makes behavior dependent on whatever
Java happens to be installed and is not suitable for a reproducible release.
The launcher also uses a fixed `/tmp/RAIDAdmin_icon.png` path.

## Bundle metadata and signing

- Bundle identifier: `com.apple.RAIDAdmin`
- Bundle version: `1.5.1`
- Minimum system version: macOS 10.15
- Local-network and Bonjour declarations are present.
- Advertised/discovered services include `_xserveraid._tcp` and
  `_xserve._tcp`.
- The application is ad-hoc signed, with no Developer ID team identity or
  notarization.
- The installed bundle is owned and writable by the local user.

The compatibility release must not imply that it is an Apple-signed current
release. Give it a separate compatibility-build identity and version while
clearly crediting and preserving the original application.

## Original Java application

The JAR manifest indicates an old build environment:

- Java 1.4.2-era build
- Ant 1.6.2
- Main class `Launcher`

Bundled components observed include:

- Xerces-J 2.0.0
- Xalan Java 2.3.0
- JmDNS 0.2
- Log4j 1.x-era classes

The logging root is configured off, which helps explain operations that appear
to do nothing when exceptions are caught and logged without a user-facing
message.

## Controller communication

- Management traffic uses plaintext HTTP on port 80.
- The connection timeout is approximately 5 seconds.
- The socket timeout is approximately 30 seconds.
- Credentials are placed in `ACP-User` and `ACP-Password` HTTP headers.
- The optional legacy `acp-crypt` mechanism does not protect those HTTP
  headers and is not equivalent to TLS.
- The RAID controller does not provide a modern TLS endpoint that can simply be
  enabled by the client.

Consequences:

- Do not claim that credentials or controller commands are encrypted.
- Recommend an isolated trusted management VLAN or physical network.
- Do not change the wire protocol in the name of security unless the controller
  is proven to support the change.

## Discovery and connection lifecycle

Discovery relies on JmDNS 0.2. This predates modern macOS networking,
multi-interface behavior, and current Bonjour APIs. Direct-IP connection must
remain available even after discovery is repaired.

The communication manager uses a single queue/thread and a persistent
connection. Reconnection backoff may grow as high as one hour. The original
quit path saves preferences and exits the JVM; no explicit graceful protocol
logout was found, although the operating system closes the socket.

The default polling interval is approximately 15 seconds. A full polling cycle
requests numerous controller/status categories. Preserve the original interval
until controlled testing demonstrates that a different rate is necessary.

## Firmware update behavior

The old AWT file dialog applies a filename filter for `.xfb`, but a modern
native chooser may still allow another file to be selected.

The application treats an `.xfb` as a JAR/ZIP-style bundle and examines
manifest entries including:

- `firmware-version`
- `firmware-date`
- `xserveraid-raid-controller-update-image`
- `xserveraid-coprocessor-full-image`
- `xserveraid-coprocessor-update-image`

Expected image paths include:

- `raid-controller/updateROM.bin`
- `coprocessor/updateROM.bin`

No host-side certificate, signature, or digest verification was identified in
the compiled application. The controller may perform its own validation; that
has not been established. Do not claim that an arbitrary image can be flashed.

The constructor can catch parsing/loading exceptions, send them to disabled
logging, and return with no useful message. A successful update should produce
visible progress and a controller restart. Selecting a file with neither result
must be treated as a failed or unconfirmed operation.

## XML parsing

The application constructs a validating SAX parser using the bundled legacy
Xerces code. No explicit external-entity restrictions or resolver were found.
Harden external entity and external DTD behavior, but validate the change
against captured legitimate controller responses before shipping it.

## Password storage

The application references a native JNI `PasswordManager`. No corresponding
native library was found in the application bundle. The application catches the
resulting native-link failure and marks the feature unavailable. Modern Keychain
integration should replace only this OS integration boundary.

## Hardware observations from initial testing

- Both controllers were observed on the LAN at `192.168.33.160` and
  `192.168.33.161`.
- A full cold shutdown and power restoration recovered controller visibility
  after a period in which link activity existed but the controllers did not
  answer ARP.
- Restarting the modernized client later found and reconnected successfully.
- An aggressive full-subnet scan occurred during troubleshooting. It may have
  contributed to resource pressure on old controller management hardware, but
  causation was not established.

Do not turn these observations into a claimed diagnosis. Add controlled network
tests and capture evidence.


## 2026-10-05 source-audit corrections and refinements

The initial entries above are retained as the historical record. The following
new evidence supersedes conflicting assumptions; see
[xserve-raid-admin/AUDIT-BASELINE.md](AUDIT-BASELINE.md).

- The installed launcher hash matches. The historical JAR digest contains only
  62 hexadecimal characters, so it is invalid as SHA-256 and does not match. The
  measured JAR hash is
  `aa5de223d524e9a518b4a8a6a1adcacac066bfe5bc2b96e964ded7716f9b7236`.
  A missing `ac` suggests a transcription error (inference), but historical
  artifact identity remains unresolved. Both strings are retained. An earlier
  conversational statement that both hashes matched was incorrect. The installed
  JAR is **already patched**, not the original reference. The repository candidate
  original hash is `5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449`;
  its manifest main class is `com.apple.xsr.Main`, not `Launcher`. Its official
  Apple acquisition provenance is unresolved.
- Installed plist short version is 1.5.1, build version is 1. Source build uses
  build version 2. Installed-only automatic-termination=false is omitted by
  source packaging. Exact differences and signatures are in the intake manifest.
- Source and installed MRJ/FileManager patch bytecode materially differ. All
  original `com.apple.xsr` application/controller classes match across artifacts.
- On installed Corretto 8 and 11, runtime class-origin probes show bootstrap
  FileManager shadows the replacement inside the JAR. Packaging a shim does not
  prove it runs. Other probed compatibility classes load from app classpath.
- The original XML handler **does implement an EntityResolver** and embeds the
  Apple plist DTD, selected by URL prefix. Other entities fall through. Guarded
  fixtures on original/installed/audit JARs show external file expansion and
  attempted external-DTD networking. Only a disposable synthetic file was read;
  sockets were denied. JAXP selects bundled Xerces on the tested runtimes.
- Original request `toString()` includes password. Do not enable legacy logging.
  The new harness's event allowlisting does not yet secure application logging.
- HTTP defaults to user agent 1.5.1, but ACP header injection overrides it to
  `Apple-Xserve_RAID_Admin/1.6.0`. This existing wire detail must be preserved.
- Source implements plaintext HTTP/80; server-side TLS capability has not been
  tested in this audit. The earlier categorical endpoint claim is not established
  by source inspection alone. Neither HTTP nor acp-crypt protects credentials.
- Unchanged builds have identical entry payloads but different ZIP timestamps and
  archive hashes. The separate audit builder produces matching unsigned app
  content hashes under a locked local JDK. It is not a qualified release.
- No controller was contacted and no GUI app launched during this audit. Initial
  historical hardware observations were not reproduced or converted to diagnoses.

## Accepted project baseline — user direction

Use `original/RAID_Admin_original.jar` from GitHub source commit
`ed171c734f98706fd02524306941625603e1a751` as the authoritative project baseline,
SHA-256 `5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449`.
The user explicitly accepted this repository artifact. The historical digest
issue is retained only as an audit note and does not block implementation or
require further investigation. Keep the repository JAR immutable and hash-checked.
This records the chosen project reference; it does not assert an independently
verified Apple signature.

## audit.4 verified implementation

- Clean source `631b638` reproduces the security candidate twice; full provenance
  is in `audit/security-clean-provenance.json`. The immutable original is unchanged.
- Only the plist resolver and two request diagnostic method bodies are substituted
  within the original protocol/parser classes. The original DTD is copied exactly.
  Independent javap checks and guarded Reader/InputStream/password-change fixtures
  pass; details and limits are in `audit/security-fixtures.json`.
- Both pinned runtime bundle pairs reproduce with vendor signatures and exact
  permissions preserved. `audit/security-bundle-results.json` records digests and
  clean source/packager commits. Runtime fixtures include arm64 and x64 under
  Rosetta, plus installed Java 11 observations; no native Intel-machine claim.
- Original and candidate ACP serialization/retry fixture results still match.
- No GUI launch, controller contact, firmware transmission, mounted-volume test,
  or modification of the installed application occurred. App-wide logging and
  operational acceptance remain open; successful fixtures are bounded evidence.

Bundled diagnostics now recognizes schema 3 and checks runtime/content identity
against repository locks instead of reporting Java absent. It validates the full
file and directory allowlists independently of a self-consistent local manifest.
`audit/bundled-diagnostics.json` records both architectures. Signature validation
is explicitly not evaluated by this tool; the separate bundle verifier performed
it. Malformed/deep/oversized manifests and non-regular files fail without echoing
untrusted metadata. No application or controller is started.

## audit.5 continuation

The root logger now uses a bounded fixed-code appender after a full original-JAR
logging branch inventory and Claude review. Original config bytes are retained
except the root assignment and one appended declaration. Request formatting and
XML hardening remain in place; controller commands, polling and retry code remain
unchanged. Synthetic archive and logging runtime evidence is recorded separately
from hardware acceptance, which remains unperformed.

Clean source `13ac370` reproduces audit.5 exactly. The synthetic archive probe
also ran from that clean fixture commit. The transport fixture additionally
compares forced-OFF logging with the candidate's actual default logging: command
bytes, retries and callbacks match, and captured stderr is exactly one fixed
error code. No raw event is emitted. The three logging probe modes and transport
comparison remain offline; they do not establish visible GUI error handling.

## Apple-served distribution and real archive observation

Bounded read-only acquisition from Apple’s HTTPS server returned the 8,052,021-byte
1.5.1 tarball, SHA-256
`21cf7a8c4e82b925bf9df3d6ea982569bfd24148773ad8dad47f6ddc698ae2c7`.
Its JAR exactly matches the existing immutable GitHub reference; the reference
was not replaced. `audit/apple-distribution-acquisition.json` records provenance.
This establishes bytes served by Apple now, without claiming a historical signature.

The included firmware container SHA-256 is
`32c077ea0ec50a944a996b72978f6d7b9585d17603da847fd4317ebc364dd9a7`.
Its manifest identifies coprocessor 1.5.1 and RAID-controller 1.51c, dated
12/08/2006. The full-image key is absent. Original and candidate wrapper reads
match independent Python image hashes on both pinned runtimes; the updater,
controller model and command classes are not constructed by this probe.

Release notes confirm LUN Masking was removed from the Advanced panel and that
firmware updates alter caches and restart the RAID. These refine preservation
requirements and restricted-operation scope; no such operation was performed.
