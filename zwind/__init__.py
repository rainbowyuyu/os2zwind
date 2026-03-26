"""
zwind: a thin compatibility wrapper for the compiled OpenSeesPy extension.

This package lets you write:
    import zwind as ops

and keep using the same API as:
    import opensees as ops
"""

from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType
from typing import Any


def _get_project_root() -> str:
    # __file__ = <root>/zwind/__init__.py
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _ensure_bin_on_path(project_root: str) -> None:
    bin_dir = os.path.join(project_root, "bin")
    if os.path.isdir(bin_dir) and bin_dir not in sys.path:
        sys.path.insert(0, bin_dir)


def _import_backend() -> ModuleType:
    # Primary name produced by this repository is `opensees.pyd` (module name: `opensees`)
    try:
        return importlib.import_module("opensees")
    except ModuleNotFoundError:
        # Fallback for other build layouts (seen in tests/examples).
        return importlib.import_module("openseespy.opensees")


_ROOT = _get_project_root()
_ensure_bin_on_path(_ROOT)

_ops = _import_backend()


# Re-export public symbols so `zwind.<name>` behaves like `opensees.<name>`.
__all__ = [name for name in dir(_ops) if not name.startswith("_")]

for _name in __all__:
    globals()[_name] = getattr(_ops, _name)


def __getattr__(name: str) -> Any:
    # For any symbol missed by static re-export.
    return getattr(_ops, name)


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + __all__))

