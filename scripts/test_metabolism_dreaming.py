#!/usr/bin/env python3
"""
Metabolism + Dreaming 集成测试
"""
import sys
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db_wrapper import MemoryDBWrapper
from memory_metabolism import MemoryMetabolism, DreamStateReader, DreamScoreCalculator, DreamSignals


def test_dream_signals_disabled():
    """测试 dreaming 未启用时系统正常工作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # 复制 schema.sql 到 temp 目录
        import shutil
        shutil.copy(Path(__file__).parent.parent / 'schema.sql', tmpdir / 'schema.sql')
        db_path = tmpdir / 'test.db'
        db = MemoryDBWrapper(str(db_path))
        # 不传 dreams_dir
        metabolism = MemoryMetabolism(db)
        assert metabolism.dream_reader is None
        assert metabolism.dream_signals is None
        result = metabolism.run_full_metabolism_cycle()
        assert result['status'] == 'success'
        assert result['dream_enabled'] is False
        print("PASS: test_dream_signals_disabled")


def test_dream_state_reader_no_directory():
    """测试 .dreams/ 目录不存在时返回 disabled 信号"""
    reader = DreamStateReader(Path('/nonexistent/.dreams'))
    signals = reader.read_latest_dream()
    assert signals.enabled is False
    assert signals.phase == 'none'
    print("PASS: test_dream_state_reader_no_directory")


def test_dream_score_calculator_disabled():
    """测试 signals.disabled 时 boost 为 0"""
    calc = DreamScoreCalculator()
    memory = {'id': 1, 'access_count': 5, 'score': 3.0}
    signals = DreamSignals(enabled=False)
    boost = calc.calculate_dream_boost(memory, signals)
    assert boost == 0.0
    print("PASS: test_dream_score_calculator_disabled")


def test_dream_score_calculator_enabled():
    """测试 signals.enabled 时 boost 大于 0"""
    calc = DreamScoreCalculator()
    memory = {'id': 1, 'access_count': 5, 'score': 3.0, 'updated_at': datetime.now().isoformat()}
    signals = DreamSignals(enabled=True, phase='deep', promotion_candidates=[1, 2], avg_dream_score=0.8)
    boost = calc.calculate_dream_boost(memory, signals)
    assert boost > 0.0
    print(f"PASS: test_dream_score_calculator_enabled (boost={boost:.3f})")


def test_metabolism_with_fake_dreams():
    """测试有 .dreams/ 时的 metabolism"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # 复制 schema.sql 到 temp 目录
        import shutil
        shutil.copy(Path(__file__).parent.parent / 'schema.sql', tmpdir / 'schema.sql')
        # 创建 fake .dreams 结构
        dreams_dir = tmpdir / '.dreams' / '2026-04-06'
        dreams_dir.mkdir(parents=True)
        deep_file = dreams_dir / 'deep.json'
        deep_file.write_text(json.dumps({
            'phase': 'deep',
            'timestamp': datetime.now().isoformat(),
            'candidates': [1, 2],
            'avg_score': 0.82,
            'patterns': ['用户偏好冷咖啡', 'Obsidian 索引已自动化']
        }))

        db_path = tmpdir / 'test.db'
        db = MemoryDBWrapper(str(db_path))
        metabolism = MemoryMetabolism(db, dreams_dir=dreams_dir)

        # 手动写入一条 STM 记忆
        db.execute("""
            INSERT INTO user_memory (l0_summary, l1_overview, memory_type, score, tier, access_count)
            VALUES ('测试记忆', '这是一个测试', 'fact', 5.0, 'STM', 3)
        """)
        db.commit()

        result = metabolism.run_full_metabolism_cycle()
        assert result['status'] == 'success'
        print(f"PASS: test_metabolism_with_fake_dreams (result={result})")


if __name__ == '__main__':
    test_dream_signals_disabled()
    test_dream_state_reader_no_directory()
    test_dream_score_calculator_disabled()
    test_dream_score_calculator_enabled()
    test_metabolism_with_fake_dreams()
    print("\nAll tests passed!")
