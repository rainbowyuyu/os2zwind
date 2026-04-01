"""
三维布尔运算模块（结构级别，基于节点集合与坐标去重的简化实现）。
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from dsl_schema import ConstraintBoolean, DslModel
from geometry_generator import Element, ElementId, Node, NodeId


def _build_node_index(nodes: Sequence[Node]) -> Dict[NodeId, Node]:
    return {n.id for n in nodes}  # type: ignore[return-value]


def _merge_nodes_by_tolerance(
    nodes: Sequence[Node],
    merge_tol: float,
) -> Tuple[List[Node], Dict[NodeId, NodeId]]:
    """
    按坐标容差合并节点，返回：
    - 新节点列表
    - old_id -> new_id 映射
    """
    reps: List[Node] = []
    mapping: Dict[NodeId, NodeId] = {}

    def is_close(n1: Node, n2: Node) -> bool:
        dx = n1.x - n2.x
        dy = n1.y - n2.y
        dz = n1.z - n2.z
        return dx * dx + dy * dy + dz * dz <= merge_tol * merge_tol

    next_id = 1
    for n in nodes:
        found_rep_id: NodeId | None = None
        for rep in reps:
            if is_close(n, rep):
                found_rep_id = rep.id
                break
        if found_rep_id is None:
            # 新代表点
            new_node = Node(
                id=next_id,
                x=n.x,
                y=n.y,
                z=n.z,
                entity_id=n.entity_id,
            )
            reps.append(new_node)
            mapping[n.id] = next_id
            next_id += 1
        else:
            mapping[n.id] = found_rep_id

    return reps, mapping


def _apply_union(
    nodes: List[Node],
    elements: List[Element],
    merge_tol: float,
) -> Tuple[List[Node], List[Element]]:
    new_nodes, mapping = _merge_nodes_by_tolerance(nodes, merge_tol)

    new_elements: List[Element] = []
    seen_edges: set[Tuple[NodeId, NodeId, str]] = set()
    eid = 1
    for e in elements:
        i = mapping[e.i]
        j = mapping[e.j]
        if i == j:
            continue
        key = (min(i, j), max(i, j), e.type)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        new_elements.append(
            Element(
                id=eid,
                i=i,
                j=j,
                entity_id=e.entity_id,
                type=e.type,
            )
        )
        eid += 1

    return new_nodes, new_elements


def _apply_difference(
    base_entities: List[str],
    subtract_entities: List[str],
    nodes: List[Node],
    elements: List[Element],
    merge_tol: float,
) -> Tuple[List[Node], List[Element]]:
    """
    简化 difference：删除 base 实体中与 subtract 实体近似重合的节点及相关单元。
    """
    base_nodes = [n for n in nodes if n.entity_id in base_entities]
    other_nodes = [n for n in nodes if n.entity_id in subtract_entities]

    if not base_nodes or not other_nodes:
        return nodes, elements

    # 标记 base 中需要删除的节点
    to_delete: set[NodeId] = set()
    for nb in base_nodes:
        for no in other_nodes:
            dx = nb.x - no.x
            dy = nb.y - no.y
            dz = nb.z - no.z
            if dx * dx + dy * dy + dz * dz <= merge_tol * merge_tol:
                to_delete.add(nb.id)
                break

    new_nodes = [n for n in nodes if n.id not in to_delete]
    new_elements = [e for e in elements if e.i not in to_delete and e.j not in to_delete]
    return new_nodes, new_elements


def _apply_intersection(
    entities: List[str],
    nodes: List[Node],
    elements: List[Element],
    merge_tol: float,
) -> Tuple[List[Node], List[Element]]:
    """
    简化 intersection：仅保留所有目标实体间“共同节点”及相关单元。
    """
    if len(entities) < 2:
        return nodes, elements

    groups: Dict[str, List[Node]] = {eid: [] for eid in entities}
    for n in nodes:
        if n.entity_id in groups:
            groups[n.entity_id].append(n)

    # 找到出现在所有实体中的“公共点”
    common_ids: set[NodeId] = set()
    for n0 in groups[entities[0]]:
        in_all = True
        for e_id in entities[1:]:
            found = False
            for n2 in groups[e_id]:
                dx = n0.x - n2.x
                dy = n0.y - n2.y
                dz = n0.z - n2.z
                if dx * dx + dy * dy + dz * dz <= merge_tol * merge_tol:
                    found = True
                    break
            if not found:
                in_all = False
                break
        if in_all:
            common_ids.add(n0.id)

    new_nodes = [n for n in nodes if n.id in common_ids]
    new_elements = [e for e in elements if e.i in common_ids and e.j in common_ids]
    return new_nodes, new_elements


def apply_boolean_ops(
    dsl: DslModel,
    nodes: List[Node],
    elements: List[Element],
    merge_tol: float = 1e-3,
) -> Tuple[List[Node], List[Element]]:
    """
    按 DSL 中的 boolean 约束顺序执行 union / intersection / difference。
    """
    cur_nodes = list(nodes)
    cur_elements = list(elements)

    for c in dsl.constraints:
        if not isinstance(c, ConstraintBoolean):
            continue
        targets = c.targets
        if c.operation == "union":
            cur_nodes, cur_elements = _apply_union(cur_nodes, cur_elements, merge_tol)
        elif c.operation == "intersection":
            cur_nodes, cur_elements = _apply_intersection(targets, cur_nodes, cur_elements, merge_tol)
        elif c.operation == "difference":
            if len(targets) >= 2:
                base = [targets[0]]
                subtract = targets[1:]
                cur_nodes, cur_elements = _apply_difference(base, subtract, cur_nodes, cur_elements, merge_tol)

    return cur_nodes, cur_elements


__all__ = ["apply_boolean_ops"]

