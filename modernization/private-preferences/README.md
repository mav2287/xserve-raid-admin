# Private preference saving — audit28

This is a narrow compatibility/security addition to the preserved audit27 application. It is not a rewritten controller client or UI. The original Apple JAR and audit27 build remain immutable comparison artifacts. The only JAR entry changed relative to audit27 is `compat/PreferenceIO.class`; seven helper classes are added. All other uncompressed entries must invert exactly to audit27. XML serialization, FileBasedPreferences store monitor, synchronize catches, changeCount, repeated saves, interrupt flags and all controller commands, polling/retry behavior remain unchanged.

## Deliberate security differences

Preference writes create a same-directory random exclusive, no-follow, close-on-exec temporary file. Ownership, private 0600 mode, ACL, filesystem ownership support and identity checks precede serialization. The original XML serializer writes through its original raw UTF-8 stream; Java closes the writer descriptor before native commit. Existing writable regular files owned by the current user are replaced atomically; absent targets require exclusive rename. A descriptor retains the staged inode for validation and remote writeback checking. Parent directories must be owned by the user or root, not group/world writable, and pass conservative ACL checks. Read-only file intent is checked at begin and commit. Symlinks and unsafe parents are rejected; replacing a hardlinked file deliberately splits its link. Existing metadata/ACLs are not copied onto the private replacement. Parent read/search/write permission is needed, which differs from in-place writes to a writable file in a nonwritable parent.

Java performs the original File/security-manager path check before native availability checks. Kernel path resolution of dot/dotdot and File removal of repeated/trailing slashes are retained. Malformed UTF-16 names fail closed rather than substitute `?`. Raw File-created APFS case/Unicode aliases retain their stored spelling under the tested kernel rename behavior. This is an observed APFS result; other filesystems remain unqualified. The caller filename is passed unchanged to native lookup and rename; no extra stored-name metadata lookup is used. No Java lexical normalization is used. Paths at or beyond the Darwin PATH_MAX boundary fail closed. Non-APFS and remote filesystems remain unqualified; unsupported exclusive rename capabilities fail visibly, with no insecure fallback.

The private native library has a fixed bundle path derived from the helper's JAR CodeSource: `Contents/Frameworks/libPrivatePreference.dylib`. No ambient library search or fixture properties/hooks are shipped. Private methods bind eagerly; partial registration is undone; an exact ABI token is checked. If first load fails, this process permanently refuses saves: correcting the bundle requires restarting the app. Both architecture packages contain the same application JAR and their own runtime/native library.

## Failure semantics

The preserved caller still handles the same IOException/RuntimeException/Error types and retains its original counts/locks. Reporting and cleanup cannot intentionally replace the primary throwable, including reporting-class linkage failure. Native commit/abort takes ownership after native entry, while the Java Session is locked, to avoid dropping the sole handle before entry. No filesystem rename is retried on EINTR: remote commit may be ambiguous. The result is a fixed unconfirmed diagnostic, and the original caller's repeated synchronize behavior is retained.

Only fixed diagnostic codes are emitted, at most once per result category per application helper classloader:

- `RAID_ADMIN_PREFERENCES_SAVE_FAILED`
- `RAID_ADMIN_PREFERENCES_COMMITTED_CLEANUP_FAILED`
- `RAID_ADMIN_PREFERENCES_SAVE_UNCONFIRMED`

No pathname, dictionary, exception text, credential or ACP-Password is rendered. A deferred Swing warning is attempted only when the sanitized bundle launcher selects original zero-argument GUI mode; CLI mode uses stderr and does not initialize AWT for the warning. Actual dialog rendering and shutdown delivery remain unqualified. Errors are not turned into success or swallowed by the caller. A failed cleanup can leave a private staged file; no blanket zero-leftover guarantee or glob deletion exists. Abrupt process termination, arbitrary JVM exhaustion, same-uid/root interference, real remote failure, fsync/power-loss durability and other users/filesystems are not qualified.

## Build and verification

The common output from `tools/secure_build.py` is a nonlaunchable intermediate. Use `tools/secure_package.py` to create per-architecture runnable bundles. Tools require the pinned compiler/Python/runtime and new output paths; no tool installs, launches Main, signs, changes an installed application, accesses actual profiles or contacts controllers.

The frozen original gate drivers remain unchanged. `tools/secure_gate_driver.py` explicitly adapts only artifact identity metadata and static helper comparisons; all Java fixture classpaths use the actual secure JAR. Frozen protocol, behavioral oracles and fixture bodies are not rewritten. The prior in-place-save gate is rerun on rebuilt audit27, and replaced by direct product private-save fixtures on audit28. No static inverse proves a runtime feature; runtime proofs and their scope are separately recorded.

The native fault matrix uses deliberately compiled source variants confined to disposable files. Thirty-three of each 37 functional cases call the actual writer; four race cases invoke its actual private transaction primitives through reflection in test code. No race hook is shipped. Fault tests exercise public PreferenceIO reporting end to end. x64 runtime execution here is Rosetta, not physical Intel. Packages are unsigned and unnotarized. Original Apple redistribution rights, real GUI, Gatekeeper/quarantine and physical controller acceptance remain open/deferred, not passed. HTTP remains plaintext.

Development ABI03 stored-name metadata was removed after raw-name fixtures disproved its need on tested APFS. The original apparent NFD spelling change came from NIO fixture setup normalization. Production uses ABI04 to distinguish the final contract, despite unchanged JNI method signatures. Historical trials/reviews remain preserved; their removed metadata faults are not final product evidence.
