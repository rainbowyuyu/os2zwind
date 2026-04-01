"""
示例 Prompt 与本地示例 DSL。

当通义千问 API 不可用或解析失败时，系统会回退到本地 DSL，
确保整体约束建模与 OpenSeesPy 流程可以直接运行。
"""

from __future__ import annotations

from typing import Any, Dict


def get_sample_prompt() -> str:
    """返回用于请求通义千问的示例 Prompt。"""
    return (
        "你是一名结构工程与 CAD 约束建模专家。\n"
        "请根据以下要求，只输出一个 JSON 对象，严格符合给定 DSL 结构：\n"
        "1. 不要生成任何 OpenSees 或 OpenSeesPy 代码；\n"
        "2. 不要生成任何有限元节点或单元编号；\n"
        "3. 只允许生成约束 DSL，字段包括 entities 与 constraints；\n"
        "4. entities 中至少包含两个三维框架结构 A 和 B，类型为 frame；\n"
        "5. constraints 中必须包含：\n"
        "   - A 与 B 之间的 connect_nearest 约束，用于自动生成夹子（mode 可为 rigid/elastic/auto）；\n"
        "   - 对 A 和 B 的 boolean union 运算；\n"
        "   - 至少一个 support_base 约束（例如对 A 的支座约束）；\n"
        "6. 只输出 JSON，不要添加任何自然语言解释。\n"
        "7. 示例 DSL 结构为：\n"
        '{\n'
        '  \"entities\": [\n'
        '    {\"id\": \"A\", \"type\": \"frame\", \"stories\": 3, \"height\": 3, \"origin\": [0,0,0]},\n'
        '    {\"id\": \"B\", \"type\": \"frame\", \"stories\": 3, \"height\": 3, \"origin\": [5,0,0]}\n'
        '  ],\n'
        '  \"constraints\": [\n'
        '    {\"type\": \"connect_nearest\", \"between\": [\"A\",\"B\"], \"mode\": \"auto\", \"tolerance\": 0.3},\n'
        '    {\"type\": \"boolean\", \"operation\": \"union\", \"targets\": [\"A\",\"B\"]},\n'
        '    {\"type\": \"support_base\", \"target\": \"A\"}\n'
        '  ]\n'
        '}\n'
    )


def get_sample_dsl() -> Dict[str, Any]:
    """返回一个内置的示例 DSL，用于无网络或调试场景。"""
    return {
        "entities": [
            {
                "id": "A",
                "type": "frame",
                "stories": 3,
                "height": 3.0,
                "origin": [0.0, 0.0, 0.0],
                "num_bays_x": 2,
                "num_bays_y": 2,
                "bay_width_x": 5.0,
                "bay_width_y": 5.0,
            },
            {
                "id": "B",
                "type": "frame",
                "stories": 3,
                "height": 3.0,
                "origin": [5.0, 0.0, 0.0],
                "num_bays_x": 2,
                "num_bays_y": 2,
                "bay_width_x": 5.0,
                "bay_width_y": 5.0,
            },
        ],
        "constraints": [
            {
                "type": "connect_nearest",
                "between": ["A", "B"],
                "mode": "auto",
                "tolerance": 0.3,
                "z_tolerance": 1e-3,
            },
            {
                "type": "boolean",
                "operation": "union",
                "targets": ["A", "B"],
            },
            {
                "type": "support_base",
                "target": "A",
            },
        ],
    }


__all__ = ["get_sample_prompt", "get_sample_dsl"]

