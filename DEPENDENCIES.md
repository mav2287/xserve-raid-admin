# Dependencies and SBOM

[audit/sbom.json](audit/sbom.json) is a machine-readable, file-complete inventory of the 3,043 non-directory entries in the immutable candidate JAR. It is a project schema, not falsely labeled SPDX/CycloneDX compliant. It includes every entry hash, component aggregate hashes, observed versions, notice evidence and explicit unknowns. The original JAR hash is the acquisition anchor; aggregate component hashes are not upstream distribution checksums.

| Component | Observed version | Evidence / license status |
|---|---|---|
| Apple application/support | 1.5.1, development 1.5.1GMc5 | Versions.properties; Apple license images present; official provenance/redistribution unresolved |
| JmDNS | 0.2 | JmDNS static VERSION initializer; license not established from this intake |
| Xerces | 2.0.0 | `org.apache.xerces.impl.Version` literal; exact distribution/license provenance unresolved |
| Xalan | 2.3.0 | XSLProcessorVersion initializer; XML/XPath helpers bundled; exact distribution/license provenance unresolved |
| Log4j | 1.x, exact release unresolved | Legacy namespace/API and root OFF configuration; do not assert a precise version/CVE from package names |
| BCEL | Unresolved | Bundled BCEL.LICENSE.txt states Apache Software License 1.1 |
| Apache regexp | Unresolved | regexp.LICENSE.txt states Apache Software License 1.1 |
| JLex | Unresolved | Bundled custom permissive notice; retain full text |
| Java CUP and runtime | 0.10j | java_cup.version constants; separate custom generator/runtime notices |
| W3C DOM, SAX, JAXP and HTML/WML implementations | Mixed/unresolved | Vendored namespaces, some may be superseded by JDK parent loading |
| Chaotic plist/preferences/rendezvous/Base64 support | Unresolved | Bundled classes; no independent release/notice provenance established |
| Stanford BrowserLauncher | Unresolved | Bundled class; version/license unresolved |
| Four modernization Java patches | Repository commit | No repository-wide license file found |
| Build/runtime JDK used in audit | Amazon Corretto 8 1.8.0_362 arm64 | Exact 224-file lock and aggregate hash in jdk-lock.json; no runtime bundled; redistribution/support not qualified |
| Python | Recorded per build manifest | Standard library only for audit tools; no pip dependency needed |
| macOS tools | Host supplied | Upstream uses bash, java_home, jar/javac, codesign; launcher uses osascript, sips, and open via FileManager |

The deterministic builder hashes its own script, source patches, template build script and JDK lock in provenance. It avoids dependency downloads. The launcher and icons are hashed individually. There is no native helper to hash and no bundled-JRE hash to report; these fields are explicitly absent, not invented.

Do not replace bundled libraries wholesale without classloading, XML compatibility and wire regression tests. Known gaps include permissive external XML resolution, credential-bearing object formatting, old discovery APIs and unqualified runtime behavior. No current vulnerability-database audit or legal redistribution determination was performed. Before distribution, resolve all NOASSERTION licenses, generate a standard release SBOM, and qualify a maintained runtime independently.

The user accepts the GitHub repository JAR as the authoritative project baseline.
Historical digest discrepancies and independent Apple acquisition evidence do
not block the authorized compatibility work.

## Pinned runtime candidate

Amazon Corretto 8.504.04.1 is now pinned for macOS aarch64 and x64 in
`audit/runtime-lock.json`, with archive URLs/hashes, per-file hashes and vendor
permission bits. Vendor signatures verify as `com.amazon.corretto.8`, Team
`94KV3E626L`. Archives were obtained from the [official download catalog](https://docs.aws.amazon.com/corretto/latest/corretto-8-ug/downloads-list.html);
future builds use recorded versioned URLs and hashes, never a floating latest URL.
The full vendor JDK bundle and its LICENSE, ASSEMBLY_EXCEPTION and
THIRD_PARTY_README files are preserved. Public redistribution/source-availability
requirements and the application's legacy dependencies still require resolution
before publication. The runtime is local to the build; no system JDK was replaced.
