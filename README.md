## 项目说明：LLM 驱动的三维结构约束建模示例

本工程演示如何使用通义千问生成“约束 DSL”，再由本地约束求解器自动完成：

- 三维框架几何生成（节点/单元）
- 结构间夹子（equalDOF / zeroLength）自动生成（KD-Tree）
- 三维布尔运算（union / intersection / difference）
- OpenSees 模型构建与静力分析
- matplotlib 3D 可视化原始结构与变形结果

### 1. 安装依赖

在项目根目录（`D:/python_project/os2zwind`）下执行：

```bash
pip install -r requirements.txt
```

### 2. 配置通义千问 API Key

本工程通过环境变量 `QWEN_API_KEY` 使用通义千问，不在代码中硬编码密钥。

在 PowerShell 中：

```powershell
$env:QWEN_API_KEY="你的通义千问密钥，例如 sk-affb2f4..."
```

不设置该变量时，程序会自动回退到本地内置的示例 DSL。

### 3. 一句话建模方式

打开 `main.py`，找到：

```python
user_requirements = (
    "生成两个并排三层钢框架结构，自动用刚性/弹性夹子连接，并对两者做并集布尔运算，固定 A 的底层。"
)
```

你只需要修改这**一句中文描述**，用自然语言写下你的建模需求，程序会自动：

1. 将这句话包装成完整的 Prompt（包括 DSL 结构和约束说明）；
2. 调用通义千问生成约束 DSL(JSON)；
3. 解析 DSL，生成几何、夹子、布尔运算结果；
4. 通过 Validator 检查拓扑；
5. 使用 `zwind` 调用 OpenSees 完成静力分析；
6. 用 matplotlib 3D 显示结构与变形图。

运行方式：

```bash
python main.py
```

### 4. 如何判断是否真正使用了大模型

`llm_client.call_qwen` 在关键路径打印了简单日志：

- 当缺少 API Key 时：

```text
[LLM] Fallback to local DSL: no QWEN_API_KEY in environment.
```

- 当 HTTP 调用失败时：

```text
[LLM] Request failed, using local DSL. Error: ...
```

- 当成功从通义千问获得并解析出 JSON DSL 时：

```text
[LLM] Got response from Qwen.
[LLM] Parsed JSON DSL from Qwen output.
```

- 当解析失败而回退到本地 DSL 时：

```text
[LLM] JSON parse failed, using local sample DSL. Error: ...
```

**只有在终端看到 `Got response from Qwen` 且 `Parsed JSON DSL from Qwen output` 时，才表示本次真正使用了大模型生成 DSL。**

要验证“一句话建模”的效果，可以：

1. 先运行一次，保留当前 `user_requirements`，观察打印的 DSL 或结构统计信息；
2. 稍微修改 `user_requirements`（例如改变 B 框架的偏移、层数或布尔运算类型），再次运行；
3. 比较两次运行的节点数、单元数或可视化结果是否明显不同。

---

### 5. 工程整体架构与模块说明

工程主要 Python 模块：

- `dsl_schema.py`：约束 DSL 定义与解析  
  - 定义 `EntityFrame`（frame 结构实体）、`ConstraintConnectNearest`、`ConstraintBoolean`、`ConstraintSupportBase` 等数据类。  
  - `parse_dsl(raw: dict) -> DslModel`：从通义千问返回的 JSON 转成内部对象，并填充默认值（跨数、跨距等）。

- `sample_prompt.py`：内置示例 Prompt 与 DSL  
  - `get_sample_prompt()`：用于没有自定义需求时的默认 Prompt。  
  - `get_sample_dsl()`：网络/解析失败时的兜底 DSL，保证工程可运行。

- `llm_client.py`：通义千问调用封装  
  - 使用 `QWEN_API_KEY` 调用 `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`。  
  - 通过 `_extract_json_from_content` 兼容多种输出格式（纯 JSON / ```json 代码块 / 前后有说明文字）。  
  - 失败时打印 `[LLM] ...` 日志并回退到 `get_sample_dsl()`。

- `geometry_generator.py`：从 DSL `entities` 生成几何  
  - 输入：`DslModel`。  
  - 输出：  
    - `nodes: List[Node]`，字段：`id, x, y, z, entity_id`。  
    - `elements: List[Element]`，字段：`id, i, j, entity_id, type`（`beam` / `column`）。  
    - `entity_node_map`、`entity_element_map`。  
  - 生成规则：  
    - `frame`：按 `stories`（层数）、`height`（层高）、`num_bays_x/num_bays_y`（跨数）、`bay_width_x/bay_width_y`（跨距）在 X-Y 平面生成规则网格，并沿 Z 方向层层堆叠。  
    - 自动生成柱单元（层间竖向）与梁单元（各层内 X/Y 向）。

- `clip_generator.py`：夹子（连接约束）生成  
  - 从 `DslModel` 中提取所有 `connect_nearest` 约束。  
  - 使用 `scipy.spatial.cKDTree` 为目标实体节点构建 KD-Tree，对源实体节点做最近邻搜索。  
  - 同层约束：要求 `|z1 - z2| < z_tolerance`。  
  - 距离阈值 `tolerance` 控制是否生成夹子。  
  - 输出：  
    - `EqualDofClip`（刚性夹子，对应 OpenSees `equalDOF`）。  
    - `ZeroLengthClip`（弹性夹子，对应 OpenSees `zeroLength`，内部含简化轴向刚度 `axial_k`）。  
  - `mode="auto"` 时：根据实际距离自动在刚性/弹性夹子间切换。

- `boolean_ops.py`：三维布尔运算（结构级）  
  - 基于节点坐标、容差 `merge_tol` 定义“等价节点”。  
  - `union`：合并节点坐标并去重，重定向单元端点到合并后的代表节点。  
  - `intersection`：找出在多个实体中都存在的“重叠节点”，仅保留这些节点以及在这些节点间的单元。  
  - `difference`：从基准实体中删除与其他实体“重合”的节点及其相关单元。  
  - 对外接口：`apply_boolean_ops(dsl, nodes, elements, merge_tol=1e-3) -> (nodes, elements)`。

- `validator.py`：拓扑检查  
  - 使用 `networkx` 构建无向图：节点为结构节点 ID，边为单元、刚性夹子、弹性夹子。  
  - 检查：  
    - 节点存在性（任何单元/夹子引用的节点必须在全局节点列表中）。  
    - 连通分量数量。  
    - 孤立节点（度数为 0）。  
    - 重复连接（相同 `(i,j)` 的多条边）。  
  - 返回摘要字典，并在终端打印统计信息。

- `opensees_builder.py`：OpenSees 建模与静力分析（通过 `zwind`）  
  - 使用仓库自带的 `zwind` 包，导入方式为 `import zwind as ops`，避免直接依赖系统级 `openseespy` DLL。  
  - 建模流程：  
    - `ops.wipe()`，`ops.model("basic", "-ndm", 3, "-ndf", 6)`。  
    - `ops.node(...)` 创建所有节点。  
    - 定义统一弹性材料和截面参数，使用 `elasticBeamColumn` 生成梁柱单元。  
    - 几何变换：  
      - 定义两个 `geomTransf Linear`：  
        - 水平构件：`transf_xy`，参考向量 v = (0,0,1)。  
        - 竖向构件：`transf_z`，参考向量 v = (0,1,0)。  
      - 根据单元端点坐标方向自动选择合适的 transf，避免 `v` 与局部 x 轴平行的数值问题。  
    - `support_base` 约束 → 对底层节点施加 `fix` 全约束。  
    - 刚性夹子 → `ops.equalDOF(master, slave, ...)`。  
    - 弹性夹子 → 为每个 zeroLength 创建 `uniaxialMaterial Elastic`，再用 `ops.element("zeroLength", ...)` 连接节点。  
    - 施加竖向荷载：顶层节点统一向下集中力。  
    - 静力分析：`constraints/numberer/system/test/algorithm/integrator/analysis/analyze`。  
    - 从 `ops.nodeDisp` 读取每个节点的位移，返回位移字典及最大竖向位移。

- `visualization.py`：三维可视化  
  - 使用 `matplotlib` 的 3D 坐标轴：  
    - 原始结构：梁柱单元以线框显示，柱/梁颜色区分。  
    - 夹子：刚性（红色实线）、弹性（橙色虚线）。  
    - 变形图：灰色为未变形，蓝色为放大后的变形结构（`scale_factor` 可调）。

- `main.py`：主流程与“一句话建模”  
  - 关键变量：  
    - `user_requirements`：用户的一句中文建模需求。  
    - 文件顶部通过 `os.environ.setdefault("QWEN_API_KEY", "...")` 自动设置通义千问密钥，确保在各种运行方式下都调用大模型。  
  - 流程：  
    1. 将 `user_requirements` 包装为详细 Prompt（包含 DSL 结构约束与禁止事项）。  
    2. 调用 `call_qwen(prompt)` 得到 DSL JSON。  
    3. `parse_dsl` → `generate_geometry` → `apply_boolean_ops` → `generate_clips`。  
    4. `validate_topology` 检查拓扑。  
    5. `build_and_run_opensees` 进行静力分析并返回位移。  
    6. `plot_structure` 与 `plot_deformed` 进行三维可视化。

---

### 6. 关键技术点回顾

- **LLM 限制与职责边界**：  
  - LLM 只负责生成 DSL（entities + constraints），不直接生成节点、单元或 OpenSees 代码。  
  - 所有几何、连接、拓扑与分析逻辑都在本地 Python 模块中完成，符合 CAD“约束驱动几何”的思想。

- **约束驱动几何生成**：  
  - 实体只给出“层数 + 层高 + 跨数 + 跨距 + 原点”等宏观参数。  
  - 几何生成器根据这些参数自动搭建网格，统一编号节点与单元。

- **KD-Tree 空间连接（夹子）**：  
  - 通过 KD-Tree 进行最近邻搜索，实现不同结构之间的“自动找最近节点并连成夹子”。  
  - 同层约束与距离阈值保证连接合理，`mode="auto"` 实现刚性/弹性自动判别。

- **布尔运算与拓扑安全**：  
  - 基于节点坐标的“等价”判定，实现 union/intersection/difference 的几何级操作。  
  - Validator 在每次建模后检查拓扑合理性，防止孤立/重复连接。

- **OpenSees 集成（通过 zwind）**：  
  - 通过 `zwind` 封装 OpenSees 调用，使工程在 Windows 环境下更易部署。  
  - 统一材料、截面与几何变换设置，保证示例清晰、可复现。

通过以上设计，整个工程实现了：**一句自然语言 → LLM 生成 DSL → 约束求解 → 结构建模 → OpenSees 分析 → 3D 可视化** 的完整闭环。
