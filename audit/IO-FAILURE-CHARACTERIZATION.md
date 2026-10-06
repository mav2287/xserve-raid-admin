# G10-a bounded IO failure characterization

This step changes no application bytes. The immutable original and audit.11
candidate are exercised through actual AcpxConnection.send and CommunicationsManager.run
with injected memory connections, synthetic requests and logging disabled.
No firmware transmission, controller connection, saved profile or production
volume is accessed. The restart request is serialized into memory only.

## Observed facts

- A colonless response header produces a ProtocolException whose message contains
  the synthetic peer line. The fixture emits only a boolean, never that message.
- Both a status read and a synthetic set-time request are sent twice with identical
  bytes after this malformed response; the scripted second response succeeds.
  Each receives one terminal callback with the original context.
- A synthetic restart request with one dropped response is also replayed with
  identical bytes. Its shutdown flag is true; memory disconnect is a no-op, so
  this is not qualification of that flag's socket effects.
- An injected message-less IOException escapes run as a NullPointerException.
  The fixture worker dies after one send with no callback, stopped=false,
  connected=true, and the removed transaction is lost. A later asynchronous post
  remains queued. The fixture contains the uncaught exception without printing it.
- A header property changed on the original request after posting appears in the
  queued clone's wire bytes. This proves shared header-map mutation only.

Original and candidate produce the same eight fixed output lines on both pinned
Java 8 runtimes. x64 executes under Rosetta, not physical Intel. Python checks
require the exact vector and suppress unrecognized output on failure.

## Evidence and limits

The full pinned Manager/factory/request bytecode corroborates the IO handler's
getMessage().startsWith call and requeue branch. Handler code lies outside the
protected send region; a null receiver therefore escapes the worker. The shallow
clone is Object.clone. A possible connection leak on ordinary retries remains
an inference, not a measured resource finding.

The Manager constructor is bypassed. The worker calls run on a fixture thread
with a custom uncaught handler, rather than the original CommMgr thread group.
The null exception is injected, not proven to arise from a real socket. One retry
is observed because the next scripted response succeeds; persistent bad-peer
retry behavior is not bounded by this measurement. Real doConnect, TCP timing,
backoff and polling are excluded. Synchronous callers after worker death are
unmeasured. Parameter mutability and concurrent request modification are not
tested. Two pinned CLI direct-send callers exist; their inventory is incomplete.

Bounds include 16 sends, eight injected retries, capped response bytes, 64 MiB
heap, 20-second process timeout, and two-second worker joins with cleanup.
Captured stdout/stderr must be empty and the offline guard records zero actions.

## Actual Claude consultation and next boundary

[Design consultation](claude-review/AMBIGUOUS-IO-RECOVERY-DESIGN.txt) recommends
characterization first, a fixed terminal malformed-header marker second, and
an IO replay classifier only after a complete factory/RPC/caller/sequence audit.
[Implementation review](claude-review/AMBIGUOUS-IO-CHARACTERIZATION-IMPLEMENTATION.txt)
found no fixture blocker. Its fixes are incorporated: the direct peer-line
boolean, precise shutdown_flag wording, logger threshold, and the limits above.
Historical line references and its seven-line vector are superseded by the
eight-line fixture. Clean evidence is generated after this fixture commit.

The proposed first application change removes only the malformed-header peer-text
exception and makes it an exact security rejection through the existing retirement
path. Null-message handling and broader ambiguous mutation replay remain separate
open work. No whole-program no-replay or complete security claim is made.
