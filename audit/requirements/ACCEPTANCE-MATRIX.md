# Acceptance matrix

Copy this table into test reports and add evidence links. “Pass” requires an
observable expected result, not the absence of an error dialog.

| Area | Test | Original reference | Compatibility build | Wire parity | Hardware evidence | Status |
|---|---|---|---|---|---|---|
| Startup | Launch from Finder on Apple silicon |  |  | N/A |  | Not run |
| Startup | Launch with no system Java installed |  |  | N/A |  | Not run |
| Startup | Damaged/missing bundled runtime gives useful error | N/A |  | N/A |  | Not run |
| Identity | About/diagnostics show Apple baseline and modern build |  |  | N/A |  | Not run |
| Discovery | Find both controllers on Ethernet |  |  |  |  | Not run |
| Discovery | Find controllers on Wi-Fi where network permits |  |  |  |  | Not run |
| Discovery | Interface changes do not duplicate or lose identities |  |  |  |  | Not run |
| Discovery | Sleep/wake recovery |  |  |  |  | Not run |
| Connection | Direct-IP connection to each controller |  |  |  |  | Not run |
| Connection | Monitor authentication |  |  |  |  | Not run |
| Connection | Administrator authentication |  |  |  |  | Not run |
| Connection | Wrong password produces visible failure |  |  |  |  | Not run |
| Connection | Disconnect and reconnect in the same app session |  |  |  |  | Not run |
| Connection | Quit/relaunch and reconnect |  |  |  |  | Not run |
| Connection | One controller unavailable |  |  |  |  | Not run |
| Connection | Controller timeout and later recovery |  |  |  |  | Not run |
| Security | Password absent from all logs and diagnostics |  |  | N/A |  | Not run |
| Security | External XML entity/file/network access blocked |  |  | N/A | Emulator | Not run |
| Status | System overview |  |  |  |  | Not run |
| Status | Both controller status pages |  |  |  |  | Not run |
| Status | Drive inventory and state |  |  |  |  | Not run |
| Status | RAID set and volume inventory |  |  |  |  | Not run |
| Status | Power, cooling, temperature, and battery state |  |  |  |  | Not run |
| Status | Event log retrieval and display |  |  |  |  | Not run |
| Status | Controller time display and refresh |  |  |  |  | Not run |
| Polling | Continuous 24-hour monitoring without loss |  |  |  |  | Not run |
| Polling | Request rate matches expected original behavior |  |  |  |  | Not run |
| Network | Read both controller network settings |  |  |  |  | Not run |
| Network | Validate network-setting edits before submission |  |  |  |  | Not run |
| Network | Apply and rediscover after approved address change |  |  |  |  | Not run |
| RAID | Read RAID configuration |  |  |  |  | Not run |
| RAID | Create test RAID set on disposable media |  |  |  |  | Not run |
| RAID | Delete test RAID set with confirmation |  |  |  |  | Not run |
| RAID | Rebuild begins with designated replacement disk |  |  |  |  | Not run |
| RAID | Rebuild progress and completion are accurate |  |  |  |  | Not run |
| Drive | Identify and inspect each drive |  |  |  |  | Not run |
| Drive | Failure/removal/insertion state transitions |  |  |  |  | Not run |
| Cache | Read cache configuration |  |  |  |  | Not run |
| Cache | Approved reversible cache setting change |  |  |  |  | Not run |
| Diagnostics | Retrieve available diagnostic information |  |  |  |  | Not run |
| Power | Restart one test controller |  |  |  |  | Not run |
| Power | Reconnect after controller restart |  |  |  |  | Not run |
| Firmware | Reject wrong extension/type visibly |  |  | N/A | Emulator | Not run |
| Firmware | Reject malformed archive visibly |  |  | N/A | Emulator | Not run |
| Firmware | Parse known-good `.xfb` and show metadata |  |  | N/A | Offline | Not run |
| Firmware | Confirm exact images before transfer |  |  | N/A | Offline | Not run |
| Firmware | Transfer progress is visible |  |  |  |  | Not run |
| Firmware | Controller acknowledgement is verified |  |  |  |  | Not run |
| Firmware | Restart/reconnect/version verification |  |  |  |  | Not run |
| macOS | File chooser and dialogs behave normally |  |  | N/A |  | Not run |
| macOS | Keychain remember/update/forget | N/A |  | N/A |  | Not run |
| macOS | Menus, shortcuts, focus, Retina, accessibility |  |  | N/A |  | Not run |
| Distribution | Clean install passes Gatekeeper | N/A |  | N/A | Clean Mac | Not run |
| Distribution | Signature and notarization validate | N/A |  | N/A |  | Not run |
| Distribution | Offline reproducible build matches manifest | N/A |  | N/A |  | Not run |

## Evidence format

For each completed row, record:

- Build commit and application hash
- macOS version and architecture
- JRE version and hash
- RAID firmware versions and controller address/identity
- Preconditions, including whether volumes were mounted
- Exact action taken
- Expected result
- Actual result
- Relevant redacted log excerpt
- Packet-capture comparison or reason it is not applicable
- Controller event-log entry where applicable
- Pass, fail, blocked, or unsupported conclusion
- Issue link for every failure or unexplained difference

