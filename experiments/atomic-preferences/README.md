# Atomic preference experiment — not shipping

This directory is excluded from the application build and both release packages.
The application remains audit27. Only synthetic disposable APFS files are used;
no real saved profile, secret, controller, production RAID or installed app is
opened. These tests do not qualify complete application operation.

## Facts from source

Java attaches the original noninterruptible FileOutputStream to an empty
FileDescriptor before native opening. It retains the original XML serializer,
UTF-8 writer, explicit flush and interrupt flag. Native creates a random,
exclusive temporary inode at mode 0600 in an anchored checked parent. Java owns
one descriptor; native owns a duplicate for identity checks. Successful raw
close precedes native commit. Commit checks the temporary inode/name, parent,
and original target identity, then renames. An absent target uses RENAME_EXCL.
Abort only unlinks the recorded temporary inode; it never writes the old target.

The parent must be owned by the effective uid or root, lack group/other write,
retain ownership semantics, and carry no allow or file-inheritable ACL entries. Filesystems whose ACL API is unsupported are refused conservatively; real remote availability remains unknown.
Non-inheriting deny-only ACLs are accepted. The target must be regular, owned by
the effective uid, and lack immutable/append flags. Effective-id faccessat checks
at begin and commit preserve read-only and deny-write intent. This is a preflight,
not atomic authorization; same-uid/root races are outside the threat model.

JNI methods are registered eagerly at library loading. Lookup calls stop on a
pending exception; global references are cleaned on failed load and unload.
Java additionally probes all three transaction methods with invalid arguments and requires native ABI token 0x58415201 before enabling writes. Only JNI_OnLoad/Unload are exported. Failed registration is unregistered while preserving the original exception. Missing, unset and mismatched libraries fail before any profile file is created.
Cleanup failure distinguishes +leftover from +close (or both) on the primary native code.
Successful rename followed by a native close error uses atomic-committed:close:
the save has already been applied and cannot be rolled back.

If both descriptor-stat attempts fail after creation, the code reports
atomic-temporary-stat-leftover and refuses to unlink an unverified name. A private
empty file may remain. Interrupted create can likewise report an uncertain
private leftover. No age/glob cleanup is performed. JVM death or exhaustion at a
native-call boundary may leave one private temporary file and OS-owned resources.
These are limits, not a zero-leftover guarantee under arbitrary failure. Sustained failures can leave one private file per retry; no accumulation bound is claimed.

The native duplicate means Java close is not the last close. On a nonlocal
filesystem, fsync precedes rename to check writeback. Only an injected error in
that branch is tested; real network homes and power-loss durability are unqualified.
Fixed error codes carry no path or payload. The implementation intentionally
omits errno detail from the earlier design recommendation.

## Deliberate differences requiring product acceptance

Successful bytes are preserved. Existing readers and hard-link aliases retain
old content; the target receives a new private inode. Failed serialization leaves
the previous file unchanged instead of truncated/partial. Existing target ACLs
are dropped; hard links are split. Inode, group, birthtime, xattrs and ordinary
file flags are not copied. Root-owned private parents are allowed in code but
not independently exercised. RuntimePermission(writeFileDescriptor) is newly required under a SecurityManager. Parent read/write/search access is newly required;
final symlinks, foreign ownership and disallowed parents are refused.

The strict UTF-8 path encoder and interior dot-component rejection are experimental
restrictions and must not silently become product behavior. The explicit fixture
boundary and Java hook must never ship. Actual filename normalization/case and
long-name behavior remain to be tested. A pure-Java suppression helper skips self-suppression and preserves the primary if adding suppression fails. Four pure-Java runs cover self, distinct and disabled suppression; actual JVM exhaustion is not injected. The original handler swallows Exceptions
and does not reset changeCount, so integration must address visible save failures
and repeated replacement cost without changing controller commands or polling.

## Offline checks and evidence

The runner pins audit27 JAR e0fe515d1a02e53afd6e3aadc3ba0c4d4ab2878e3981aacc687015710ed6ff62,
the compiler, Python and both runtime trees/signatures. Source bytes, probes,
native outputs and recorded native tool inputs are checked before/after. Repeated
native outputs match by architecture. Native metadata is not a complete SDK lock.
`--require-clean` verifies every source at the recorded Git commit. A clean
execution remains qualification=false because this is not product integration.

The matrix requires 16 differential runs of 37 cases: both runtimes, Xint/Xcomp,
umask 000/022/077/0277. Read-only fixtures compare the actual audit27 helper's
failure; a hook assertion ensures commit-time freezing really occurs. Parent ACL
allow/inherit/deny cases are separate. Directory listings are recursive and the
new target ACL is inspected independently. Twenty-six interpreted native negatives
must fail at their intended assertion, not a crash, timeout or verifier error.
A planted target between native precheck and rename reaches RENAME_EXCL itself.

Forty-four fault runs cover eleven source-injected failures/recovery paths under
both modes/runtimes, with 32 repetitions and zero measured FD/GC growth. They
exercise stat retry/private leftover, mode, dup, rename, cleanup, remote sync success/failure, statfs failure,
post-commit close and exclusive-rename contention. These are fault-injected source
variants, not actual filesystem I/O failures. Thirty-two binding variants check
normal operation, missing/unset/mismatched, no-OnLoad and stale-ABI libraries and security-manager denials.

A separate -Xcheck:jni loading control compares exact stdout with an empty
JNI_OnLoad library. Both exhibit the same two loader warnings on the observed
runtime. No warning is silently discarded. This comparative load result does
not prove the runtime warnings' source. Two full interpreted functional runs and interpreted rename-failure runs additionally use -Xcheck:jni and require that exact warning prefix, with no extra diagnostics. Normal and mismatched-library binding cases are also checked this way.
Vendor native close implementation remains unverified; runtime Java attachment
sources and FileDescriptor bytecode are hash bound.

Not yet qualified: FileBasedPreferences.synchronize caller integration, native
packaging, full GUI, physical Intel, actual foreign users/root, ownership-disabled
filesystems, hostile same-user races, real remote filesystems, close/syscall
failures rather than injected variants, and arbitrary JVM exhaustion. x64 is
Rosetta. Stored credentials are not claimed encrypted; HTTP remains plaintext.

## Reproduction

From the repository root, with the pinned compiler and both audit27 runtimes:

```
/opt/homebrew/bin/python3 -E -s experiments/atomic-preferences/check.py \
  --jdk /path/to/pinned/compiler/Contents/Home \
  --output build/atomic-preferences-new-run --require-clean
```

Output must be new. Use only disposable fixtures. Actual Claude static reviews
are archived under audit; they are not executed tests. Excluded development runs:
3 failed on JNI warning output and deny-delete fixture cleanup; 4 exposed read-only
race setup under umask 0277; 5/6 exposed assertion ordering in negative controls;
7 exposed inherited deny-delete cleanup in an intentionally weakened native mutant. Run 11 failed compilation because a suppression control tried to subclass final Session; the control now exercises a package-private pure-Java helper and Session remains final. Runs 8, 9 and 10 passed only at their recorded intermediate sources and are superseded by the expanded matrix.
Expanded tests and specific cleanup supersede those incomplete runs.

Development run `build/atomic-preferences-development-12/observations.json` passes
the expanded matrix at dirty experimental source. Its tracked copy is
`audit/atomic-preference-development.json`. The clean reproduction record is a
separate next step; neither record qualifies product integration.
