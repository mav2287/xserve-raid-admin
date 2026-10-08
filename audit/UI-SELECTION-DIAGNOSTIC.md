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
It did not reproduce the operator's delay, so it does not close acceptance.

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
