"""
Print the pinned requirements of the Home Assistant integrations Bermuda loads with.

Home Assistant installs the requirements of an integration's dependencies at
runtime. Tests and a plain import outside Home Assistant need them up front:
for example bluetooth -> usb -> serialx, whose ESPHome platform needs
aioesphomeapi. The pins differ between Home Assistant versions, so they are read
from the installed Home Assistant instead of being fixed in requirements_test.txt.

The walk follows "dependencies" and "after_dependencies" of the manifests,
recursively, starting at custom_components/bermuda/manifest.json.

Usage:
    python scripts/ha_component_requirements.py [path/to/manifest.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from homeassistant import components

KEYS = ("dependencies", "after_dependencies")
DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "custom_components" / "bermuda" / "manifest.json"


def component_requirements(manifest_path: Path) -> list[str]:
    """Return the sorted requirements of all integrations reachable from the manifest."""
    root = Path(components.__path__[0])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    todo = [domain for key in KEYS for domain in manifest.get(key, [])]
    seen: set[str] = set()
    requirements: set[str] = set()
    while todo:
        domain = todo.pop()
        if domain in seen:
            continue
        seen.add(domain)
        path = root / domain / "manifest.json"
        if not path.exists():
            # Custom integrations such as googlefindmy are not part of Home Assistant.
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        requirements.update(data.get("requirements", []))
        todo.extend(dependency for key in KEYS for dependency in data.get(key, []))
    return sorted(requirements)


def main() -> None:
    """Print one requirement per line."""
    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MANIFEST
    for requirement in component_requirements(manifest_path):
        print(requirement)


if __name__ == "__main__":
    main()
