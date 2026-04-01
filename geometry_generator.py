"""
结构几何生成器：从约束 DSL 的 entities 生成 3D 节点与单元。

注意：
- 所有节点与单元均由本模块根据约束生成，LLM 不直接给出节点/单元。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from dsl_schema import DslModel, EntityFrame


NodeId = int
ElementId = int


@dataclass
class Node:
    id: NodeId
    x: float
    y: float
    z: float
    entity_id: str


@dataclass
class Element:
    id: ElementId
    i: NodeId
    j: NodeId
    entity_id: str
    type: str  # "beam" | "column"


def _generate_frame_geometry(
    entity: EntityFrame,
    start_node_id: int,
    start_element_id: int,
) -> Tuple[List[Node], List[Element], int, int, List[NodeId]]:
    """
    为单个 frame 实体生成节点与单元。

    返回：
    - nodes, elements
    - 下一个可用 node_id, element_id
    - 该实体的节点 ID 列表
    """
    nodes: List[Node] = []
    elements: List[Element] = []

    stories = entity.stories
    h = entity.height  # 这里按“单层高度”理解

    nx = entity.num_bays_x
    ny = entity.num_bays_y
    bx = entity.bay_width_x
    by = entity.bay_width_y

    ox, oy, oz = entity.origin

    # 节点网格尺寸：沿 X 方向 nx+1，沿 Y 方向 ny+1，沿 Z 方向 stories+1
    node_id = start_node_id
    element_id = start_element_id

    # 记录各层各网格点的 node_id，便于后续生单元
    grid: Dict[Tuple[int, int, int], NodeId] = {}
    entity_node_ids: List[NodeId] = []

    for k in range(stories + 1):  # 层号 0..stories
        z = oz + k * h
        for ix in range(nx + 1):
            x = ox + ix * bx
            for iy in range(ny + 1):
                y = oy + iy * by
                nid = node_id
                node_id += 1
                nodes.append(Node(id=nid, x=x, y=y, z=z, entity_id=entity.id))
                grid[(ix, iy, k)] = nid
                entity_node_ids.append(nid)

    # 生成柱单元：同一网格点在相邻层之间连接
    for k in range(stories):
        for ix in range(nx + 1):
            for iy in range(ny + 1):
                n1 = grid[(ix, iy, k)]
                n2 = grid[(ix, iy, k + 1)]
                eid = element_id
                element_id += 1
                elements.append(
                    Element(
                        id=eid,
                        i=n1,
                        j=n2,
                        entity_id=entity.id,
                        type="column",
                    )
                )

    # 生成梁单元：每一层在 X/Y 方向连接相邻节点
    for k in range(stories + 1):
        # X 向梁
        for ix in range(nx):
            for iy in range(ny + 1):
                n1 = grid[(ix, iy, k)]
                n2 = grid[(ix + 1, iy, k)]
                eid = element_id
                element_id += 1
                elements.append(
                    Element(
                        id=eid,
                        i=n1,
                        j=n2,
                        entity_id=entity.id,
                        type="beam",
                    )
                )
        # Y 向梁
        for ix in range(nx + 1):
            for iy in range(ny):
                n1 = grid[(ix, iy, k)]
                n2 = grid[(ix, iy + 1, k)]
                eid = element_id
                element_id += 1
                elements.append(
                    Element(
                        id=eid,
                        i=n1,
                        j=n2,
                        entity_id=entity.id,
                        type="beam",
                    )
                )

    return nodes, elements, node_id, element_id, entity_node_ids


def generate_geometry(
    dsl: DslModel,
) -> Tuple[
    List[Node],
    List[Element],
    Dict[str, List[NodeId]],
    Dict[str, List[ElementId]],
]:
    """
    根据 DSL 中的 entities 生成全局节点和单元。

    返回：
    - nodes: 全部节点
    - elements: 全部单元
    - entity_node_map: entity_id -> 该实体的节点 ID 列表
    - entity_element_map: entity_id -> 该实体的单元 ID 列表
    """
    all_nodes: List[Node] = []
    all_elements: List[Element] = []
    entity_node_map: Dict[str, List[NodeId]] = {}
    entity_element_map: Dict[str, List[ElementId]] = {}

    next_node_id: int = 1
    next_element_id: int = 1

    for entity in dsl.entities:
        if not isinstance(entity, EntityFrame):
            continue
        nodes, elements, next_node_id, next_element_id, entity_node_ids = _generate_frame_geometry(
            entity, next_node_id, next_element_id
        )
        all_nodes.extend(nodes)
        all_elements.extend(elements)
        entity_node_map[entity.id] = entity_node_ids
        entity_element_map[entity.id] = [e.id for e in elements]

    return all_nodes, all_elements, entity_node_map, entity_element_map


__all__ = ["Node", "Element", "generate_geometry", "NodeId", "ElementId"]

