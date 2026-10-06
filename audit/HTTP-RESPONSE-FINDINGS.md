# Offline HTTP response and queue characterization

This milestone changes fixture code only. Application source remains `13ac370`
(audit.5), JAR SHA-256
`b6fdfab523768556f2c3c76190704c2319a9038efb43ebac05d66a3afebe70df`.
The immutable original SHA-256 remains
`5505d8d9a08aafb338150cd0ca54a163048961172df15ee3a0749c4192f59449`.

## Facts

`HttpResponse.parseHeaders` reads but does not validate or interpret the HTTP
start line. `HttpMessage` uses a case-sensitive header map. `getBody` parses
the exact `Content-Length` field, allocates its buffer from that integer, reads
bytewise and throws on premature EOF. `BasicResponse` derives its result from
the plist's `status` value, defaulting to zero when absent. These are independent
`javap -p -c` observations of the verified original classes.

The guarded fixture verifies 21 direct-response cases, nine queued-response
cases and a two-request queue sequence. Original and candidate outputs agree
on both pinned Java 8 runtimes. Candidate configured logging also agrees and
emits exactly one fixed error code during the complete process; application
`System.out` capture is empty. The logging check applies to the complete run,
not once per error case. See [machine-readable observations](http-response-observation.json).

| Synthetic input | Observed behavior |
|---|---|
| HTTP 401, 403 or 500 with the fixture success plist | Result zero, including through the queue |
| Arbitrary nonempty start line with success plist | Result zero |
| ACP plist status -16, -27 or -28 | Corresponding result preserved, including queued callbacks |
| Missing or lowercase length; chunked without length | Empty parsed response; lowercase length produces queued result zero |
| Duplicate exact length fields | Last value wins |
| Non-integer or integer-overflow length | Number-format exception; queued non-integer length produces -102 |
| Negative length | Illegal-argument exception before body read |
| Truncated body | I/O exception; queued case retries once against the following valid reply |
| Invalid header lacking a colon | Protocol exception |
| Synthetic open-idle truncated stream | Immediate synthetic socket-timeout exception |
| Two distinct read requests with first response dropped | Sends first–first–second on connection ordinals 1–2–2; one callback per request, in order, with original context |

The queue test derives its assertion from original bytecode (`addFirst` of the
same transaction on non-parse I/O failure) and the first reference fixture run.
Requests use status and time getters, never a live controller. Existing synthetic
write/firmware retry probes remain memory-only and are not hardware operations.

## Inferences and unresolved questions

Ignoring HTTP status and treating missing body framing as empty success can hide
failures. This is a demonstrated transport result, not proof of authentication
bypass: actual controller replies and downstream authentication/UI handling have
not been qualified. A truncated reply can repeat a command already accepted by
the controller; this refines the existing ambiguous-retry risk.

No parser/protocol fix is made in this milestone. Rejecting previously accepted
messages, changing result mapping or altering retries would change operational
semantics and requires a reviewed preservation decision backed by representative
controller responses. The next safe investigation is bounded plist resource
handling and the original authentication callback path.

Each reply uses a fresh stream. Residual bytes on reused sockets, undersized
lengths causing desynchronization, actual keep-alive EOF/timeouts, concurrent
queue posting, cancellation, backoff and long-duration polling remain open.
Synthetic idle timeout is immediate, so it proves exception routing, not timing.
Unsafe bypasses transport/model constructors; only reached initialized paths are
covered. Positive large-length allocation and resource exhaustion are excluded;
the original allocates directly from a positive parsed integer without a size
ceiling, so an excessive length can cause an uncaught VM allocation error.
Negative/overflow lengths and synthetic idle replies are direct-send cases only.

Replies are under 4 KiB; scripted reads are bounded below 8,192 and sends below
16 per state. The outer process timeout is 20 seconds. The real dispatch loop
catches Exception, not AssertionError. The guard denies sockets, writes,
preferences, subprocesses, process exit and new descriptor writes and reports
zero attempts. Python additionally requires the final completion marker.
No full app, native UI, hardware or installed app was modified or exercised.
The x64 JVM runs on this arm64 host under inferred Rosetta translation.

## Reproduction

Run from the repository with the locked compiler and existing candidate bundles:

```sh
python3 -E -s tools/check_transport.py \
  --jdk /Users/mav2287/Library/Java/JavaVirtualMachines/corretto-1.8.0_362/Contents/Home \
  --default-logging \
  --runtime 'build/logging-bundled-arm64-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk' \
  --runtime 'build/logging-bundled-x64-1/RAID Admin.app/Contents/PlugIns/Runtime.jdk' \
  'build/logging-clean-1/RAID Admin.app/Contents/Resources/RAID_Admin.jar'
```

Runtime bytes, permissions and vendor signatures are verified against the lock
before and after observation. Output records fixture commit/dirty state, source
hashes, imported harness helper hashes, JAR hashes, compiler identity, runtime
identities and host architecture.
Raw JVM failure output is withheld. Actual Claude CLI design and implementation
consultations are recorded in `audit/claude-review/`.

The 38-test Python suite includes early-successful-exit/incomplete-transcript and
symlink rejection regressions. Since the shared guard was hardened, existing
menu, folder, resolver and logging fixtures were rerun on both pinned runtimes;
see [guard regression observations](hardened-guard-runtime-fixtures.json).
