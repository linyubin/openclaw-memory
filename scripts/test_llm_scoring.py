import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from memory_llm_scorer import LLMBatchScorer

def test_llm_scorer_batch_structure():
    """测试批量评分返回正确的结构"""
    scorer = LLMBatchScorer(
        api_key="fake_key",
        endpoint="https://api.scikey.ai/v1"
    )
    memories = [
        {"id": 1, "l0_summary": "项目路径", "l1_overview": "InkTime项目在/home/andy/inktime/", "memory_type": "fact", "access_count": 0, "created_at": "2026-04-03T14:05:25"},
        {"id": 2, "l0_summary": "用户喜欢咖啡", "l1_overview": "用户喜欢冷咖啡", "memory_type": "preference", "access_count": 5, "created_at": "2026-04-01T10:00:00"},
    ]
    # 不调真实API，只验证结构
    prompt = scorer._build_prompt(memories)
    assert "记忆评分专家" in prompt
    assert "项目路径" in prompt
    assert "用户喜欢咖啡" in prompt
    print("PASS: test_llm_scorer_batch_structure")

def test_llm_scorer_parse_response():
    """测试解析 LLM JSON 响应"""
    scorer = LLMBatchScorer(api_key="fake", endpoint="fake")
    raw = '[{"id": 1, "score": 7.5, "reasoning": "重要事实"}, {"id": 2, "score": 3.0, "reasoning": "普通交互"}]'
    result = scorer._parse_response(raw)
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["score"] == 7.5
    print("PASS: test_llm_scorer_parse_response")

def test_llm_scorer_disabled_when_no_key():
    """测试 api_key 为空时返回空列表"""
    scorer = LLMBatchScorer(api_key="", endpoint="")
    result = scorer.score_memories([])
    assert result == []
    print("PASS: test_llm_scorer_disabled_when_no_key")

if __name__ == '__main__':
    test_llm_scorer_batch_structure()
    test_llm_scorer_parse_response()
    test_llm_scorer_disabled_when_no_key()
    print("\nAll scorer tests passed!")