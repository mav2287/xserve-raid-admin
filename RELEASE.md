# Local audit27 artifact handoff

Current locally qualified candidate uses product/build/package/release source
`4735f41` and evidence assembly `c7ea088`. Seventeen gates and 175 unit tests pass.
The app remains unsigned and unnotarized; native full GUI, physical Intel, signing,
redistribution and controller acceptance remain unverified or deferred. Hardware
checks wait until actual operational need, as directed. No installed app change
or remote publication occurred. HTTP is plaintext.

| Architecture | Local ZIP | SPDX inventory |
|---|---|---|
| Apple silicon | [ARM ZIP](build/releases/audit27/RAID-Admin-aarch64.zip) | [ARM SPDX](build/releases/audit27/RAID-Admin-aarch64.spdx.json) |
| Intel | [x64 ZIP](build/releases/audit27/RAID-Admin-x64.zip) | [x64 SPDX](build/releases/audit27/RAID-Admin-x64.spdx.json) |

Repeated artifacts match, and extracted vendor runtime signatures verify. The
qualified save-stream fix preserves original file format, paths, permissions,
links and interrupts. Private creation and other documented security gaps remain.
See [scope and exact hashes](audit/PREFERENCE-IO.md),
[frozen ledger](audit/preference-final-integrity.json), and
[archived evidence](audit/preference-archival-map.json). These local artifacts are
for review; successful launch alone would not qualify controller functionality.

---



## Audit26 local unsigned artifacts

Product/build/package/archive/SPDX source is clean `46dec9e`; assembler source
is `809bdb2`. Sixteen gates and 170 units pass. Matching repeated packages, ZIPs
and SPDX documents exist for aarch64 and x64 under `build/releases/audit26`.
ZIPs preserve exact modes and vendor runtime signatures after extraction.
The application is unsigned and unnotarized, with full native GUI, physical
Intel, controller and redistribution acceptance unverified or deferred. No
installed app is modified and no remote release is published. Reproduction
and exact artifact digests are in [scope](audit/MODEL-DIAGNOSTIC.md);
[ledger](audit/model-final-integrity.json) and [archival map](audit/model-archival-map.json)
bind the records. Do not overwrite the frozen artifacts.
