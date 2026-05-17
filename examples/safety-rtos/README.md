# Automotive Safety RTOS Validation Project

This validation corpus describes a lightweight real-time safety operating
system for an automotive ECU. It is ISO 26262-inspired, but it is not a
certifiable safety case or a production RTOS specification.

The corpus is designed to validate `planttoxmi` at three levels:

- Requirements: stable IDs, safety goals, kernel, platform, API, timing
  constraints, and traceability.
- Architecture: importable component diagrams for complete RTOS service,
  platform, safety, and application integration views.
- Detailed design: importable sequence diagrams for selected runtime flows.
- UML coverage: at least one example for every UML structure and behavior
  diagram type, including unsupported future conversion targets.

The project also includes richer UML diagrams for every UML structure and
behavior diagram family, so the converter can be exercised across a broad
EA-importable validation set.

## Validation Commands

Inspect every diagram:

```powershell
Get-ChildItem examples\safety-rtos\diagrams -Recurse -Filter *.puml |
  ForEach-Object { planttoxmi inspect $_.FullName }
```

Convert importable diagrams:

```powershell
Get-ChildItem examples\safety-rtos\diagrams\importable -Filter *.puml |
  ForEach-Object {
    planttoxmi convert $_.FullName -o "$env:TEMP\$($_.BaseName).xmi" --profile ea
  }
```

All diagrams under `diagrams/importable` should inspect as supported and convert
to EA-profile XMI. The set covers requirements, component, class, object,
package, composite structure, deployment, profile, use case, activity, state
machine, sequence, communication, interaction overview, and timing diagrams.
