# Legacy LaunchServices metadata — bundled launcher compatibility

Claude's no-hardware triage identified a preservation gap: original Main selects
CLI mode for any nonempty arguments other than its special version/LAF cases.
The bundled shell launcher forwarded all arguments unchanged. A canonical legacy
LaunchServices process serial number could therefore select CLI mode and exit.
Whether current macOS actually supplies that metadata is unobserved; this is a
narrow compatibility safeguard, not a claim of reproducing a modern Finder bug.

Only a leading argument matching `-psn_[decimal]_[decimal]` is removed. All other
arguments, including malformed matches and later canonical arguments, retain
their exact order, spaces, empty strings, Unicode and newlines. No Java, controller,
profile, polling or retry code changes. The audit-only historical launcher is
preserved; the pinned-runtime package launcher receives the fix.

Shell-level tests execute the actual copied launcher against a synthetic Java
executable. They cover metadata-only GUI selection, metadata plus other arguments,
unchanged CLI/invalid tokens and existing ambient-environment injection rejection.
No application Main, real Java GUI, network, preferences or installed app is used.
A first test attempt failed because its expected path did not resolve macOS's
/var alias; correcting the fixture path required no product change.

Native Finder event delivery remains unqualified. Real RAID hardware acceptance
is deferred under the user's latest instruction; no such test is queued.
