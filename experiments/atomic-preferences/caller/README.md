# Preserved preference caller experiment — not shipping

The probe calls the original Apple and audit27 FileBasedPreferences.synchronize
methods through isolated child loaders. Only the candidate adapter helper changes;
three atomic helper classes are added from the hash-bound clean experiment.
Backend class bytes and every other audit27 entry remain identical. ZIP metadata
is normalized; this is an entry-content comparison, not archive-byte identity.

The 19 cases re-expect the original 18 scenarios for atomic saving and add the
zero-count case on both backends. Successful XML bytes match the Apple reference.
Invalid-key Exceptions remain swallowed, Error identity/cause/suppression remain,
changeCount is preserved and the actual callback executes under the store lock.
Existing profiles receive a new private inode. Serialization failure retains the
old bytes and metadata; final symlinks and dangling links are refused. Interrupt
flags and successful/Exception/Error save-loop FD/GC counts are checked.

The SecurityManager denies networking, execution, native preferences permission,
security-manager replacement, external writes/deletes, preferences-folder reads
and unapproved native libraries. A fake user.home is supplied. These are fixture
guards, not a general native sandbox; native writes also depend on the explicit
boundary in AtomicPreferenceFile. No factory, Main or GUI is exercised. The guard
counter must remain zero. Missing factory-class property was removed: permission
and native-library denials are the actual native-preferences tripwires.

The callback records its first failure instead of throwing inside the serializer,
so an old/in-place helper fails specifically at actual-helper-chain rather than a
generic outer error. Class origins, null loader parents, helper absence from the
Apple JAR and library availability are asserted. JAR indexes, versioned entries,
manifest Class-Path and duplicate entries are rejected. After each positive run
the exact recursive directory-entry set must match, not merely absence of .xra
files. Compiler/runtime/native/JAR/probe/source and prior-helper hashes are checked.

Sixteen interpreted negatives cover old audit27 helper, unset library, Error
swallowing/wrapping/suppression, in-place writing, nonisolated and swapped loaders.
They must fail at their precise assertion and fixture-only frames, never a crash,
timeout or arbitrary exception. Development run 7 passes four variants of 19 cases
and sixteen controls; it is dirty-source evidence, qualification=false. Run 4
failed because a mutation-hash map was initialized too late; it is excluded.
Earlier 8-case and weaker runs are superseded by this expanded evidence.

Clean execution requires --require-clean after committing these sources. The
pinned clean native experiment and its classes must be present. Example:

```
/opt/homebrew/bin/python3 -E -s experiments/atomic-preferences/caller/check.py \
  --jdk /path/to/pinned/compiler/Contents/Home \
  --output build/atomic-caller-new-run --require-clean
```

The output must be new and inside the real repository build directory. x64 runs
under Rosetta. Root/foreign users, actual I/O failure, full GUI, real profiles,
Main/factory, native release packaging and hardware remain unqualified. No release
JAR or installed app is changed. HTTP remains plaintext; no credential encryption
claim is made. Actual Claude reviews are archived under audit.
