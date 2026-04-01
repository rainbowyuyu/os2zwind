"""
夹子生成器：基于 KD-Tree 的最近邻搜索，自动在结构之间生成连接约束。

输出：
- rigid 夹子 → equalDOF 约束数据
- elastic 夹子 → zeroLength 单元数据（含简化刚度）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from scipy.spatial import cKDTree as KDTree

from dsl_schema import ConstraintConnectNearest, DslModel
from geometry_generator import Node, NodeId


@dataclass
class EqualDofClip:
    master: NodeId
    slave: NodeId
    dofs: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)


@dataclass
class ZeroLengthClip:
    i: NodeId
    j: NodeId
    axial_k: float  # 仅示意，统一使用简化轴向刚度


def _build_entity_nodes_index(nodes: Sequence[Node]) -> Dict[str, List[Node]]:
    result: Dict[str, List[Node]] = {}
    for n in nodes:
        result.setdefault(n.entity_id, []).append(n)
    return result


def _generate_clips_between_two(
    nodes: Sequence[Node],
    entity_nodes: Dict[str, List[Node]],
    constraint: ConstraintConnectNearest,
) -> Tuple[List[EqualDofClip], List[ZeroLengthClip]]:
    e1, e2 = constraint.between
    if e1 not in entity_nodes or e2 not in entity_nodes:
        return [], []

    nodes_1 = entity_nodes[e1]
    nodes_2 = entity_nodes[e2]

    # 以实体 2 为“目标”，构建 KD-Tree
    coords_2 = [(n.x, n.y, n.z) for n in nodes_2]
    tree = KDTree(coords_2)

    equal_clips: List[EqualDofClip] = []
    zl_clips: List[ZeroLengthClip] = []

    tol = constraint.tolerance
    z_tol = constraint.z_tolerance
    d_rigid = tol * 0.3  # 自动模式下的刚性阈值

    for n1 in nodes_1:
        # 只考虑同层近似节点：先用 z 过滤
        # 在 KDTree 里只能用全局距离，这里先查询，再用 z_tol 精化
        dist, idx = tree.query((n1.x, n1.y, n1.z), k=1)
        if dist > tol:
            continue
        n2 = nodes_2[idx]
        if abs(n1.z - n2.z) > z_tol:
            continue

        mode = constraint.mode
        used_mode = mode
        if mode == "auto":
            used_mode = "rigid" if dist <= d_rigid else "elastic"  # type: ignore[assignment]

        if used_mode == "rigid":
            equal_clips.append(EqualDofClip(master=n1.id, slave=n2.id))
        else:  # elastic
            # 简化刚度：与距离成反比，防止除零
            axial_k = 1e5 / max(dist, 1e-3)
            zl_clips.append(ZeroLengthClip(i=n1.id, j=n2.id, axial_k=axial_k))

    return equal_clips, zl_clips


def generate_clips(
    dsl: DslModel,
    nodes: Sequence[Node],
) -> Tuple[List[EqualDofClip], List[ZeroLengthClip]]:
    """
    根据 DSL 中的 connect_nearest 约束，自动生成夹子。
    """
    entity_nodes = _build_entity_nodes_index(nodes)

    all_equal: List[EqualDofClip] = []
    all_zl: List[ZeroLengthClip] = []

    for c in dsl.constraints:
        if isinstance(c, ConstraintConnectNearest):
            eqs, zls = _generate_clips_between_two(nodes, entity_nodes, c)
            all_equal.extend(eqs)
            all_zl.extend(zls)

    return all_equal, all_zl


__all__ = ["EqualDofClip", "ZeroLengthClip", "generate_clips"]

