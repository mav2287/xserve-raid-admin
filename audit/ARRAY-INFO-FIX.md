# Array information selection fix — audit29

The user authorized a narrow fix to investigate intermittent scattered drive
highlights while switching Array & Drives selections. Claude reviewed the
design, patch, fixture and compilation checks; raw reviews are in
[array-info-fix](array-info-fix). This is an offline-tested trial, not confirmation
that the reported native display symptom is resolved.

## Verified cause and precise change

**Fact:** a cleared original `ArrayLabel` reports array ID `0`, including the
hidden-radio path. The information listener passes this straight to
`DriveSelectionPanel.setArrayIndex`. That panel uses `INDEX_NONE` (`-10`) for
no selection; `0` instead highlights drives with zero/unassigned array membership.
Fresh raster tests reproduce that incorrect cleared-selection state.

**Inference:** this mismatch can contribute to the user's scattered highlights.
The exact clicked control and native repaint behavior have not been established;
accelerated rendering, stale events or another path may still be involved.

Only `SystemInfoPane$5.propertyChange`'s call at bytecode offset 30 changes from
`invokevirtual DriveSelectionPanel.setArrayIndex(I)` to
`invokestatic compat.ArrayInfoSelection.setArrayIndex(DriveSelectionPanel,I)`.
The small helper translates only `0` to `INDEX_NONE`; every other value is passed
through and the setter is invoked once. Null-panel failure remains a
`NullPointerException`. Instruction width and stack shape are unchanged.

The information view's private panel getter intentionally now reports `-10`
after a cleared array row. Whole-JAR references show no controller or wizard
consumer of this private panel. Raw detail selection (`id - 1`), original radio
handling, CardLayout choice, refresh call and event timing are retained. No model,
network, request, polling, retry, array creation/deletion or shared renderer class
changes. All other JAR entries, including resources and the manifest, are exactly
audit28 bytes. No new persistence, logging, threads or catches are introduced.

The final Claude review found no release blockers. Its minor documentation notes
were addressed by archiving the exact two-key plist diff and clarifying combined
run counts; historical review records retain their original wording.

## Artifact and test evidence

Product and packaging source is clean commit
`26d7ec7921d9839d1dfcb9f0158e3af1a2824c6c`. Documentation commits and the release
tag add evidence without attributing a new build to them.

- Original Apple JAR, unchanged: `5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449`.
- Fresh rebuilt audit28 base: `bf5f630be51d992be918f2dd3cef8beed3f3873aae60efc2defdfd20cee5fb9e`.
- Audit29 common JAR: `d616359dbea9fa8c9bd61f107b86e65b3563353f833a35430b314036d1a03fc6`.

Two independent common builds have identical files, modes and input maps. Each
architecture package passes repeated ZIP equality, extraction files/modes, pinned
vendor-runtime signatures, SPDX schema validation and physical/virtual entry
checksum checks, including bad-checksum negatives. Full package comparison with
audit28 changes only the JAR and the two version fields in Info.plist; launcher,
JNI helper, bundled runtime, icons, file set and permissions are unchanged.

The actual listener and actual no-system refresh pass eight original/candidate
runs across native ARM and x64 Rosetta, interpreted and focused compiled modes.
Four original-code negative controls fail the fixed-selection oracle as expected.
The fixture checks valid array IDs 1–6, JBOD sentinels, none, mixed drive membership,
14 drive-image pixels, repeated transitions, raw detail selection, radio/CardLayout
state, setter count, null behavior and unchanged model state. Synthetic detail
label subclasses avoid constructors that would read legacy preferences; real
Swing controls are used headlessly. This does not test native window painting.

XML JIT logs prove installation of the listener and helper code in focused compiled
runs. They do not prove every assertion or the whole application ran compiled;
deoptimization and inlining remain possible. An earlier broad `-Xcomp` diagnostic
with CodeCache warnings was rejected and retained separately; it is not a passed
qualification run. Product JVM options are unchanged. The earlier fixture-review resolution referring
to PrintCompilation is historical; the later JIT review and final records use XML
LogCompilation instead.

The unit suite passes 192 tests with six existing skips. Ten additional interpreted
packaged CodeSource/native preference fixtures and ten dummy launcher argv-stub
runs pass in total across both architectures (five of each per architecture). Those use unchanged, hash-verified historical probes with actual new
package paths and synthetic disposable files. The x64 run initially refused an
incorrect common-build provenance argument before executing fixtures; rerunning
with its recorded common-8 build passed. The archived adapter is explicitly a new
trial test driver, not a modification or relabeling of frozen audit28 gates.

[Receipt and hashes](array-info-fix/receipt.json) bind the provenance, results,
bytecode, identity tables, compressed raw JIT logs and package checksums. Read-only
verification (local ZIP checks run when those recorded build files are present):

```sh
/opt/homebrew/bin/python3 -I -S audit/array-info-fix/verify.py
```

The frozen audit28 verifier completed its record, Git, ZIP, audit27 and original
checks, then refused its final installed-reference check: the current installed
JAR matches audit28 (`bf5f…fb9e`), rather than the historical intake JAR. This
is not an overall verifier pass. The old verifier and expected intake hash are
preserved; the audit29 record explains the difference without changing the app.

## Reproduce safely

Use a clean checkout of the product commit above, the compiler/Python/runtime and
SPDX validator locked in `audit/`, and fresh output directories under `build/`.
The example runtime directories refer to previously verified local vendor trees;
see the runtime lock for vendor URLs and checksums. Repeat the common build with a
second output and compare actual files/modes, then package both architectures.

```sh
/opt/homebrew/bin/python3 -E -s tools/array_info_build.py --jdk /path/to/locked-corretto-8.362/Contents/Home --output build/new-array-common
/opt/homebrew/bin/python3 -I -S tools/array_info_release.py --build build/new-array-common --architecture aarch64 --runtime 'build/secure-release-aarch64-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk' --validator build/spdx-validator --created 2026-10-08T00:00:00Z --output build/new-array-arm
/opt/homebrew/bin/python3 -I -S tools/array_info_release.py --build build/new-array-common --architecture x64 --runtime 'build/secure-release-x64-6/RAID Admin.app/Contents/PlugIns/Runtime.jdk' --validator build/spdx-validator --created 2026-10-08T00:00:00Z --output build/new-array-intel
/opt/homebrew/bin/python3 -E -s tools/check_array_info_fix.py --jdk /path/to/locked-corretto-8.362/Contents/Home --build build/new-array-common --output build/new-array-fixtures
```

The compiled fixture uses the recorded `build/secure-release-{aarch64,x64}-6`
runtime paths, independently verified against the runtime lock. The archived
`packaged-preference-driver.py` was executed from `build/`; copy it to a fresh
build filename before reproducing its checks with `--package`, `--fixtures`,
`--build`, `--reference` and fresh `--output` arguments. Its historical compiled
probes must match the pinned fixture manifest; see the driver and recorded package
observations for exact paths and scope.

## Release and remaining check

[v1.5.1-modern.audit.29](https://github.com/mav2287/xserve-raid-admin/releases/tag/v1.5.1-modern.audit.29)
provides unsigned Apple silicon and Intel packages with Java included. Audit28
artifacts, tags and frozen audit records remain unchanged. `/Applications/RAID
Admin.app` was neither replaced nor launched during this work. No profiles,
credentials, controller operations or production volumes were accessed.

**Unresolved:** the user should try the new bundle and repeat normal left/right
Array & Drives selection. Confirmation that intermittent stale highlights are
gone remains open. Full GUI, physical Intel, actual controller workflows,
Developer ID/notarization, other filesystems/OS versions and future macOS remain
unqualified. Legacy HTTP remains plaintext.


## Later operator evidence — 2026-10-08

The user reports the patch improves the symptom. Selection and details remain correct; rapid transitions still produce a short, self-resolving highlight delay. [The follow-up investigation](ARRAY-REFRESH.md) preserves this distinction. No additional product changes or hardware acceptance follow from the new report.
