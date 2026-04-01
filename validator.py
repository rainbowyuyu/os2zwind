"""
拓扑 Validator：检查节点存在性、连通性、孤立节点与重复连接。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import networkx as nx

from clip_generator import EqualDofClip, ZeroLengthClip
from geometry_generator import Element, Node


def validate_topology(
    nodes: List[Node],
    elements: List[Element],
    equal_clips: List[EqualDofClip],
    zl_clips: List[ZeroLengthClip],
) -> Dict[str, object]:
    node_ids = {n.id for n in nodes}

    # 节点存在性
    missing_nodes: List[int] = []
    for e in elements:
        if e.i not in node_ids or e.j not in node_ids:
            missing_nodes.extend([nid for nid in (e.i, e.j) if nid not in node_ids])
    for c in equal_clips:
        if c.master not in node_ids or c.slave not in node_ids:
            missing_nodes.extend([nid for nid in (c.master, c.slave) if nid not in node_ids])
    for c in zl_clips:
        if c.i not in node_ids or c.j not in node_ids:
            missing_nodes.extend([nid for nid in (c.i, c.j) if nid not in node_ids])
    missing_nodes = sorted(set(missing_nodes))

    # 图连通性（单元 + 夹子）
    G = nx.Graph()
    G.add_nodes_from(node_ids)
    for e in elements:
        G.add_edge(e.i, e.j, kind="element")
    for c in equal_clips:
        G.add_edge(c.master, c.slave, kind="equalDOF")
    for c in zl_clips:
        G.add_edge(c.i, c.j, kind="zeroLength")

    components = list(nx.connected_components(G))
    num_components = len(components)
    isolated_nodes = [nid for nid in node_ids if G.degree[nid] == 0]

    # 重复连接：相同 (i,j) 的多条边
    edge_counts: Dict[Tuple[int, int], int] = {}
    for u, v in G.edges():
        key = (min(u, v), max(u, v))
        edge_counts[key] = edge_counts.get(key, 0) + 1
    duplicate_edges = [pair for pair, cnt in edge_counts.items() if cnt > 1]

    summary = {
        "num_nodes": len(node_ids),
        "num_elements": len(elements),
        "num_equal_clips": len(equal_clips),
        "num_zero_length_clips": len(zl_clips),
        "num_components": num_components,
        "num_isolated_nodes": len(isolated_nodes),
        "missing_nodes": missing_nodes,
        "isolated_nodes": isolated_nodes,
        "duplicate_edges": duplicate_edges,
    }

    # 打印简要拓扑信息
    print("=== Topology Validation Summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

    return summary


__all__ = ["validate_topology"]

