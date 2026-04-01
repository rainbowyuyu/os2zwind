"""
主流程：
1. 调用通义千问获取约束 DSL（或回退到本地示例）；
2. 解析 DSL；
3. 生成几何（节点与单元）；
4. 执行布尔运算；
5. 自动生成夹子（刚性/弹性/自动）；
6. 拓扑验证；
7. OpenSeesPy 建模与静力分析；
8. 三维可视化原始结构与变形结果。
"""

from __future__ import annotations

import os

from llm_client import call_qwen
from boolean_ops import apply_boolean_ops
from clip_generator import generate_clips
from dsl_schema import parse_dsl
from geometry_generator import generate_geometry
from opensees_builder import build_and_run_opensees
from sample_prompt import get_sample_prompt
from validator import validate_topology
from visualization import plot_deformed, plot_structure


# 若外部未设置 QWEN_API_KEY，则在此使用你提供的密钥，
# 确保通过 @main.py 或直接运行 main.py 时都会调用大模型。
os.environ.setdefault("QWEN_API_KEY", "sk-affb2f48526b4aa38cadfd3004646fcc")


def main(user_requirements) -> None:

    # 自动扩展为完整的大模型提示词
    prompt = (
        "你是一名结构工程与 CAD 约束建模专家，只能根据用户描述生成约束 DSL 的 JSON。\n"
        "禁止输出任何 OpenSees / OpenSeesPy / Python 代码，也禁止直接给出有限元节点或单元编号。\n"
        "下面是用户的建模需求（可能只有一句话，请你自行合理补全结构参数）：\n"
        "—— 建模需求开始 ——\n"
        f"{user_requirements}\n"
        "—— 建模需求结束 ——\n"
        "请只输出一个 JSON 对象，严格符合以下 DSL 规范：\n"
        "1. 顶层结构为：{\n"
        '     "entities": [...],\n'
        '     "constraints": [...]\n'
        "   }\n"
        "2. entities：列表，每个实体表示一个三维框架结构，至少包含两个实体（如 A、B），示例：\n"
        '   {\"id\": \"A\", \"type\": \"frame\", \"stories\": 3, \"height\": 3, \"origin\": [0,0,0]}\n'
        "   你可以根据需求合理增加：num_bays_x, num_bays_y, bay_width_x, bay_width_y 等参数。\n"
        "3. constraints：列表，至少包含以下三类约束中的各一条：\n"
        "   - 自动夹子约束 connect_nearest，例如：\n"
        '     {\"type\": \"connect_nearest\", \"between\": [\"A\",\"B\"], \"mode\": \"auto\", \"tolerance\": 0.3}\n'
        "   - 布尔运算约束 boolean，例如：\n"
        '     {\"type\": \"boolean\", \"operation\": \"union\", \"targets\": [\"A\",\"B\"]}\n'
        "   - 底部支座约束 support_base，例如：\n"
        '     {\"type\": \"support_base\", \"target\": \"A\"}\n'
        "4. 只能输出 JSON，不要输出任何解释性文字或代码片段。\n"
    )

    # 1. 调用 LLM 获取 DSL（自动回退到本地示例）
    raw_dsl = call_qwen(prompt)

    # 2. 解析 DSL
    dsl = parse_dsl(raw_dsl)

    # 3. 生成几何
    nodes, elements, entity_node_map, entity_element_map = generate_geometry(dsl)
    print(f"Generated {len(nodes)} nodes and {len(elements)} elements from entities.")

    # 4. 布尔运算
    nodes_bool, elements_bool = apply_boolean_ops(dsl, nodes, elements, merge_tol=1e-3)
    print(f"After boolean ops: {len(nodes_bool)} nodes, {len(elements_bool)} elements.")

    # 5. 夹子生成
    equal_clips, zl_clips = generate_clips(dsl, nodes_bool)
    print(f"Generated {len(equal_clips)} rigid clips and {len(zl_clips)} elastic clips.")

    # 6. 拓扑验证
    topo_info = validate_topology(nodes_bool, elements_bool, equal_clips, zl_clips)

    # 7. OpenSeesPy 分析
    analysis_result = build_and_run_opensees(dsl, nodes_bool, elements_bool, equal_clips, zl_clips)

    # 8. 可视化
    try:
        plot_structure(nodes_bool, elements_bool, equal_clips, zl_clips, title="Structure with Clips")
        disps = analysis_result.get("displacements", {})
        if disps:
            plot_deformed(nodes_bool, elements_bool, disps, scale_factor=50.0, title="Deformed Shape (scaled)")
    except Exception as exc:
        print(f"Visualization failed: {exc}")


if __name__ == "__main__":
    # 1. 用户只需在这里写一句建模需求（自然语言）
    user_requirements = (
        "生成两个并排三层钢框架结构，自动用刚性/弹性夹子连接，并对两者做并集布尔运算，固定 A 的底层。"
        # "生成一个风机塔筒和叶片结构，自动用刚性/弹性夹子连接，并对两者做并集布尔运算"
    )
    main(user_requirements)

