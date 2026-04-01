"""
约束 DSL 定义与解析模块

本模块只负责：
- 定义 DSL 的 Python 数据结构
- 提供从原始 JSON(dict) 到内部对象的解析与基本校验

注意：
- LLM 只被允许生成符合该 DSL 的 JSON，不允许生成节点、单元或 OpenSees 代码。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


Vec3 = Tuple[float, float, float]


@dataclass
class EntityFrame:
    """三维框架结构实体定义（由约束求解器生成几何，而非 LLM 直接给出节点/单元）。"""

    id: str
    type: Literal["frame"]
    stories: int
    height: float
    origin: Vec3

    # 可选扩展参数，若缺省则由解析器填默认值
    num_bays_x: int = 2
    num_bays_y: int = 2
    bay_width_x: float = 5.0
    bay_width_y: float = 5.0


@dataclass
class ConstraintConnectNearest:
    """自动夹子约束：基于 KD-Tree 寻找两结构间最近节点对。"""

    type: Literal["connect_nearest"]
    between: Tuple[str, str]
    mode: Literal["rigid", "elastic", "auto"] = "rigid"
    tolerance: float = 0.5
    z_tolerance: float = 1e-3


@dataclass
class ConstraintBoolean:
    """三维布尔运算：作用在结构级别。"""

    type: Literal["boolean"]
    operation: Literal["union", "intersection", "difference"]
    targets: List[str]


@dataclass
class ConstraintSupportBase:
    """支座约束：将指定实体底部节点固定。"""

    type: Literal["support_base"]
    target: str


Constraint = ConstraintConnectNearest | ConstraintBoolean | ConstraintSupportBase


@dataclass
class DslModel:
    """完整 DSL 模型：包含实体及约束列表。"""

    entities: List[EntityFrame] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)

    def get_entity_by_id(self, entity_id: str) -> Optional[EntityFrame]:
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None


def _parse_entity(raw: Dict[str, Any]) -> EntityFrame:
    """将原始 dict 解析为 EntityFrame，并填充默认值。"""
    if raw.get("type") != "frame":
        raise ValueError(f"Unsupported entity type: {raw.get('type')}")

    try:
        origin_raw = raw.get("origin", [0.0, 0.0, 0.0])
        if len(origin_raw) != 3:
            raise ValueError("origin must be a 3-element list")
        origin: Vec3 = (float(origin_raw[0]), float(origin_raw[1]), float(origin_raw[2]))

        return EntityFrame(
            id=str(raw["id"]),
            type="frame",
            stories=int(raw.get("stories", 3)),
            height=float(raw.get("height", 3.0)),
            origin=origin,
            num_bays_x=int(raw.get("num_bays_x", 2)),
            num_bays_y=int(raw.get("num_bays_y", 2)),
            bay_width_x=float(raw.get("bay_width_x", 5.0)),
            bay_width_y=float(raw.get("bay_width_y", 5.0)),
        )
    except KeyError as exc:
        raise ValueError(f"Missing required entity field: {exc}") from exc


def _parse_constraint(raw: Dict[str, Any]) -> Constraint:
    """将原始 dict 解析为具体的 Constraint 对象。"""
    ctype = raw.get("type")
    if ctype == "connect_nearest":
        between_raw = raw.get("between")
        if not isinstance(between_raw, (list, tuple)) or len(between_raw) != 2:
            raise ValueError("connect_nearest.between must be a 2-element list")
        return ConstraintConnectNearest(
            type="connect_nearest",
            between=(str(between_raw[0]), str(between_raw[1])),
            mode=raw.get("mode", "rigid"),
            tolerance=float(raw.get("tolerance", 0.5)),
            z_tolerance=float(raw.get("z_tolerance", 1e-3)),
        )
    if ctype == "boolean":
        op = raw.get("operation", "union")
        if op not in ("union", "intersection", "difference"):
            raise ValueError(f"Unsupported boolean operation: {op}")
        targets_raw = raw.get("targets") or []
        if not isinstance(targets_raw, (list, tuple)) or len(targets_raw) < 2:
            raise ValueError("boolean.targets must be a list with at least 2 entries")
        return ConstraintBoolean(
            type="boolean",
            operation=op,  # type: ignore[arg-type]
            targets=[str(t) for t in targets_raw],
        )
    if ctype == "support_base":
        target = raw.get("target")
        if not target:
            raise ValueError("support_base.target is required")
        return ConstraintSupportBase(type="support_base", target=str(target))

    raise ValueError(f"Unsupported constraint type: {ctype}")


def parse_dsl(raw: Dict[str, Any]) -> DslModel:
    """
    从原始 JSON(dict) 解析为 DslModel。

    该函数是 LLM 输出与约束求解器之间的唯一桥梁：
    - LLM 只能输出符合本 DSL 的 JSON
    - 几何节点、单元以及 OpenSees 建模均在本地完成
    """
    entities_raw = raw.get("entities") or []
    constraints_raw = raw.get("constraints") or []

    if not isinstance(entities_raw, list):
        raise ValueError("DSL.entities must be a list")
    if not isinstance(constraints_raw, list):
        raise ValueError("DSL.constraints must be a list")

    entities: List[EntityFrame] = []
    for e_raw in entities_raw:
        if not isinstance(e_raw, dict):
            raise ValueError("entity entry must be an object")
        entities.append(_parse_entity(e_raw))

    constraints: List[Constraint] = []
    for c_raw in constraints_raw:
        if not isinstance(c_raw, dict):
            raise ValueError("constraint entry must be an object")
        constraints.append(_parse_constraint(c_raw))

    return DslModel(entities=entities, constraints=constraints)


__all__ = [
    "Vec3",
    "EntityFrame",
    "ConstraintConnectNearest",
    "ConstraintBoolean",
    "ConstraintSupportBase",
    "Constraint",
    "DslModel",
    "parse_dsl",
]

