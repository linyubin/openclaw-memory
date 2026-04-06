#!/usr/bin/env python3
"""
记忆新陈代谢模块
实现记忆的晋升、遗忘、定期清理机制
"""
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from db_wrapper import MemoryDBWrapper, MemoryDBException, MemoryOperations

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DreamSignals:
    """Dreaming 状态信号数据结构"""
    last_dream_time: Optional[datetime] = None
    phase: str = "none"  # 'light' | 'deep' | 'rem' | 'none'
    promotion_candidates: List[int] = field(default_factory=list)
    avg_dream_score: float = 0.0
    pattern_themes: List[str] = field(default_factory=list)
    enabled: bool = False

class MemoryMetabolism:
    """记忆新陈代谢管理器"""
    
    def __init__(self, db: MemoryDBWrapper, dreams_dir: Optional[Path] = None):
        self.db = db
        self.memory_ops = MemoryOperations(db)

        # 配置参数
        self.STM_RETENTION_DAYS = 7  # 短期记忆保留7天
        self.LTM_PROMOTION_THRESHOLD = 5  # 访问次数超过5次晋升为长期记忆
        self.CORE_SOUL_PROMOTION_THRESHOLD = 20  # 访问次数超过20次晋升为核心灵魂
        self.SCORE_THRESHOLD_FORGET = 3.0  # 评分低于3的记忆会被清理
        self.SCORE_THRESHOLD_LTM = 7.0  # 评分高于7的记忆直接进入长期记忆

        # Dreaming 配置
        self.DREAM_BOOST_THRESHOLD = 0.3
        self.DREAM_SCORE_BONUS = 2.0

        # Dreaming 组件（可选）
        if dreams_dir:
            self.dream_reader = DreamStateReader(dreams_dir)
            self.dream_calculator = DreamScoreCalculator()
            self.dream_signals: Optional[DreamSignals] = None
        else:
            self.dream_reader = None
            self.dream_calculator = None
            self.dream_signals = None
    
    def evaluate_memory_importance(self, memory: Dict[str, Any]) -> float:
        """
        评估记忆的重要性，返回0-10的评分
        评估维度：
        1. 是否永久改变系统状态
        2. 涉及的操作类型（规则修改 > 技能学习 > 事实记录 > 普通交互）
        3. 记忆类型权重
        """
        base_score = memory.get('score', 0.0)
        
        # 根据记忆类型调整权重
        type_weights = {
            # 用户记忆类型权重
            'preference': 8.0,
            'fact': 5.0,
            'interaction': 3.0,
            'task': 4.0,
            # 代理记忆类型权重
            'rule': 10.0,
            'skill': 8.0,
            'architecture': 9.0,
            'tool': 6.0,
            'state': 4.0
        }
        
        memory_type = memory.get('memory_type', 'fact')
        type_weight = type_weights.get(memory_type, 5.0)
        
        # 访问次数加成
        access_count = memory.get('access_count', 0)
        access_bonus = min(access_count * 0.5, 2.0)  # 最多加2分
        
        # 计算最终评分
        final_score = min((base_score * 0.5 + type_weight * 0.3 + access_bonus * 0.2), 10.0)
        return round(final_score, 2)
    
    def run_stm_cleanup(self) -> int:
        """清理过期的短期记忆（STM），返回清理的数量"""
        cutoff_date = datetime.now() - timedelta(days=self.STM_RETENTION_DAYS)
        cleaned_count = 0
        
        # 清理用户STM记忆
        cursor = self.db.execute("""
            DELETE FROM user_memory 
            WHERE tier = 'STM' 
              AND score < ? 
              AND created_at < ?
        """, (self.SCORE_THRESHOLD_FORGET, cutoff_date.isoformat()))
        cleaned_count += cursor.rowcount
        
        # 清理代理STM记忆
        cursor = self.db.execute("""
            DELETE FROM agent_memory 
            WHERE tier = 'STM' 
              AND score < ? 
              AND created_at < ?
        """, (self.SCORE_THRESHOLD_FORGET, cutoff_date.isoformat()))
        cleaned_count += cursor.rowcount
        
        self.db.commit()
        logger.info(f"清理了 {cleaned_count} 条过期短期记忆")
        return cleaned_count

    def run_promotion_cycle(self) -> Dict[str, int]:
        """运行记忆晋升周期，返回各层级晋升的数量"""
        promotion_stats = {
            'stm_to_ltm': 0,
            'ltm_to_core': 0,
            'dream_boosted': 0
        }

        # 读取 dreaming 信号（如果可用）
        signals = self._get_dream_signals()

        # 1. 短期记忆晋升为长期记忆
        for table in ['user_memory', 'agent_memory']:
            promotions = self._promote_stm_to_ltm(table, signals, promotion_stats)
            promotion_stats['stm_to_ltm'] += promotions

        # 2. 长期记忆晋升为核心灵魂
        for table in ['user_memory', 'agent_memory']:
            promotions = self._promote_ltm_to_core(table)
            promotion_stats['ltm_to_core'] += promotions

        self.db.commit()
        logger.info(f"记忆晋升完成：{promotion_stats['stm_to_ltm']} 条STM→LTM，{promotion_stats['ltm_to_core']} 条LTM→Core_Soul，{promotion_stats['dream_boosted']} 条通过dream boost晋升")
        return promotion_stats

    def _get_dream_signals(self) -> Optional[DreamSignals]:
        """获取 dream 信号，如果 dreaming 未启用返回 None"""
        if not self.dream_reader:
            return None
        if self.dream_signals is not None:
            return self.dream_signals
        try:
            self.dream_signals = self.dream_reader.read_latest_dream()
            if self.dream_signals.enabled:
                logger.info(f"检测到 dreaming 信号: phase={self.dream_signals.phase}, candidates={len(self.dream_signals.promotion_candidates)}")
            return self.dream_signals
        except Exception as e:
            logger.warning(f"读取 dreaming 信号失败: {e}")
            return None

    def _promote_stm_to_ltm(self, table: str, signals: Optional[DreamSignals], stats: Dict) -> int:
        """
        执行 STM → LTM 晋升逻辑。
        条件：评分 >= 7.0 或 访问次数 >= 5 或 dream boost 足够高。
        返回晋升数量。
        """
        count = 0
        cursor = self.db.execute(f"SELECT * FROM {table} WHERE tier = 'STM'")
        columns = [desc[0] for desc in cursor.description]
        stm_memories = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for memory in stm_memories:
            memory_id = memory['id']
            base_score = memory['score']
            access_count = memory['access_count']

            # 原有条件
            if base_score >= self.SCORE_THRESHOLD_LTM or access_count >= self.LTM_PROMOTION_THRESHOLD:
                self.db.execute(f"UPDATE {table} SET tier = 'LTM', updated_at = ? WHERE id = ?",
                              (datetime.now().isoformat(), memory_id))
                count += 1
                continue

            # Dream boost 条件
            if signals and signals.enabled and self.dream_calculator:
                boost = self.dream_calculator.calculate_dream_boost(memory, signals)
                if boost >= self.DREAM_BOOST_THRESHOLD:
                    effective_score = base_score + (boost * self.DREAM_SCORE_BONUS)
                    if effective_score >= self.SCORE_THRESHOLD_LTM:
                        self.db.execute(f"UPDATE {table} SET tier = 'LTM', updated_at = ?, score = ? WHERE id = ?",
                                      (datetime.now().isoformat(), effective_score, memory_id))
                        count += 1
                        stats['dream_boosted'] = stats.get('dream_boosted', 0) + 1

        return count

    def _promote_ltm_to_core(self, table: str) -> int:
        """执行 LTM → Core_Soul 晋升。条件不变：访问次数 >= 20 且 评分 >= 8"""
        cursor = self.db.execute(f"""
            UPDATE {table}
            SET tier = 'Core_Soul', updated_at = ?
            WHERE tier = 'LTM'
              AND access_count >= ?
              AND score >= 8.0
        """, (datetime.now().isoformat(), self.CORE_SOUL_PROMOTION_THRESHOLD))
        return cursor.rowcount

    def run_full_metabolism_cycle(self) -> Dict[str, Any]:
        """运行完整的新陈代谢周期"""
        logger.info("开始运行记忆新陈代谢周期")

        try:
            # 0. 预读取 dreaming 信号（如果可用）
            self._get_dream_signals()

            # 1. 重新评估所有记忆的评分
            self._reevaluate_all_memory_scores()

            # 2. 清理过期短期记忆
            stm_cleaned = self.run_stm_cleanup()

            # 3. 运行记忆晋升
            promotions = self.run_promotion_cycle()

            # 4. 更新系统元数据
            self._update_metadata()

            # 5. 生成 DREAMS.md 报告（如果 dreaming 可用）
            dreams_report_written = self._write_dreams_report()

            result = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'stm_cleaned': stm_cleaned,
                'promotions': promotions,
                'dream_enabled': self.dream_signals.enabled if self.dream_signals else False,
                'dreams_report_written': dreams_report_written
            }

            logger.info(f"记忆新陈代谢周期完成：{result}")
            return result

        except Exception as e:
            logger.error(f"记忆新陈代谢周期失败：{str(e)}")
            raise MemoryDBException(f"记忆新陈代谢失败：{str(e)}") from e
    
    def _reevaluate_all_memory_scores(self) -> None:
        """重新评估所有记忆的重要性评分"""
        # 处理用户记忆
        cursor = self.db.execute("SELECT * FROM user_memory")
        user_memories = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        for row in user_memories:
            memory = dict(zip(columns, row))
            new_score = self.evaluate_memory_importance(memory)
            if new_score != memory['score']:
                self.db.execute("""
                    UPDATE user_memory
                    SET score = ?, updated_at = ?
                    WHERE id = ?
                """, (new_score, datetime.now().isoformat(), memory['id']))
        
        # 处理代理记忆
        cursor = self.db.execute("SELECT * FROM agent_memory")
        agent_memories = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        for row in agent_memories:
            memory = dict(zip(columns, row))
            new_score = self.evaluate_memory_importance(memory)
            if new_score != memory['score']:
                self.db.execute("""
                    UPDATE agent_memory
                    SET score = ?, updated_at = ?
                    WHERE id = ?
                """, (new_score, datetime.now().isoformat(), memory['id']))
        
        self.db.commit()
        logger.info("所有记忆评分重新评估完成")
    
    def _update_metadata(self) -> None:
        """更新系统元数据"""
        # 计算总记忆数
        cursor = self.db.execute("SELECT COUNT(*) FROM user_memory")
        user_count = cursor.fetchone()[0]
        cursor = self.db.execute("SELECT COUNT(*) FROM agent_memory")
        agent_count = cursor.fetchone()[0]
        total_count = user_count + agent_count
        
        # 计算核心灵魂记忆数
        cursor = self.db.execute("SELECT COUNT(*) FROM user_memory WHERE tier = 'Core_Soul'")
        user_core = cursor.fetchone()[0]
        cursor = self.db.execute("SELECT COUNT(*) FROM agent_memory WHERE tier = 'Core_Soul'")
        agent_core = cursor.fetchone()[0]
        core_count = user_core + agent_core
        
        # 更新元数据
        self.db.execute("""
            UPDATE memory_system_metadata
            SET value = ?, updated_at = ?
            WHERE key = 'total_memory_count'
        """, (str(total_count), datetime.now().isoformat()))
        
        self.db.execute("""
            UPDATE memory_system_metadata
            SET value = ?, updated_at = ?
            WHERE key = 'core_soul_count'
        """, (str(core_count), datetime.now().isoformat()))
        
        self.db.execute("""
            UPDATE memory_system_metadata
            SET value = ?, updated_at = ?
            WHERE key = 'last_maintenance_run'
        """, (datetime.now().isoformat(), datetime.now().isoformat()))

        self.db.commit()

    def _write_dreams_report(self) -> bool:
        """
        生成 DREAMS.md 反思报告。
        如果 .dreams/ 不存在或写入失败，静默返回 False。
        """
        if not self.dream_signals or not self.dream_signals.enabled:
            return False

        signals = self.dream_signals
        today = datetime.now().strftime('%Y-%m-%d')

        # 构建报告块
        report_lines = [
            f"\n---\n",
            f"## Dream Report - {today}\n",
            f"\n",
            f"### Phase Status\n",
            f"- **Last Phase**: {signals.phase.capitalize()}\n",
            f"- **Dream Score**: {signals.avg_dream_score:.2f}\n",
            f"- **Candidates**: {len(signals.promotion_candidates)} memories\n",
        ]

        if signals.pattern_themes:
            report_lines.extend([
                f"\n### Pattern Themes (from REM)\n",
            ])
            for theme in signals.pattern_themes:
                report_lines.append(f"- {theme}\n")

        if signals.last_dream_time:
            next_dream = signals.last_dream_time + timedelta(days=1)
            report_lines.extend([
                f"\n### Next Dream\n",
                f"- Scheduled: {next_dream.strftime('%Y-%m-%d %H:%M')} CST\n",
            ])

        report_block = ''.join(report_lines)

        # 追加到 DREAMS.md
        dreams_md_path = self.dream_reader.dreams_dir.parent / 'DREAMS.md'
        try:
            with open(dreams_md_path, 'a', encoding='utf-8') as f:
                f.write(report_block)
            logger.info(f"DREAMS.md 报告已写入: {dreams_md_path}")
            return True
        except Exception as e:
            logger.warning(f"写入 DREAMS.md 失败: {e}")
            return False


class DreamStateReader:
    """读取 .dreams/ 目录中的 dreaming 状态文件"""

    def __init__(self, dreams_dir: Path | str):
        self.dreams_dir = Path(dreams_dir) if isinstance(dreams_dir, str) else dreams_dir

    def read_latest_dream(self) -> DreamSignals:
        """
        读取最新的 dream 状态。
        如果 .dreams/ 不存在或解析失败，返回 DreamSignals(enabled=False)
        """
        if not self.dreams_dir.exists():
            logger.debug(".dreams/ 目录不存在，跳过 dream boost")
            return DreamSignals()

        # 查找最新的日期子目录
        date_dirs = [d for d in self.dreams_dir.iterdir() if d.is_dir() and d.name.match(r'\d{4}-\d{2}-\d{2}')]
        if not date_dirs:
            logger.debug(".dreams/ 中无日期目录，跳过 dream boost")
            return DreamSignals()

        latest_dir = max(date_dirs, key=lambda d: d.name)

        # 按优先级读取 phase 文件
        for phase_name in ['deep', 'light', 'rem']:
            phase_file = latest_dir / f"{phase_name}.json"
            if phase_file.exists():
                try:
                    with open(phase_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return self._parse_phase_data(data, phase_name, latest_dir.name)
                except Exception as e:
                    logger.warning(f"解析 {phase_file} 失败: {e}，跳过 dream boost")
                    return DreamSignals()

        logger.debug(f"在 {latest_dir} 中未找到有效的 phase 文件，跳过 dream boost")
        return DreamSignals()

    def _parse_phase_data(self, data: dict, phase: str, date_str: str) -> DreamSignals:
        """解析 phase JSON 数据为 DreamSignals"""
        try:
            last_time = datetime.fromisoformat(data.get('timestamp', date_str))
        except Exception:
            last_time = datetime.now()

        return DreamSignals(
            last_dream_time=last_time,
            phase=phase,
            promotion_candidates=data.get('candidates', []),
            avg_dream_score=data.get('avg_score', 0.0),
            pattern_themes=data.get('patterns', []),
            enabled=True
        )


class DreamScoreCalculator:
    """基于 6 维信号计算 dream boost 分数"""

    # 信号权重
    WEIGHTS = {
        'frequency': 0.24,
        'relevance': 0.30,
        'recency': 0.15,
        'consolidation': 0.10,
        'conceptual_richness': 0.06,
        'query_diversity': 0.15,
    }

    def __init__(self):
        pass

    def calculate_dream_boost(
        self,
        memory: Dict[str, Any],
        signals: DreamSignals
    ) -> float:
        """
        计算给定记忆的 dream boost 值（0.0-1.0）。
        如果 signals.enabled=False，返回 0.0。
        """
        if not signals.enabled:
            return 0.0

        scores = {}

        # 1. Frequency (0.24): min(access_count / 10, 1.0)
        access_count = memory.get('access_count', 0)
        scores['frequency'] = min(access_count / 10.0, 1.0)

        # 2. Relevance (0.30): 如果 memory 在 promotion_candidates 中则得满分
        memory_id = memory.get('id')
        scores['relevance'] = 1.0 if memory_id in signals.promotion_candidates else 0.0

        # 3. Recency (0.15): 指数衰减，30天半衰期
        updated_at_str = memory.get('updated_at') or memory.get('created_at', '')
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str)
                days_since = (datetime.now() - updated_at).days
                scores['recency'] = max(0.0, 1.0 - (days_since / 30.0))
            except Exception:
                scores['recency'] = 0.0
        else:
            scores['recency'] = 0.0

        # 4. Consolidation (0.10): 在多个 candidates 中出现代表高价值
        scores['consolidation'] = 1.0 if signals.phase == 'deep' and memory_id in signals.promotion_candidates else 0.0

        # 5. Conceptual richness (0.06): 基于 l2_full_text 长度
        l2_text = memory.get('l2_full_text', '') or ''
        scores['conceptual_richness'] = min(len(l2_text) / 500.0, 1.0)

        # 6. Query diversity (0.15): 估算，access_count 越多代表查询越多样
        scores['query_diversity'] = min(access_count / 10.0, 1.0)

        # 加权求和
        total = sum(scores[key] * weight for key, weight in self.WEIGHTS.items())

        # 归一化到 0.0-1.0
        return min(max(total, 0.0), 1.0)
