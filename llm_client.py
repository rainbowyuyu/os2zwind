"""
通义千问 LLM 调用封装。

本模块只返回约束 DSL(JSON)，不允许也不支持直接生成节点、单元或 OpenSees 代码。
若调用失败或解析失败，会自动回退到本地示例 DSL。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

import requests

from sample_prompt import get_sample_dsl, get_sample_prompt


QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def _build_headers() -> Dict[str, str]:
    api_key = os.getenv("QWEN_API_KEY")
    if not api_key:
        # 未配置环境变量则由上层回退到本地示例 DSL
        print("[LLM] Fallback to local DSL: no QWEN_API_KEY in environment.")
        raise RuntimeError("Environment variable QWEN_API_KEY is not set.")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def _extract_json_from_content(content: str) -> Dict[str, Any]:
    """
    从通义千问返回的 content 中尽可能鲁棒地提取一个 JSON 对象。
    兼容：
    - 纯 JSON
    - 被 ```json ... ``` 或 ``` 包裹的 JSON
    - 前后有解释性文字的情况
    """
    text = content.strip()

    # 去掉 markdown 代码块包裹
    if text.startswith("```"):
        # 去掉第一行 ``` 或 ```json
        lines = text.splitlines()
        if lines:
            if lines[0].startswith("```"):
                lines = lines[1:]
            # 去掉末尾 ``` 行
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 优先直接尝试整体解析
    try:
        return json.loads(text)
    except Exception:
        pass

    # 回退：截取第一个大括号块
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 再回退：用正则取第一个 {...} 块（非贪婪）
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        candidate = match.group(0)
        return json.loads(candidate)

    raise ValueError("No valid JSON object found in model output.")


def call_qwen(prompt: str | None = None) -> Dict[str, Any]:
    """
    调用通义千问，返回约束 DSL(JSON)。

    约束：
    - 严禁输出 OpenSees 或 OpenSeesPy 代码；
    - 严禁输出有限元节点或单元编号；
    - 只允许输出符合 DSL 规范的 JSON。
    """
    if prompt is None:
        prompt = get_sample_prompt()

    try:
        headers = _build_headers()
    except RuntimeError:
        # 无 API key，直接使用本地示例
        return get_sample_dsl()

    payload = {
        "model": "qwen-plus",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一名结构工程与 CAD 约束建模专家，只能根据用户描述生成约束 DSL 的 JSON。"
                    "禁止输出有限元节点、单元或 OpenSees 代码。"
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    }

    try:
        resp = requests.post(QWEN_API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print("[LLM] Got response from Qwen.")
    except Exception as e:
        # 网络或 API 错误，回退到本地示例
        print(f"[LLM] Request failed, using local DSL. Error: {e}")
        return get_sample_dsl()

    # 有些模型会在 JSON 外再包裹说明文字，这里尽可能鲁棒地提取 JSON 段
    try:
        dsl = _extract_json_from_content(content)
        print("[LLM] Parsed JSON DSL from Qwen output.")
        return dsl
    except Exception as e:
        # 解析失败，同样回退到本地示例
        print(f"[LLM] JSON parse failed, using local sample DSL. Error: {e}")
        return get_sample_dsl()


__all__ = ["call_qwen"]

