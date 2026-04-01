"""
OpenSeesPy 建模与简单静力分析。

使用：
- node / elasticBeamColumn / equalDOF / zeroLength 等命令
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import os
import sys

# 使用仓库自带的 `zwind` 包装 OpenSees，
# 避免直接依赖系统级 openseespy DLL。
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import zwind as ops

from clip_generator import EqualDofClip, ZeroLengthClip
from dsl_schema import ConstraintSupportBase, DslModel
from geometry_generator import Element, Node as GeoNode


def _build_support_info(dsl: DslModel) -> Dict[str, bool]:
    supports: Dict[str, bool] = {}
    for c in dsl.constraints:
        if isinstance(c, ConstraintSupportBase):
            supports[c.target] = True
    return supports


def build_and_run_opensees(
    dsl: DslModel,
    nodes: List[GeoNode],
    elements: List[Element],
    equal_clips: List[EqualDofClip],
    zl_clips: List[ZeroLengthClip],
) -> Dict[str, object]:
    """
    构建 OpenSees 模型并执行简单静力分析，返回节点位移等结果。
    """
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    # 定义节点
    for n in nodes:
        ops.node(n.id, n.x, n.y, n.z)

    # 材料与截面（统一简化）
    ops.uniaxialMaterial("Elastic", 1, 3.0e7)
    # 使用 elasticBeamColumn 时需要截面刚度参数，这里简单统一
    A = 0.04
    E = 3.0e7
    G = 1.2e7
    J = 8.0e-5
    Iy = 8.0e-5
    Iz = 8.0e-5

    # 坐标变换
    # 不同单元方向使用不同的参考向量，以避免 v 与局部 x 轴平行：
    # - 对主要沿 X/Y 方向的单元，使用 v = (0, 0, 1)
    # - 对主要沿 Z 方向的单元（竖向柱），使用 v = (0, 1, 0)
    transf_xy = 1
    transf_z = 2
    ops.geomTransf("Linear", transf_xy, 0.0, 0.0, 1.0)
    ops.geomTransf("Linear", transf_z, 0.0, 1.0, 0.0)

    # 为选择合适的几何变换，先建立节点查找表
    node_map = {n.id: n for n in nodes}

    # 梁柱单元
    for e in elements:
        ni = node_map[e.i]
        nj = node_map[e.j]
        dx = nj.x - ni.x
        dy = nj.y - ni.y
        dz = nj.z - ni.z
        # 判断主方向
        if abs(dz) >= abs(dx) and abs(dz) >= abs(dy):
            t_tag = transf_z  # 竖向构件
        else:
            t_tag = transf_xy  # 水平构件

        ops.element(
            "elasticBeamColumn",
            e.id,
            e.i,
            e.j,
            A,
            E,
            G,
            J,
            Iy,
            Iz,
            t_tag,
        )

    # 支座
    supports = _build_support_info(dsl)
    for n in nodes:
        if n.z == 0.0 and n.entity_id in supports:
            ops.fix(n.id, 1, 1, 1, 1, 1, 1)

    # 刚性夹子（equalDOF）
    for c in equal_clips:
        ops.equalDOF(c.master, c.slave, *c.dofs)

    # 弹性夹子（zeroLength）
    # 为每个 zeroLength 夹子定义一个简化弹簧材料
    mat_base_tag = 1000
    for idx, c in enumerate(zl_clips, start=0):
        mat_tag = mat_base_tag + idx
        ops.uniaxialMaterial("Elastic", mat_tag, c.axial_k)
        # 只在轴向方向起作用，这里示意地绑定到 x 方向自由度
        ops.element(
            "zeroLength",
            5000 + idx,
            c.i,
            c.j,
            "-mat",
            mat_tag,
            "-dir",
            1,
        )

    # 施加竖向重力荷载（简化为统一竖向集中力）
    ops.timeSeries("Linear", 1)
    load_pattern_tag = 1
    ops.recorder("Node", "-file", "node_disp.out", "-time", "-nodeRange", 1, len(nodes), "-dof", 1, 2, 3, "disp")

    # 这里使用统一的竖向荷载：对所有顶层节点施加向下集中力
    max_z = max(n.z for n in nodes)
    top_nodes = [n for n in nodes if n.z == max_z]
    total_load = -100.0 * len(top_nodes)
    per_node = total_load / len(top_nodes) if top_nodes else 0.0

    ops.pattern("Plain", load_pattern_tag, 1)
    for n in top_nodes:
        ops.load(n.id, 0.0, 0.0, per_node, 0.0, 0.0, 0.0)

    # 静力分析
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.test("NormDispIncr", 1.0e-6, 10)
    ops.algorithm("Newton")
    ops.integrator("LoadControl", 1.0)
    ops.analysis("Static")
    ok = ops.analyze(1)

    # 收集位移结果
    displacements: Dict[int, Tuple[float, float, float]] = {}
    if ok == 0:
        for n in nodes:
            ux, uy, uz = (
                ops.nodeDisp(n.id, 1),
                ops.nodeDisp(n.id, 2),
                ops.nodeDisp(n.id, 3),
            )
            displacements[n.id] = (ux, uy, uz)
    else:
        print("WARNING: OpenSees analysis did not converge.")

    max_uz = 0.0
    if displacements:
        max_uz = min(uz for (_, _, uz) in displacements.values())

    result = {
        "displacements": displacements,
        "max_vertical_disp": max_uz,
    }
    print("=== OpenSees Analysis Result ===")
    print(f"max_vertical_disp: {max_uz}")

    return result


__all__ = ["build_and_run_opensees"]

