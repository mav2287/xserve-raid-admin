# Residual Array & Drives presentation delay — 2026-10-08

**User report:** audit29 is better. Rapid switching and drive-to-array transitions
can briefly leave old highlights, but the selected item and details remain correct.
The highlights now catch up by themselves before a cover/uncover test is possible;
the correction is not tied to other parts of the interface redrawing.

**Decision:** keep the published audit29 application unchanged. This investigation
adds tests and evidence only. No new launcher options, image allocation, selection
logic, event scheduling, controller commands, polling or retries were shipped.

## Facts from source and bytecode

The original renderer creates and sets all 14 icons on each pass, using mode and
array/drive index. Normal information updates go through
`SystemInfoPane.updateInfo` → `SwingUtilities.invokeLater` → `setSystem` →
`ArrayDrivePanel.updateInfo`. Whole-JAR method-reference inspection finds that
inner method called only by the outer pane and its own constructor. This does not
establish every external/reflection caller or runtime thread.

Actual pinned bundled Corretto 8.504 runtime bytecode, inspected on ARM and x64,
shows `Component.createImage` ultimately delegates through the native peer to
`CGLGraphicsConfig.createAcceleratedImage`. That implementation creates an opaque,
software-backed `OffScreenImage`; its graphics inherit component colours/font.
`Image` defaults acceleration priority to 0.5. Native cached copies/presentation
remain outside these headless checks. Early compiler-JDK dumps are preserved
separately; the `runtime-*` records identify actual bundled runtime binary hashes.

An array-row event calls `setArrayIndex` (render and summary) and then
`setSelectionMode(4)` (render and summary). When already in mode 4, the latter
repeats the icon rebuild. It fires no selection property event, but does cause
additional JLabel icon/accessibility notifications and another model-state read.
A guard could remove that extra work. There is no verified evidence that doing so
would resolve the reported native delay.

The array list and drive-panel selection also have separate state: a drive-icon
array selection updates the detail index without selecting the corresponding list
row. That pre-existing behavior is a separate finding, not an explanation proved
for the user's report, and was not silently changed.

## Accepted offline evidence

Clean fixture source `f760d80` runs the exact, unchanged audit29 JAR from product
source `26d7ec7`. [Results](array-refresh/results.json) record four interpreted
runs: native ARM and x64 under Rosetta, each with a fresh BufferedImage or a
headless JDK OffScreenImage using RGBdefault. Every run passes 300 mixed rounds
with real radio handlers, real DriveIndex/ArrayIndex/SelectionMode listeners and
the original private drive-selection method. Valid arrays, JBOD, cleared/none
sentinels, selected-detail fields, both visible cards and 14 icon sample pixels
are checked. Model arrays remain unchanged; guards report no prohibited operation.

The fixture substitutes detail labels, skips constructors that initialize legacy
profiles, and supplies Component's object lock for the constructor-bypassed panel.
Real class identities, probes, runtime trees and source/Git state are checked.
The `$2`/`$3`/`$4` listener mapping is recorded in the archived disassemblies.
The invisible synthetic message panel is setup, not acceptance of real messages.

These runs verify images assigned synchronously on the event thread. Scheduled
native painting does not run. Single-pixel samples do not qualify every visual
pixel, native colour handling or presentation timing. No real RaidSystem, profiles,
credentials, Main, controller, mounted volumes or installed application were used.
The earlier audit29 negative controls retain their separate original scope; this
new record has no pre-fix negative controls. Early exploratory fixture attempts
that hit a synthetic-home read guard or an uninitialized Component lock are not
accepted runs. No guards were relaxed for the clean runs.

Claude reviewed the investigation, proposed alternatives and fixture, recommending
against speculative product changes. Its final wording/coverage notes led to
explicit mixed JBOD/clear transitions and both card/detail assertions in `f760d80`.

## Unshipped alternatives and remaining question

A local redundant-redraw prototype preserves the final tested state and reduces
one allocation pass for array-to-array events. A software-image prototype was also
considered. Both remain under ignored `build/`; neither is in a released bundle.

Exploratory C1 timing ran concurrently and the ARM runs emitted CodeCache
compilation-disabled diagnostics. Those results are preserved as **rejected timing
evidence**, not healthy compiled qualification or a reliable performance comparison.
No product JVM setting was changed. Even the headless timings without warnings do
not establish native presentation delay or its cause.

**Inference:** correct selection/details with spontaneous highlight recovery point
toward repaint/presentation latency. **Unresolved:** its on-screen duration and
cause have not been measured. Eliminating it would require bounded on-device paint
timing evidence; it does not justify changing controller semantics or forcing
unreviewed repaint/timing behavior. No additional hardware operation is accepted.

Reproduction, with the pinned compiler and a fresh output under build:

```sh
/opt/homebrew/bin/python3 -E -s tools/check_array_transitions.py --jdk /path/to/locked-corretto-8.362/Contents/Home --build build/array-info-common-7 --output build/new-array-transition-check
```

The exact audit29 common artifact and verified local runtime trees must be present.
The [integrity record](array-refresh/integrity.json) hashes archived evidence;
source inputs and probe hashes are in the clean result record. This is offline
correctness evidence, not full application or native GUI qualification.
