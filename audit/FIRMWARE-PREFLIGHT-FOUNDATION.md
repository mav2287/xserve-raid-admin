# Offline strict known-package firmware foundation

This standalone tool is not application preflight, a transmission approval or
firmware-operation qualification. No application bytes or updater code change.

## Enforced policy

`tools/firmware_preflight.py` reads a bounded immutable snapshot of a local
regular file. It rejects non-bytes snapshots, oversize input, unknown content,
symlinks, FIFOs and ordinary read failures with fixed codes. It accepts only the
929851-byte package matching SHA-256
`32c077ea0ec50a944a996b72978f6d7b9585d17603da847fd4317ebc364dd9a7`,
previously acquired from Apple's distribution archive. Unknown ZIPs are never
parsed or decompressed. There is no runtime ZIP parser, network API, Java call or
updater invocation.

Once bytes match, the tool returns reviewed reference metadata: coprocessor
update 1.5.1 and RAID-controller update 1.51c, dated 12/08/2006, with fixed paths,
image sizes and digests. The optional full image is absent in this known package.
Provenance describes the acquired reference bytes, not the selected input's
history. No arbitrary filenames, unknown digests, manifest text or OS exception
messages are printed. CLI argument failures also emit fixed JSON.

This is a deliberately strict allowlist. ZIP integrity, safe paths, manifest
keys and image sizes are inherited from byte identity with the checked reference,
not established by a general unknown-archive validator. Additional package
support requires a reviewed source change and new acquisition/Java evidence.
No controller signature scheme or hardware compatibility is asserted.

## File-read boundary

lstat rejects nonregular paths before open. O_NOFOLLOW, O_NONBLOCK and O_CLOEXEC
are applied; fstat verifies regular type, dev/inode identity and size again.
Reads accumulate short chunks, never request more than 65536 bytes and stop at
the largest known size plus one byte. Growth past the cap rejects; byte count
must equal opened size. The returned bytes cannot change when the file changes.

O_NOFOLLOW covers the final component only. This is not path containment or a
hostile-filesystem sandbox. The lstat/open race cannot guarantee that opening a
replaced device has no side effects; test inputs here are disposable local files
and the pinned public cache. No production volume or credential store is read.

## Source refinements from actual Claude consultation

The [initial design review](claude-review/FIRMWARE-PREFLIGHT-FOUNDATION-DESIGN.txt)
identified a material legacy detail: manifest references select displayed
metadata, while updateRaidController/updateCoprocessor open fixed updateROM.bin
paths. References must describe those actual images. Required Name sections and
version/date metadata also prevent original null dereferences. The full-image
key is read but not transmitted by the inspected outer updater class; inner
class behavior was outside that review and remains unqualified.

The [follow-up design review](claude-review/FIRMWARE-PREFLIGHT-KNOWN-HASH-DESIGN.txt)
endorsed rejecting unknown content before interpretation and returning frozen
metadata without a runtime parser. This removes the Python/Java unknown-ZIP
interpretation surface identified in the first review. CRC/flag values are not
added to the table because the existing reviewed fixture did not independently
record them. Package identity fixes those bytes without needing guessed fields.

The [implementation review](claude-review/FIRMWARE-PREFLIGHT-FOUNDATION-IMPLEMENTATION.txt)
found no blocker. Its two medium evidence gaps are addressed: the checker compares
all frozen provenance and member metadata with committed acquisition records,
and the static test disallows unexpected OS attributes, import aliases/from-imports
and dynamic/builtin access. Additional tests cover short reads, growth, inode
mismatch, read counts, device precheck and fixed CLI errors. ZIP/inflate/socket
mocks prove zero such runtime calls for reviewed test paths, not a general sandbox.

## Evidence and remaining application work

The opt-in checker parses only the snapshot already accepted by the gate. It
compares member order/sizes/methods/digests, complete success metadata and known
manifest paths/sections with the reference. Five arbitrary byte-position mutations
and prepend/append/truncate variants reject before interpretation. These probes
test the hash boundary, not generic ZIP handling. Without the public package,
the checker explicitly records that package tests were not run.

The legacy FirmwareBundleConnection wrapper remains byte-identical. Existing
original/candidate Java archive probes separately verify the two known image
hashes on both pinned runtimes, without constructing updater requests.

Run the validator with a local package path. Run
`tools/check_firmware_preflight.py --official-firmware <pinned public cache2 XFB>`
to verify the exact acquisition marker and known metadata, or omit the option to
verify committed table evidence only. The marker pin belongs to the second
acquisition; the first has different marker bytes but the same container/package.

**Unresolved:** Java updater integration, safe jar URL construction, chooser and
summary/confirmation UI, version/hardware/downgrade rules, progress, acknowledgement,
restart/reconnect and final-version verification. Snapshot validation here says
nothing about bytes later reopened or transmitted. Future integration must bind
validation to those bytes, including JarURLConnection cache behavior and original
closed-stream retry semantics. It must retain immediate explicit confirmation
before firmware transmission and associated cache/controller operations. No
restricted action is authorized or performed by this foundation.
