# Operator observations and array highlights — 2026-10-07

This is new evidence after audit28 publication. Frozen release, hardware-audit,
credential-persistence and acceptance records retain their original scope.
This investigation does not qualify the entire application on real hardware.

## User-reported operator session

| Area | Report | Evidence scope |
| --- | --- | --- |
| Discovery | Add System prompted for Java local-network access; the prompt was hidden on another screen. The user identified this as the discovery issue. | User report; no new agent discovery test or permission change. |
| Array & Drives | Switching sides sometimes leaves scattered highlights, e.g. drive 2 on the left and 7, 9–14 on the right. | Open visual defect; exact clicked control and repaint behavior not yet established. |
| Firmware | Selecting Update Firmware opens a file chooser. | Visual only; no transmission. |
| Settings, Email, Utilities, Advanced, Create Array, Delete Array | Screens appear functional; the user did not apply changes. | Visual only; operations are not passed. |
| Update Now | User reports it works. | User-observed action; refresh contents/timing and wire behavior not independently measured. |
| Service ID on/off | User reports both work. | User-observed operation; physical LED evidence, device/firmware identity and request parity not independently recorded. |

The exact installed/downloaded build in that session has not been established
from the user's report. Do not attribute it to audit28 solely from publication.
No controller command, firmware transfer, profile inspection, app startup or
installed-app change was performed by this investigation.

## Source facts

The released common JAR and immutable original have byte-identical
`DriveSelectionPanel`, `SystemInfoPane`, and `SystemInfoPane$ArrayDrivePanel`
classes. This is original application behavior, not evidence of a modernization
regression. Their SHA-256 values respectively are:

```
9aafaaed3b1ea6f6f8c69c2ffa690b39ee8b36096ae8cbbfe8d5194453c9a2ba
76aabb5a94f81ea631c663aede908099b4db3ded29b7db9b6512117d1cc5cbe0
978ab57cce83a9541e73c22a9f8865d3db7e59accaf80d6fc4cf72fb5fba7859
```

`DriveSelectionPanel.syncDriveIcons()` redraws all fourteen icons. Array mode
(4) tints slots whose `driveArrays[i] == arrayIndex`; drive mode (3) tints
`i == driveIndex`. The array list uses 0 for no selection, whereas the drive
panel's no-selection constant is -10. Cleared array-description rows retain a
mouse-release listener and id 0. `ArraySelectionPanel$1` forwards that id in an
ArrayIndex property event. `SystemInfoPane$5` passes its new integer value
directly to `DriveSelectionPanel.setArrayIndex`, then sets array mode.
Consequently a forwarded 0 can highlight every zero-index slot. These slots
need not occupy a contiguous controller bank. This is a source-supported edge
case; it does not establish what happened in the user's session.

`SystemInfoPane.updateInfo` schedules its runnable using
`SwingUtilities.invokeLater`; the runnable calls `setSystem`. A claim that this
normal refresh entry point paints directly on the polling thread is unsupported.
Other callers and concurrent model mutations are not exhaustively qualified.

The pinned macOS runtime's `LWComponentPeer.createImage(width,height)` delegates
to `LWGraphicsConfig.createAcceleratedImage`. Headless raster tests therefore
do not exercise the native image allocation/presentation path. The original
renderer discards drawImage readiness results and does not dispose the acquired
Graphics in this method. Their relevance to the symptom remains unproven.

## Offline observation

[Fixture](../tests/java/uifixture/ArrayHighlightObservation.java) and
[runner](../tools/check_array_highlight.py) use actual original and audit28 JAR
methods, pinned vendor runtimes, verified class origins/resources, a trusted
offline guard, headless AWT and Swing's event thread. No RaidSystem, application
factory, controller or saved profile is constructed. A subclass is allocated
without its constructor; only image allocation (fresh BufferedImage) and the
unrelated model-dependent summary method are substituted. This tests the
rendering boundary, not full application startup or native display behavior.

The fixture checks 1,000 alternating array selections (14,000 tint pixels per
run), a drive-to-array transition, synthetic mixed membership with indices
1/2/0/-10, and the actual cleared ArrayLabel's mouse-release action. It also
checks unchanged drive membership/state. In particular it observes that a
cleared row emits id 0, zero tints scattered zero-index slots, and -10 clears
those highlights. It does not execute the complete SystemInfoPane wiring;
that connection is bytecode evidence.

The first two development attempts did not qualify the fixture: one supplied
the wrong runtime verifier argument, and another omitted resource-bundle
initialization. Neither ran an application or contacted a controller. The
corrected initial fresh-buffer fixture passed original/current on native ARM
and x64 under Rosetta in interpreted mode. Final results and source identities
are recorded separately in `audit/array-highlight/` when qualification finishes.
Rosetta evidence is not physical Intel qualification.

## Open questions and next implementation boundary

The reported symptom is not fixed. Determine whether the user clicked an array
description, a drive icon or a mode selector, whether zero-index drives were
highlighted, and whether covering/uncovering the window removes the stale
pixels. No real operation is required for those observations.

If the zero-index path explains the report, the first proposed patch is confined
to the information view's selection forwarding. Do not change shared
creation/deletion/utility selection semantics or controller identifiers. If it
is native rendering, establish that with a detached guarded UI fixture before
altering image allocation. A successful headless test is not proof of a fixed
macOS display bug. No speculative product patch or new release is justified by
the current evidence.

Claude reviewed the bytecode and fixture design independently. Its proposals
remain advice: its initial thread-race hypothesis was refined by the actual
invokeLater source evidence, and its suggestion that non-headless work requires
approval is not an additional project permission rule. User restrictions govern.
