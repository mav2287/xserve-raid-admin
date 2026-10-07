# Preference save-site findings

FACT: immutable Apple bytecode selects `MacPreferences` on a Mac OS name through
`PreferencesFactory`. RAID Admin call sites use `com.apple.RAIDAdmin.plist`.
MacPreferences prepends FileManager's preferences-folder result and File.separator.
If findFolder throws Exception, it falls back to a relative identifier. Its null
identifier default is `preferences.plist`, not `defaultpreferences.plist`.
The current FileManager override derives the folder from user.home. No native
factory or actual preference-folder access was executed for this inventory.

FACT: Apple counter writes occur in FileBasedPreferences.load (zero at PC89),
Preferences.set (increment on replacement/addition at PC113 or successful removal
at PC153), and Preferences.remove (successful removal at PC36). Equal non-null
values avoid the increment; changes are copied through the original plist code.
Successful store does not reset the count. Synchronize calls store under the lock
only when count is positive. The separate com.chaotic.Preferences class has its
own three writes and must not be conflated with Apple's backend.

FACT: direct Apple synchronize call sites include DefaultSystemRegistry's
synchronizePrefs, three PreferencesWindow action listeners, the license-acceptance
listener RaidAdmin$1, and SystemMonitorWindow.updatePreferences. Registry update
and removal paths call synchronizePrefs. Window preference updates are also called
by close/quit paths in the selected bytecode. These are static call sites;
actual event frequency and full runtime reachability remain UNRESOLVED.

INFERENCE: after the first change, further synchronize calls can repeatedly save
until a load resets the counter. An atomic replacement then creates a new inode
for each successful save, even without a new change. No count reset, deduplication,
polling interval or retry change is authorized by this finding. Preserve semantics
and qualify the cost/failure reporting separately.

FACT: the filename experiment confirms raw-stream lossy surrogate substitution,
NIO rejection of those inputs, and different Java-listing/raw-name normalization.
The fixture helper's component rejection and realpath boundary must not be copied
into a shipping helper. Ordinary dot/dotdot must retain kernel resolution behavior.
Strict malformed-name rejection is a proposed security difference; original
application basename is ASCII, but complete identifier reachability remains
unqualified. Existing-name aliases and full path-length limits remain open.

SECURITY DECISION: binding failure must not silently fall back to the insecure
in-place stream. The current experimental unavailable-library exception is swallowed
by the original caller, so shipping requires visible, rate-limited, fixed-code
failure reporting without paths or credentials. This is a remaining integration
requirement, not implemented shipping behavior. Confidentiality is not encryption;
HTTP remains plaintext and prior readers of old public inodes retain old data.

Source evidence: immutable Apple JAR, audit/static-inventory.json, selected
original class hashes and bytecode produced by
experiments/atomic-preferences/paths/inventory.py. Selection includes 22 classes and
23 methods matching selected call names. Only FileBasedPreferences differs among those audit27 entries.
Static selection is not proof of all reflective/native accesses or runtime timing.
