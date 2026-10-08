# Continuing Array & Drives highlight investigation

This is development diagnostic evidence, not a new product release or a claim
that audit30 resolves native presentation. The product JAR remains audit30
`3875edc404c7773d602fdb834bf8090dcb73b53a30d6306bc2fb09951a542059`.

## Operator evidence

After audit30, rapid drive/array and side changes still sometimes leave several
highlights missing for approximately 1–2 seconds, then self-correct. The operator
reported drive 4 missing when changing to an array containing drives 1–7, and a
repeatable troublesome location near drive 6's right edge. Asked about that
location, the operator answered “I see multiple drives fail to highlight.”
This does not establish that the selected item or details are wrong.

## Facts from original bytecode and runtime inspection

- Every icon pass creates fourteen fresh images and calls each original
  `JLabel.setIcon`; the bundled implementation requests repaint when icon identity
  changes. Drive and array selections use the same blue pixels for a selected
  assigned drive. A missing previously selected drive therefore requires further
  explanation; a delayed final blue image alone is insufficient.
- Drive labels occupy touching 18-point bounds. Drive 6 abuts drive 7. The
  controller-side divider is between drives 7 and 8. Hit testing uses complete
  label bounds, not transparent pixels.
- Original mouse press/release sets/clears a shared drag-selection flag. Mouse
  entry can select a neighboring label while that flag is set; it does not test
  the button-down mask. This permits drag selection but does not prove a stuck
  flag in the operator's case.
- Original icon-rendering Graphics are not disposed. This is a resource-management
  finding; its relation to the reported delay is unproved.
- Inspection of actual `Gestalt.gatherInfo` refines the earlier fixture assumption:
  that method reads look-and-feel, OS/Java version and resource strings. It does
  not itself load saved RAID profiles. This allowed an original-constructor
  component fixture, without constructing the information pane or application.

## Isolated native pilot

[Source](ui-selection-diagnostic/NativeDriveObservation.java) and
[results](ui-selection-diagnostic/native-pilot.stdout) use the actual
original drive-panel constructor, layout, renderer and mouse listeners, synthetic
membership/statuses and a null controller. Model-dependent summary is suppressed;
tracking labels retain geometry and listeners. Only tagged synthetic mouse events
are accepted. No Robot, screen capture, real profiles or controller actions run.
A fake home and Java guard are used; native OS preference writes outside Java
are unmeasured.

120 mixed selection transitions completed with correct per-drive image oracles;
1,694 label paints were observed, no stale generations at timer ticks, and the
largest measured event-to-Java-paint interval was 36,990,041 ns. This ARM pilot
uses interpreted execution and default graphics-transform scale 1.0. It does not
measure framebuffer presentation or reproduce the full production hierarchy.
The numeric checks did not detect the operator's delay; they do not close acceptance.

## Temporary numeric-only observer

The [observer source](ui-selection-diagnostic/SelectionObserver.java) is a
separate diagnostic agent, not a product patch. It uses no transformer, controller
method, GUI action, text capture or profile/credential field. Fixed fields yield
numeric selection indices, memberships, statuses, icon pixels, change counters,
mouse coordinates and EDT indicators. Initial non-buffered icons are marked
unmeasured. Snapshots are coalesced on the EDT; file writes run off the EDT.

The observer keeps at most 4,096 records, rejects unsafe sink metadata, holds an
opened channel, and requires a final END trailer for a complete trace. It stops
30 seconds after the first information-view press, or after 90 seconds idle,
removes its listeners and releases panel references. Agent classes remain loaded
until application exit. This observation can affect timing slightly; it cannot
prove screen-presentation timing.

[ARM](ui-selection-diagnostic/observer-aarch64.stdout) and
[Rosetta x64](ui-selection-diagnostic/observer-x64.stdout) headless fixtures pass
numeric snapshot checks, forced callback-failure containment, null/partial bind
cleanup, bounded-buffer END retention, unchanged synthetic model, and a throwing
listener negative control. A separate disposable process passes actual attachment,
worker completion and cleanup. Private sink checks accept a valid file and reject
wrong directory/file modes, nonempty files, symlinks and hard links. No installed
application or product JAR is changed. Claude reviewed the source and the fixes;
[follow-up](ui-selection-diagnostic/claude-followup.json) reports no blocking safety
issue, with minor counter races at shutdown explicitly remaining.

[Pilot receipt](ui-selection-diagnostic/pilot-receipt.json) binds snapshots and
local outputs. These are development runs from ignored scratch inputs, not a
clean-source release qualification. Earlier failed compile/setup/attach-fixture
pilots are excluded. No remaining functional fix is inferred from these tests.

## Unresolved

The live information-view trace must be correlated with an operator reproduction
before choosing another patch. Correct model/icons with late visible highlights
would support a presentation problem; incorrect or late icons, or off-EDT changes,
would support a selection/refresh problem. Neither cause is established yet.
No polling, commands, retry timing or selection semantics should change on this
pilot evidence alone.

The first [live trace](ui-selection-diagnostic/live-idle.stdout) completed on the
unchanged local audit30 candidate, with one information panel, one initial state
and zero mouse events. Its final trailer reports no failure, dropped records or
remaining listeners. The operator did not reproduce the symptom during this
window; this is attachment/cleanup evidence only. The installed application was
not modified. A new trace requires coordinated operator reproduction.

## Operator correction: native pilot visibly reproduces the defect

The operator subsequently clarified that missing highlights were visible in the
small automated drive-panel fixture itself. This is visual reproduction evidence
in an isolated synthetic view, even though the fixture's image hashes and Java
paint counters passed. Calling that run a non-reproduction was too strong.
The numeric checks do not measure screen pixels. This substantially narrows the
investigation toward image rendering/presentation, but does not identify a
specific image-cache, damage-region or compositing defect. The normal application
observer's zero-click result remains unchanged and is a separate run.

An offline A/B/C comparison now retains the same original renderer, geometry,
tagged inputs and synthetic model. A uses original native images; B changes only
image acceleration priority to zero; C supplies opaque TYPE_INT_RGB software
images at priority zero. A bounded identity set proves that the tested images
came through the override; B/C priority and C type are checked for every oracle.
Each process uses 480 rounds at a 40-ms timer interval, with independent per-drive
oracles. This is a diagnostic experiment, not a product change or confirmed fix.
Opaque software images may differ in rendering details. Separate processes
avoid retaining pipeline state between variants. No Metal property is used:
Claude's suggested Metal switch was not established for this bundled Java 8.

Claude's [A/B/C design review](ui-selection-diagnostic/claude-ab-design.json)
and [source review](ui-selection-diagnostic/claude-ab-source.json) support this
offline experiment, not a product fix. The source review identified robustness
gaps: retain generated images still held by labels when pruning provenance; stop
the timer on all terminal paths; preserve setup failures before checking paint
coverage; measure only the first paint of a changed icon. These are corrected in
the [second source snapshot](ui-selection-diagnostic/NativeDriveAB.java). A suggested
System.exit was not adopted because the fixture guard prohibits process exit;
timer stop, frame disposal and the bounded subprocess provide termination.
The initial A/B/C run is a preliminary scratch observation; the corrected
reverse-order run supplies the archived fixture results.

The corrected reverse-order C/B/A pilot completed successfully in all three
processes: 480 transitions, 13,510 images created through the proved override,
6,734 Java label paints, no stale generations at timer ticks, and zero guarded
prohibited operations each. Largest first-paint delays were C 39,292,042 ns,
B 38,782,791 ns, A 41,518,583 ns. The recorded graphics paint scale was 1.0.
[Receipt](ui-selection-diagnostic/image-path-receipt.json) binds the local source,
classes and outputs; [A](ui-selection-diagnostic/image-path-A.stdout),
[B](ui-selection-diagnostic/image-path-B.stdout), and
[C](ui-selection-diagnostic/image-path-C.stdout) remain numeric observations.
The operator comparison of visible missing highlights is pending. No variant is
accepted as a fix, and no new product release is created.

## Operator pacing correction and held-selection test

The operator could not judge the 40-ms flashing sequence and required at least
2–3 seconds between selections. A 2.5-second attempted sequence was also reported
as flashing and was stopped. Those visual reports are not accepted as a clean
A/B/C comparison. Only the synthetic test JVM was stopped.

A single original-image-path test was then run with a 3,000-ms one-shot timer,
restarted after each completed transition, a visible step counter and a minimum
interval assertion. The operator reported: “It worked and did not reproduce the
error.” This is a clean visual observation of that paced original-path fixture;
it does not establish resolution of the intermittent normal-application defect.
No product patch is derived from it. Native fixture guards and synthetic inputs
remain unchanged. Completed numeric run results are recorded below.

The held-original test completed 12 transitions, 406 images and 182 Java
paints with zero stale generations and zero guarded prohibited operations. Its
maximum first-paint delay was 50,893,958 ns. [Source](ui-selection-diagnostic/NativeDriveHeld.java)
and [output](ui-selection-diagnostic/held-original.stdout) preserve this pilot.
The operator next requested one-second pacing and broader simulated hit locations;
a separate 60-step original-path boundary fixture is prepared with fixed bounds,
per-hit selection expectations and tagged-only drive input. Non-drive hits are
classified but never dispatched to unwrapped components.

## One-second boundary test: observed pass

The final [original-path source](ui-selection-diagnostic/NativeDriveBoundaries.java)
and [result](ui-selection-diagnostic/boundaries-original.stdout) complete all 60
steps at one-second pacing: all 14 centers; right boundaries at drives 1, 5, 6, 7
and 13 with -1/0/+1 offsets; drive 6–8 corners; above/below drive 6; divider gap;
and four press/enter/captured-release/post-release-hover drag sequences. Hits,
expected indices/membership masks, stable bounds, drag flags and unchanged
synthetic state pass. There are 1,400 created images, 742 Java paints, no stale
generations at ticks, and zero guarded prohibited operations. Largest recorded
first-paint delay: 46,887,125 ns. Native ARM only; paint scale 1.0.

The operator watched this run and reported “It looked fine.” This is a passing
visual observation for this paced synthetic fixture. It supersedes any assertion
that the one-second boundary test remains pending, but does not establish a fix
for the earlier intermittent full-application symptom. It changes no application
renderer. Events go directly to tagged drive-label listeners after local hit
testing; native OS pointer dispatch and the full information-view hierarchy are
not exercised. Non-drive hits are inert, rather than sent to unwrapped listeners.

[Receipt](ui-selection-diagnostic/boundary-receipt.json) binds the pilot source,
compiled classes and outputs. Claude's source review raised a conditional concern
about sharing mode-4 image oracles with mode 3: original renderer bytecode had
already established the same tint for assigned selected drives in both modes;
all actual mode-3 oracle checks passed here. The original mouse listener implements
drag selection on entry. Stale paint counts are observations, not framebuffer
proof. No completed hardware operation or comprehensive application acceptance
is inferred from this run.

The released audit30 product and architecture packages remain unchanged. This
follow-up synchronizes evidence and release notes only; it creates no fictitious new
renderer fix or revised binary provenance.

Claude's [publication review](ui-selection-diagnostic/claude-boundary-publication.json)
corrected “60 selections” to “60 steps”: inert gaps, releases and post-release
hover steps need not change selection. The README/release wording uses steps.
Timing describes the configured one-second pacing with a 950-ms lower-bound
assertion, not a captured minimum interval measurement.

## Release synchronization

The audit30 release notes were updated with the operator-observed paced fixture
result. [Publication verification](UI-SELECTION-PUBLICATION.json) confirms the
prepared notes are published on Latest audit30; all ten asset identities, sizes,
digests and timestamps are unchanged; and both the annotated tag and its peeled
target are unchanged. The documentation/evidence commit was pushed to main and
audit/phase-0. No new binary version was generated for these diagnostic changes.

Read-only archive verification, without Java or network:

```sh
/opt/homebrew/bin/python3 -I -S audit/ui-selection-diagnostic/verify.py
```
