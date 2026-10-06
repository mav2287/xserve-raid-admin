# audit.10 malformed and negative response lengths

**Fact:** original getBody parses Content-Length and allocates its buffer before
its protected read region. Invalid numeric, overflow and negative lengths therefore
skip outstanding-state cleanup. audit.9 fixed recovery for new ceilings only;
its ordinary invalid-length path still denies the next command. The user explicitly
prioritized safe security closure, so audit.10 deliberately refines this unsafe
failure behavior instead of preserving the liveness defect.

## Narrow change

The hash-locked transformer appends one parseLength Methodref and changes the two
operands of the existing invokestatic at getBody offset 14. The opcode, all
instructions/branches, frames, exception table and subattributes stay unchanged.
The prior allocation operands and constructor wrapper remain. There are exactly
three permitted getBody operand edits; independent complete javap checks verify
the parse target as well as allocation targets. Original Integer.parseInt owner,
name, descriptor and exact instruction window are pinned before transformation.

BoundedResponseBuffer.parseLength delegates to the same runtime Integer.parseInt.
It catches only NumberFormatException and replaces it with a fixed marker without
untrusted input or cause. The existing allocation gate also rejects negative
integers with this marker. Valid formats, including runtime-supported signs and
leading zeros, retain original parsing; -0 becomes zero. Negative contentLength
assignment still precedes rejection, while invalid strings still fail before
assignment. Values above 16 MiB retain the existing too-large marker.

The reviewed exact-marker send/queue retirement from audit.9 applies unchanged:
one terminal -102 callback, no replay of the failed command, safe close despite
cleanup errors and original reconnect handling for the next distinct command.
The missing exact header still follows the original null branch and empty-body
behavior. Lowercase, duplicate, chunked and HTTP-status interpretation remain
G12 work; this does not claim standards-compliant HTTP framing.

## Validation and scope

Candidate-only memory fixtures cover malformed text, int overflow, -1 and int
minimum as well as all four prior ceilings, on both architectures. They check
persistent/nonpersistent transport, cleanup IO/runtime failures and distinct
queued status/time requests retaining their contexts. Pure gates compare supported
valid strings directly with Integer.parseInt on the executing JVM, reject invalid
strings with the exact fixed class/message, and verify absent cause and absent
synthetic input in the escaped stack trace.

The original malformed-length stale-state observation remains in original results.
Candidate intentional differences are explicitly enumerated and validated; all
remaining direct/queue/retry/ACP/XML observations must match. A comparison unit
test rejects missing or invented security-difference labels and exposes ordinary
differences. Exception-type equality for the changed security cases is not claimed.

Full original catch-table scanning and scoped bytecode inspection find no typed
NumberFormatException catch in AcpxConnection, CommunicationsManager, CLI
DefaultHandler or handler 15. These CLI callers also get the new fixed exception
and close-and-rethrow behavior; their full lifecycle/UI remains unqualified.
Normal IOException handling and legacy ambiguous mutation replay (G10) are
unchanged. An idle manager still reconnects only on a later queued command.
No polling interval or controller command serialization is altered.

These are bounded offline fixtures, not hardware, real TCP timing or production
volume tests. x64 uses Rosetta; physical Intel and full operational acceptance
remain open. HTTP remains plaintext. Original JAR and installed app stay unchanged.
Actual Claude design review preceded implementation. Its implementation review
found no patch defect and prompted reproducible catch-inventory provenance,
additional helper static checks, parse operand mutation coverage and explicit
transport policy requirements. New direct-send tests check the escaped trace,
absent cause and closed connection; flags/body-codec/logger-failure variations
remain measured on the earlier ceiling sites, rather than claimed for every new
length case. Final clean evidence is pending.


## Clean evidence

Application source `cdcc98c`, packager `b1c4040`; repeated clean builds match bytes,
modes and inputs. JAR SHA-256: `1526b6a5e6cb4be8515c74b8cf36271b405d19c7d9a4266378c5811785b9bdc1`.
Audit bundle digest: `44225bd52f2ea9b86e92cf716cf424b8b8dc6a28c50a4a16a698fdfadce8b640`.
Repeated runtime package digests:

- arm64: `f2def8812ee6a989af8d21ead3dbbd5d7f5860776276ab2290616d268f79fc59`.
- x64: `2b24b89e28e66855881aa255822834e760e22f4c434eb7307ecbd3c58bf1fe09`.

[Independent preservation/helper checks](length-clean-security.json),
[required length-policy transport](length-clean-transport.json),
[runtime/recovery fixtures](length-clean-runtime.json),
[XML regressions](length-clean-resources.json),
[reproducible catch inventory](length-clean-catch-inventory.json),
[source provenance](length-clean-provenance.json),
[package repetition/diagnostics](length-bundle-results.json) and
[installed/original integrity](length-final-integrity.json) record their scopes.
45 Python tests pass. Final fixture/verifier source `dea3f0d` records 78 recovery
output lines on each runtime. Catch inventory regeneration is byte-identical and
its tool/source hashes were checked against the tracked files. Reproduce it with
`python3 tools/inventory_exceptions.py` at this source version.

Actual Claude [follow-up](claude-review/INVALID-LENGTH-FOLLOWUP.txt) found no blocker.
Only explicitly scoped low-severity fixture/verifier nits remain. These results
close demonstrated malformed/negative-length stale-state behavior in bounded
fixtures, not full release acceptance or every controller/security gap. G10/G12,
CLI lifecycle, real TCP, physical Intel and native UI remain open.
