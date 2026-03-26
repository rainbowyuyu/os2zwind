"""
Minimal example: use `import zwind as ops` instead of `import opensees as ops`.

It keeps the rest of the OpenSeesPy workflow unchanged.
"""

from __future__ import annotations

import os
import sys


# Ensure the repository root is importable so `zwind/` can be found.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import zwind as ops


# ------------------------------
# Simple 1D truss (static)
# ------------------------------
ops.wipe()
ops.model("basic", "-ndm", 1, "-ndf", 1)

ops.uniaxialMaterial("Elastic", 1, 3000.0)
ops.node(1, 0.0)
ops.node(2, 72.0)
ops.fix(1, 1)
ops.element("truss", 1, 1, 2, 10.0, 1)

ops.timeSeries("Linear", 1)
ops.pattern("Plain", 1, 1)
ops.load(2, 100.0)

ops.constraints("Transformation")
ops.numberer("Plain")
ops.system("BandSPD")
ops.test("NormDispIncr", 1e-8, 10, 2)
ops.algorithm("Linear")
ops.integrator("LoadControl", 1.0)
ops.analysis("Static")

ok = ops.analyze(1)
print("analyze ok:", ok, "time:", ops.getTime())

