#!/usr/bin/env python3
"""
LLM 批量评分模块
调用 SiliconFlow deepseek3.2 对 STM 记忆进行重要性评分
"""
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMBatchScorer:
    """基于 SiliconFlow deepseek3.2 的批量记忆评分器"""

    SCORING_PROMPT_TEMPLATE = """你是一个记忆评分专家。请评估以下每条记忆对 Agent 的重要性。

## Agent 角色背景
- Agent 是 OpenClaw 多代理框架的核心助手
- Agent 需要记住用户的偏好、重要事实、项目架构、技能学习
- Agent 需要遗忘临时的闲聊、噪音、无关紧要的信息

## 评分标准（0-10分）
- 10分：永久改变系统状态、核心架构决策、用户关键偏好
- 8-9分：技能学习、重要规则修改、项目架构
- 6-7分：重要事实、用户偏好、有价值的经验
- 4-5分：一般交互、常规任务记录
- 2-3分：临时信息、闲聊、可遗忘
- 0-1分：噪音、无意义

## 记忆列表（JSON数组）
{memories_json}

## 输出要求
请以 JSON 数组格式返回每条记忆的评分和简要理由：
[{{"id": <id>, "score": <分数>, "reasoning": "<简要理由>"}}, ...]

只返回 JSON，不要包含其他文字。"""

    def __init__(self, api_key: str, endpoint: str = "https://api.scikey.ai/v1"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = "deepseek-ai/DeepSeek-V3-0324"

    def score_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量评分记忆，返回评分结果列表。
        如果 api_key 为空或调用失败，返回空列表（不阻塞代谢流程）。
        """
        if not self.api_key or not memories:
            return []

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.endpoint)

            prompt = self._build_prompt(memories)

            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4096
            )

            raw = response.choices[0].message.content
            return self._parse_response(raw)

        except Exception as e:
            logger.warning(f"LLM 评分调用失败: {e}，继续使用规则评分")
            return []

    def _build_prompt(self, memories: List[Dict[str, Any]]) -> str:
        """构建评分 prompt"""
        # 简化记忆信息，减少 token 消耗
        simplified = [
            {
                "id": m["id"],
                "summary": m.get("l0_summary", ""),
                "overview": m.get("l1_overview", ""),
                "type": m.get("memory_type", "fact"),
                "access_count": m.get("access_count", 0),
                "created_at": m.get("created_at", "")
            }
            for m in memories
        ]
        memories_json = json.dumps(simplified, ensure_ascii=False, indent=2)
        return self.SCORING_PROMPT_TEMPLATE.format(memories_json=memories_json)

    def _parse_response(self, raw: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的 JSON 响应"""
        try:
            # 尝试提取 JSON 数组（处理可能的 markdown 代码块）
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]) if lines[0].startswith("```") else raw
            elif raw.startswith("```json"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1])

            data = json.loads(raw)
            if not isinstance(data, list):
                return []

            # 验证并清理每条记录
            result = []
            for item in data:
                if isinstance(item, dict) and "id" in item and "score" in item:
                    result.append({
                        "id": int(item["id"]),
                        "score": float(max(0, min(10, item["score"]))),  # clamp to 0-10
                        "reasoning": str(item.get("reasoning", ""))[:200]
                    })
            return result

        except Exception as e:
            logger.warning(f"解析 LLM 响应失败: {e}")
            return []