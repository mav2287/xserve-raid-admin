# RAID Admin modern macOS compatibility project

This folder is a handoff plan for auditing and completing the modernization of
Apple RAID Admin 1.5.1 for current macOS releases while preserving the original
application's appearance, behavior, controller protocol, and operational
semantics as closely as possible.

The objective is not merely to make the application launch. The objective is to
establish, with recorded evidence, that every supported original operation works
correctly on modern macOS, fails visibly and safely when it cannot work, and
does not issue different controller commands without an explicit reason.

Start with [PLAN.md](PLAN.md). Verified facts from the installed application are
in [EVIDENCE.md](EVIDENCE.md). The required behavioral test inventory is in
[ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md).

## Source and reference artifacts

- Source repository: <https://github.com/mav2287/xserve-raid-admin>
- Installed reference application: `/Applications/RAID Admin.app`
- Original application version represented by the bundle: `1.5.1`
- Modern target used during initial testing: macOS 26.6.2 Tahoe on Apple
  silicon/arm64

Do not modify the installed reference application. Copy artifacts into a test
workspace and record hashes before inspecting or transforming them.

## Definition of done

The project is complete only when:

1. The source and build provenance are understood and reproducible.
2. Every item in `ACCEPTANCE-MATRIX.md` has a documented result.
3. Equivalent actions produce equivalent controller requests to the original
   application, except for reviewed and documented corrections.
4. Failures are reported to the user instead of disappearing into disabled
   logging.
5. Destructive and firmware operations have explicit preflight checks and have
   been tested in an appropriate maintenance environment.
6. The release bundles its supported runtime, is signed and notarized, and has
   a version distinguishable from Apple's original release.

