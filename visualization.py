"""
三维可视化模块：基于 matplotlib 3D 绘制结构与夹子、可选变形图。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from clip_generator import EqualDofClip, ZeroLengthClip
from geometry_generator import Element, Node


def plot_structure(
    nodes: List[Node],
    elements: List[Element],
    equal_clips: List[EqualDofClip],
    zl_clips: List[ZeroLengthClip],
    title: str = "Structure",
) -> None:
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    node_map = {n.id: n for n in nodes}

    # 梁柱单元
    for e in elements:
        n1 = node_map[e.i]
        n2 = node_map[e.j]
        xs = [n1.x, n2.x]
        ys = [n1.y, n2.y]
        zs = [n1.z, n2.z]
        color = "b" if e.type == "beam" else "g"
        ax.plot(xs, ys, zs, color=color, linewidth=1.0, alpha=0.8)

    # 刚性夹子：红色
    for c in equal_clips:
        n1 = node_map[c.master]
        n2 = node_map[c.slave]
        xs = [n1.x, n2.x]
        ys = [n1.y, n2.y]
        zs = [n1.z, n2.z]
        ax.plot(xs, ys, zs, color="r", linewidth=2.0, linestyle="-", alpha=0.9)

    # 弹性夹子：橙色虚线
    for c in zl_clips:
        n1 = node_map[c.i]
        n2 = node_map[c.j]
        xs = [n1.x, n2.x]
        ys = [n1.y, n2.y]
        zs = [n1.z, n2.z]
        ax.plot(xs, ys, zs, color="orange", linewidth=2.0, linestyle="--", alpha=0.9)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()


def plot_deformed(
    nodes: List[Node],
    elements: List[Element],
    displacements: Dict[int, Tuple[float, float, float]],
    scale_factor: float = 1.0,
    title: str = "Deformed Shape",
) -> None:
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    node_map = {n.id: n for n in nodes}

    # 原始结构（淡灰色）
    for e in elements:
        n1 = node_map[e.i]
        n2 = node_map[e.j]
        xs = [n1.x, n2.x]
        ys = [n1.y, n2.y]
        zs = [n1.z, n2.z]
        ax.plot(xs, ys, zs, color="lightgray", linewidth=1.0, alpha=0.6)

    # 变形后结构（蓝色）
    for e in elements:
        n1 = node_map[e.i]
        n2 = node_map[e.j]
        ux1, uy1, uz1 = displacements.get(n1.id, (0.0, 0.0, 0.0))
        ux2, uy2, uz2 = displacements.get(n2.id, (0.0, 0.0, 0.0))
        xs = [n1.x + ux1 * scale_factor, n2.x + ux2 * scale_factor]
        ys = [n1.y + uy1 * scale_factor, n2.y + uy2 * scale_factor]
        zs = [n1.z + uz1 * scale_factor, n2.z + uz2 * scale_factor]
        ax.plot(xs, ys, zs, color="b", linewidth=1.5, alpha=0.9)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()


__all__ = ["plot_structure", "plot_deformed"]

