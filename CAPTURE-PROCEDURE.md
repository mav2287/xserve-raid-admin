# Narrow observation procedure — not executed

No live capture was taken in this audit. Existing saved targets and volume usage were not inspected, and there is no established disposable/unmounted hardware test environment. Do not launch the application merely to collect traffic: it can automatically discover or poll saved controllers.

## Preconditions

Identify the exact client interface/IP, controller IP and controller identity without scanning a subnet. Establish whether production volumes are mounted; tests against those volumes require immediate explicit user confirmation. Firmware, layout, disk/cache/network changes, power operations and non-disposable rebuilds always need immediate explicit confirmation, even if an earlier maintenance plan exists. Treat diagnostics and parity scans as potentially mutating until proven otherwise.

## Metadata-only packet observation

For an approved read-only session, substitute one known client and one known controller into this template. Do not execute the placeholders literally:

```text
sudo tcpdump -i <interface> -nn -q -tt -c 100 \
  'tcp and port 80 and host <client-IP> and host <controller-IP>'
```

Use a short, bounded session and stop immediately after the intended observation. `-q` produces packet summaries; do not add `-A`, `-X`, verbose application decoding, or `-w`. Do not persist raw pcap files: HTTP headers contain credentials. This procedure captures packet counts/timestamps/lengths, not full wire semantics; it cannot prove method/path/body parity. Keep even private IP metadata local or pseudonymize before sharing.

Bonjour capture, if needed later, must have a separate bounded filter for the chosen interface and known controller sources with UDP port 5353. Never broaden to all subnet traffic. No ARP sweep, service scan or high-rate discovery.

## Full wire parity remains pending

Before recording real requests, build a tested in-memory sanitizer that discards authentication headers, passwords, account values and sensitive payload fields **before persistence**. Never record first and redact later. Allowlist paths/commands and structural body fields; treat unknown payloads as nonrecordable. Verify with synthetic mixed-case headers, malformed messages, split packets and credentials in bodies. Current `safe_event` is for harness event metadata only, not an HTTP sanitizer.

Compare original and compatibility sessions for HTTP method/path; approved nonsensitive headers; parameter structure and byte encoding; order; retry timing; connection reuse; UI terminal state; and controller event evidence. Keep credentials out of hashes as well as text. The application User-Agent discrepancy (1.5.1 default versus 1.6.0 ACP override) must be included in fidelity tests. Record expected modernization, documented correction, runtime difference or regression for every discrepancy.
