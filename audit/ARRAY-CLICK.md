# Information-view selection responsiveness — audit30

## Diagnosis and scope

**Fact:** ArraySelectionPanel$4.mouseReleased invokes AbstractButton.doClick(),
which calls doClick(68) in the bundled Java 8 runtime. Its simulated press sleeps
on the calling thread before releasing the button and firing the action. Array-row
text clicks run this on the event thread. SystemInfoPane$4 also uses that default
for internal selection-mode radio changes. These are concrete, avoidable delays.

**Inference:** queued 68 ms waits fit the operator's briefly stale, self-resolving
highlights during rapid clicks. This does not prove all native presentation delay
has the same cause. Audit29's zero/no-selection correction remains intact.

The new helper uses doClick(0) only for array-row buttons descended from the
original SystemInfoPane and its private selection-mode listener. Outside that
information view, shared row code still calls original doClick(). All original
armed/pressed/released, item/action and selection processing remains synchronous;
the simulated pressed flash is shortened. Manual radio-button mouse behavior,
controller commands, polling, retries and all wizard code retain their semantics.

The exact three invocation substitutions affect two original listener classes.
One Java 8 helper is added. Instruction widths and stack effects are unchanged;
full-class inverses and every other JAR entry are checked. No subclass, constructor
change, repaint forcing, global rendering flag or redundant-render shortcut is
included. Original Apple reference bytes and audit28/audit29 releases remain fixed.

## Validation and limits

The source includes a guarded before/after fixture with 300 mixed transitions per
run, real row and mode listeners, actual offline-drive selection, both cards,
selected details, 14 icon samples and unchanged synthetic model arrays. It compares
ordered button state/action traces and checks exact doClick(int) arguments:
0 within the information view, 68 outside it, and preserved null failures.

An initial interpreted ARM/Rosetta comparison passed event parity and retained
outside/default delay. Accepted clean-source build and release observations are recorded below. Pilot records are not release qualification. SystemInfoPane
ancestry is synthetic to avoid constructors that initialize profiles. Original
constructor bytecode establishes the real containment path, but a full native
interface session is not claimed. No Main, real profiles, credentials, controller,
production volumes or installed app was used by these fixtures.

Claude independently identified the same delay and reviewed the scoped approach.
The initial review refers to an abandoned subclass prototype; that constructor
change was removed. Final source review and follow-up are recorded in `array-click/`.

## Reproduce

Use the locked compiler, Python, runtime trees and SPDX validator; new output
folders and clean Git source are required.

```sh
/opt/homebrew/bin/python3 -E -s tools/array_responsiveness_build.py --jdk /path/to/locked-corretto-8.362/Contents/Home --output build/new-click-common
/opt/homebrew/bin/python3 -E -s tools/check_array_clicks.py --jdk /path/to/locked-corretto-8.362/Contents/Home --build build/new-click-common --output build/new-click-check
/opt/homebrew/bin/python3 -I -S tools/array_responsiveness_release.py --build build/new-click-common --architecture aarch64 --runtime 'build/secure-release-aarch64-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk' --validator build/spdx-validator --created 2026-10-08T00:00:00Z --output build/new-click-arm
```

Repeat for x64. These tools never launch or install the application.

## Accepted clean-source results

Product, fixture and package source: `1a2ef1f35ad26dc28821ab19ba3677a2280312b9`.
Two independent common builds (`build/array-click-common-3` and `-4`) match all
files, modes and input hashes. Common JAR SHA-256:
`3875edc404c7773d602fdb834bf8090dcb73b53a30d6306bc2fb09951a542059`.

[Four clean interpreted runs](array-click/listener-results.json) pass 300 mixed
rounds each on native ARM and x64 under Rosetta. Separate 12-sample row-click measurements inside and outside the information
view and 12 mode-switch measurements run in each process. Actual patched row and
mode listeners assert delay argument 0 using probe buttons; exact audit29 asserts
68; outside rows assert 68 in both. Ordered button state/action traces match; no item transitions occurred in these traces. Direct helper argument
and null tests, real mode handlers, offline-drive selection, detail/card/icon and
unchanged-model checks pass. Guards report no prohibited operation. Medians for
row clicks were 87.96 → 3.96 ms on ARM and 83.63 → 2.21 ms on Rosetta x64;
mode switches 80.29 → 4.12 and 80.82 → 2.54 ms. These are headless interpreted
observations, not native screen presentation measurements or general benchmarks.
The timed event traces exercise already-selected row buttons; they contain no
item transitions, so item-event parity is not newly qualified. The 300-round
loop checks mixed selection state through original private selection and mode
handlers/direct array property events, separately from the patched row-handler
measurements and delay-argument assertions. `fixed=true` in original/fixed stdout
refers to the retained audit29 sentinel correction, not this click-delay change.
The deterministic argument checks establish the fix without a fragile upper
latency threshold. Full Python suite: 196 tests, six existing skips.

Both unsigned architecture packages pass repeat ZIP, extraction/files/modes,
vendor-runtime signature and SPDX physical/virtual-byte checks. Relative to the
frozen audit29 packages, only JAR and the two Info.plist version fields differ;
all other files, modes and directories are equal. Packaged JARs and runtime trees
are identical to the identities used by the corresponding fixture checks.

[Receipt and archive hashes](array-click/receipt.json) bind common/package
provenance, source inputs, fixture outputs and Claude reviews. Imported build and
runtime verification modules are additionally bound by common-product input
closure and the clean fixture commit. Read-only verification, without Java:

```sh
/opt/homebrew/bin/python3 -I -S audit/array-click/verify.py
```

Claude's final review exposed a runtime-proof gap; deterministic checks through
the actual patched listeners were added. Its [follow-up](array-click/claude-followup.json)
confirms the reported issues resolved. The stale argparse observation in the
preceding review refers to an earlier snapshot; that variable bug was fixed before
`65ce931`. Pilot timing/setup runs are excluded from this accepted clean record.
The information-pane constructor and native presentation remain unqualified;
the operator should confirm normal rapid selections with this bundle. No
additional controller operation is accepted.
