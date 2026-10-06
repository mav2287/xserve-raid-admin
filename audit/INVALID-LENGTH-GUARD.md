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
Actual Claude design review preceded implementation; implementation review and
clean evidence are pending.
