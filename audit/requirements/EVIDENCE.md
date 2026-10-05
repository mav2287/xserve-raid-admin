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

