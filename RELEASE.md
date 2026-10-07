

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
