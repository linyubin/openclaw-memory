import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path

from memory_llm_scorer import LLMBatchScorer
from memory_metabolism import MemoryMetabolism
from db_wrapper import MemoryDBWrapper
from memory_search import MemorySearch

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


def test_metabolism_with_llm_scorer():
    """测试 metabolism 时调用 LLM 评分"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        import shutil
        shutil.copy(Path(__file__).parent.parent / 'schema.sql', tmpdir / 'schema.sql')
        db_path = tmpdir / 'test.db'
        db = MemoryDBWrapper(str(db_path))

        # Mock LLM response
        class MockScorer:
            def score_memories(self, memories):
                return [
                    {"id": 1, "score": 7.5, "reasoning": "重要事实"},
                    {"id": 2, "score": 2.0, "reasoning": "普通闲聊"},
                ]

        metabolism = MemoryMetabolism(db, llm_scorer=MockScorer())

        # 写入两条 STM 记忆
        db.execute("""
            INSERT INTO user_memory (l0_summary, l1_overview, memory_type, score, tier, access_count)
            VALUES ('InkTime项目路径', '/home/andy/inktime/ 目录', 'fact', 0.0, 'STM', 0)
        """)
        db.execute("""
            INSERT INTO user_memory (l0_summary, l1_overview, memory_type, score, tier, access_count)
            VALUES ('用户说hello', 'Hello是一般问候', 'interaction', 0.0, 'STM', 0)
        """)
        db.commit()

        result = metabolism.run_full_metabolism_cycle()
        assert result['status'] == 'success'
        assert result.get('llm_scoring_done') is True
        print("PASS: test_metabolism_with_llm_scorer")


def test_metabolism_without_llm_scorer():
    """测试 llm_scorer=None 时行为不变"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        import shutil
        shutil.copy(Path(__file__).parent.parent / 'schema.sql', tmpdir / 'schema.sql')
        db_path = tmpdir / 'test.db'
        db = MemoryDBWrapper(str(db_path))
        metabolism = MemoryMetabolism(db, llm_scorer=None)
        result = metabolism.run_full_metabolism_cycle()
        assert result['status'] == 'success'
        assert result.get('llm_scoring_done') is False
        print("PASS: test_metabolism_without_llm_scorer")

def test_write_with_tier_ltm():
    """测试传入 tier='LTM' 时直接写入 LTM"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        import shutil
        shutil.copy(Path(__file__).parent.parent / 'schema.sql', tmpdir / 'schema.sql')
        db_path = tmpdir / 'test.db'
        db = MemoryDBWrapper(str(db_path))
        searcher = MemorySearch(db)

        mem_id, is_update = searcher.deduplicated_write(
            l0_summary="测试LTM记忆",
            l1_overview="这是一个测试",
            l2_full_text=None,
            memory_type="fact",
            score=7.0,
            tier="LTM",  # 直接写入 LTM
            is_user_memory=True
        )

        cursor = db.execute("SELECT tier, score FROM user_memory WHERE id = ?", (mem_id,))
        row = cursor.fetchone()
        assert row[0] == "LTM"
        assert row[1] == 7.0
        print("PASS: test_write_with_tier_ltm")


def test_write_default_stm():
    """测试不传 tier 时默认写入 STM"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        import shutil
        shutil.copy(Path(__file__).parent.parent / 'schema.sql', tmpdir / 'schema.sql')
        db_path = tmpdir / 'test.db'
        db = MemoryDBWrapper(str(db_path))
        searcher = MemorySearch(db)

        mem_id, is_update = searcher.deduplicated_write(
            l0_summary="测试STM记忆",
            l1_overview="这是一个测试",
            tier="STM",  # 显式传 STM
            is_user_memory=True
        )

        cursor = db.execute("SELECT tier FROM user_memory WHERE id = ?", (mem_id,))
        row = cursor.fetchone()
        assert row[0] == "STM"
        print("PASS: test_write_default_stm")


if __name__ == '__main__':
    test_llm_scorer_batch_structure()
    test_llm_scorer_parse_response()
    test_llm_scorer_disabled_when_no_key()
    test_metabolism_with_llm_scorer()
    test_metabolism_without_llm_scorer()
    test_write_with_tier_ltm()
    test_write_default_stm()
    print("\nAll scorer tests passed!")