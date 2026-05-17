from __future__ import annotations

import argparse
import json
from pathlib import Path


def emit(payload: dict, exit_code: int) -> None:
    print(json.dumps(payload, indent=2))
    raise SystemExit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Sparx EA XMI import through COM automation.")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--xmi", required=True)
    parser.add_argument("--import-diagrams", type=int, choices=[0, 1], default=1)
    parser.add_argument("--strip-guids", type=int, choices=[0, 1], default=1)
    args = parser.parse_args()

    repository_path = str(Path(args.repository).resolve())
    xmi_path = str(Path(args.xmi).resolve())
    ea = None
    co_initialized = False

    try:
        try:
            import pythoncom
            import win32com.client
        except Exception as exc:
            emit(
                {
                    "ok": False,
                    "stage": "com_import",
                    "message": "pywin32 is unavailable",
                    "exception": repr(exc),
                },
                10,
            )

        pythoncom.CoInitialize()
        co_initialized = True

        try:
            ea = win32com.client.Dispatch("EA.Repository")
        except Exception as exc:
            emit(
                {
                    "ok": False,
                    "stage": "com_create",
                    "message": "Could not create EA.Repository COM object",
                    "exception": repr(exc),
                },
                11,
            )

        opened = ea.OpenFile(repository_path)
        if not opened:
            emit(
                {
                    "ok": False,
                    "stage": "open_repository",
                    "message": "EA could not open the repository",
                    "repository": repository_path,
                },
                12,
            )

        project = ea.GetProjectInterface()
        if ea.Models.Count < 1:
            emit(
                {
                    "ok": False,
                    "stage": "root_model",
                    "message": "The EA repository does not contain a root model/package",
                    "repository": repository_path,
                },
                13,
            )

        root_package = ea.Models.GetAt(0)
        package_guid_xml = project.GUIDtoXML(root_package.PackageGUID)
        ea_error = project.ImportPackageXMI(
            package_guid_xml,
            xmi_path,
            int(args.import_diagrams),
            int(args.strip_guids),
        )
        ea_error = "" if ea_error is None else str(ea_error)

        if _is_import_success(ea_error):
            emit(
                {
                    "ok": True,
                    "stage": "import",
                    "message": "EA import succeeded",
                    "ea_error": "",
                    "imported_package_guid": ea_error.strip() or None,
                    "repository": repository_path,
                    "xmi": xmi_path,
                },
                0,
            )

        emit(
            {
                "ok": False,
                "stage": "import",
                "message": "EA import failed",
                "ea_error": ea_error,
                "repository": repository_path,
                "xmi": xmi_path,
            },
            20,
        )

    except Exception as exc:
        emit(
            {
                "ok": False,
                "stage": "exception",
                "message": "Unhandled exception during EA validation",
                "exception": repr(exc),
                "repository": repository_path,
                "xmi": xmi_path,
            },
            99,
        )
    finally:
        if ea is not None:
            try:
                ea.CloseFile()
            except Exception:
                pass
            try:
                ea.Exit()
            except Exception:
                pass
        if co_initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def _is_import_success(value: str) -> bool:
    stripped = value.strip()
    if stripped == "":
        return True
    if len(stripped) == 38 and stripped.startswith("{") and stripped.endswith("}"):
        guid_body = stripped[1:-1]
        return all(char in "0123456789abcdefABCDEF-" for char in guid_body)
    return False


if __name__ == "__main__":
    main()
