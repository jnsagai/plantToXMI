# planttoxmi

`planttoxmi` converts PlantUML source into deterministic XMI 2.1 suitable for
Sparx Enterprise Architect import workflows.

The project is agentic without LLMs: an orchestrator detects the diagram type,
routes to a specialized deterministic agent, serializes a shared UML
intermediate representation to XMI, and validates the result before reporting
success.

## Install for development

```powershell
uv sync --extra dev
```

If `uv` is not available, use any Python 3.12 environment and install editable:

```powershell
python -m pip install -e ".[dev]"
```

## CLI

```powershell
planttoxmi inspect diagram.puml
planttoxmi convert diagram.puml -o diagram.xmi --profile canonical
planttoxmi validate diagram.xmi --profile ea
planttoxmi generate-samples -o examples/generated --seed 7
```

## EA import validation

`planttoxmi validate --profile ea` performs XML and deterministic XMI profile
checks everywhere. It can also perform a real Sparx Enterprise Architect import
check when run on Windows with EA installed, COM-registered, and a blank EA
repository template available.

Install the optional EA dependency:

```powershell
uv sync --extra dev --extra ea
```

Create a local blank repository, then run:

```powershell
planttoxmi validate diagram.xmi --profile ea --ea-template tools\ea\blank.qea
```

Useful EA options:

```powershell
planttoxmi validate diagram.xmi --profile ea --ea-template tools\ea\blank.qea --ea-strict
planttoxmi validate diagram.xmi --profile ea --json
planttoxmi validate diagram.xmi --profile ea --ea-keep-temp
```

Environment variables for CI:

- `PLANTTOXMI_EA_TEMPLATE`
- `PLANTTOXMI_EA_STRICT=1`
- `PLANTTOXMI_EA_TIMEOUT=120`

EA repositories are not committed. See `tools/ea/README.md`.

## Enterprise Architect Add-In

`planttoxmi` includes an optional Sparx Enterprise Architect Add-In for Windows.

The Add-In allows importing `.puml` files directly into the selected EA package
by calling:

```powershell
planttoxmi convert input.puml -o output.xmi --profile ea
```

The Add-In requires:

- Windows
- Sparx Enterprise Architect
- EA 64-bit recommended
- .NET Framework 4.8
- .NET Framework 4.8 Developer Pack / targeting pack for MSBuild
- `planttoxmi` installed and available on PATH or configured through `PLANTTOXMI_EXE`

See `ea-addin/README.md` for build and installation instructions.

## Enterprise Architect Add-In Updates

The Enterprise Architect Add-In is installed once as a small bootstrapper. The
conversion runtime is updated separately under the user's local AppData folder.

By default, the Add-In checks GitHub Releases only when the user selects
`PlantToXMI -> Check for Updates`; the runtime files are installed under:

`%LOCALAPPDATA%\PlantToXMI\versions\<version>`

The active runtime is tracked by:

`%LOCALAPPDATA%\PlantToXMI\current.json`

Updates do not modify the registered COM Add-In DLL and do not require
administrator privileges after initial Add-In installation.

## EA Visual Confirmation

For visual smoke checks, import PlantUML into a temporary EA repository and
export rendered diagram images:

```powershell
uv run python scripts\ea_visual_confirm.py `
  --template ea\blank.qea `
  --input examples\safety-rtos\diagrams\importable `
  --output-dir ea\visual-confirmation
```

The script writes exported images plus `visual-confirmation.md` for review.

## Current coverage

Fully implemented v1 agents:

- Component diagrams
- Sequence diagrams

Other PlantUML UML diagram families are registered as deterministic
placeholders and return structured unsupported-diagram diagnostics.
