# XML provider and bounded resource characterization

Fixture source: `5d882ec8495aa75e9fdf1dc02ce139077479327a`, clean during observation.

Application source remains `13ac370` (audit.5). No production parser, launcher,
protocol or retry code was changed for this investigation. Guarded fixtures run
11 small synthetic cases through Reader and InputStream on original/candidate,
with both pinned runtimes and default/lowered experimental JAXP properties.
Eight subprocess runs agree on application behavior.

## Facts

The original service entry selects `org.apache.xerces.jaxp.SAXParserFactoryImpl`.
The actual application `getParser()` uses service discovery, enables validation,
then creates a SAX parser. Both factory and XMLReader originate from the tested
JAR, as verified at runtime. The provider is the bundled Xerces 2.0, rather than
the JDK's internal Xerces provider. See [static evidence](xml-parser-static.json)
and [runtime observations](xml-resource-observations.json).

The bundled reader does not recognize secure processing or the tested entity
expansion, total entity size, general entity size and depth limit properties.
Lowering `jdk.xml.*` limits does not change the observed application results.
Independent JDK-provider controls in the same processes accept the three small
control documents with default settings and reject them under lowered settings.
This confirms that the experimental configuration is active for the JDK provider.
The combined size experiment does not distinguish total from individual quotas.

The small internal entity cases, depth 8/30 arrays, 4 KiB/64 KiB strings and
32,768 Unicode characters parse and roundtrip identically on both artifacts and
both runtimes. The original embedded DTD is retained throughout.

Depth 31/32/128 array cases reject with a PropertyListException. Direct readXML
reproduction unwraps an ArrayIndexOutOfBoundsException, not a quota exception.
The original `XMLDTDValidator.handleStartElement` checks array length against
element depth using `if_icmpge`, then indexes the array at that depth. At equality
the resize is skipped and the array access fails. The initial relevant capacity
is 32; `<plist>` and the leaf contribute to the boundary. This is a verified
legacy off-by-one defect, not a usable resource limit.

## Inferences and next implementation gate

Maintained Java XML quotas cannot be assumed to protect the current plist path.
The resolver change prevents external access but does not supply expansion,
depth or document-size quotas. No resource-exhaustion attack or crash threshold
was tested; the absence of these tested controls does not prove every possible
legacy limit is absent.

A thin parser-construction delegate selecting the pinned JDK parser is under
Claude review. It would keep the original handler, validation, local DTD and
serializer while enabling maintained default resource controls. Provider changes
can change parsing semantics and must have explicit differential tests, including
queue error mapping and external-resource rejection. Arbitrary controller body
or depth limits are not justified by synthetic fixtures alone.

## Scope

Heap is fixed at 64 MiB and stack at 1 MiB. Input and canonical text are below
131,072 characters; modest entity output is at most 3,584 characters; tested
array depth is at most 128. No escalating crash search or large allocations occur.
The network/write/preference/exit guard reports zero forbidden attempts.
Application console streams are captured; raw failures are withheld; output
contains fixed categories and hashes. Lowered properties are experiment flags,
never application launcher changes.

Real controller documents, HTTP allocation limits, long-running behavior and
native UI remain unqualified. The x64 runtime runs on this arm64 host under
inferred Rosetta. Actual Claude design/implementation consultations are recorded
in `audit/claude-review/`. The design review's suggestion to look for a missing
service override was refined by the verified existing override, which is preserved.
