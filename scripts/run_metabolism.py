#!/usr/bin/env python3
"""
记忆新陈代谢定时任务脚本
用于 cron 定时触发记忆清理和晋升

用法:
    python3 run_metabolism.py
    python3 run_metabolism.py --dry-run

定时配置 (系统 crontab):
    # 每天凌晨 3:00 执行
    0 3 * * * cd /home/andy/tech_tools/openclaw && python3 workspace/memory/scripts/run_metabolism.py >> /var/log/openclaw_metabolism.log 2>&1
"""
import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加 memory 模块路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.dirname(SCRIPT_DIR)  # parent of scripts/
sys.path.insert(0, MEMORY_DIR)


def find_db_path() -> str:
    """自动检测数据库路径"""
    # 1. 优先使用环境变量
    env_path = os.environ.get('MEMORY_DB_PATH')
    if env_path and Path(env_path).exists():
        return env_path

    # 2. 查找 .env 文件
    env_file = Path(MEMORY_DIR) / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith('MEMORY_DB_PATH='):
                db_path = line.split('=', 1)[1].strip().strip('"')
                if Path(db_path).exists():
                    return db_path

    # 3. 尝试在当前目录树下查找
    local_db = Path(MEMORY_DIR) / 'memory.db'
    if local_db.exists():
        return str(local_db)

    # 4. 默认路径（由 db_wrapper 使用）
    return "/home/andy/.openclaw/workspace/memory/memory.db"

def find_dreams_dir() -> Optional[Path]:
    """自动检测 .dreams/ 目录路径"""
    # 1. 优先在 MEMORY_DIR 中查找
    memory_dir = Path(MEMORY_DIR)
    dreams_dir = memory_dir / '.dreams'
    if dreams_dir.exists():
        return dreams_dir
    return None

from db_wrapper import MemoryDBWrapper
from memory_metabolism import MemoryMetabolism

# 配置日志（需要先清除已有 handler）
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_metabolism_cycle(dry_run: bool = False) -> dict:
    """执行记忆新陈代谢周期"""
    logger.info("=" * 50)
    logger.info("开始记忆新陈代谢周期")

    db_path = find_db_path()
    logger.info(f"数据库路径: {db_path}")

    try:
        db = MemoryDBWrapper(db_path)
        dreams_dir = find_dreams_dir()
        metabolism = MemoryMetabolism(db, dreams_dir=dreams_dir)

        if dry_run:
            # 干运行模式：只评估不执行
            logger.info("[DRY-RUN] 干运行模式，仅报告预计变更")

            # 统计当前状态
            cursor = db.execute("SELECT COUNT(*) FROM user_memory WHERE tier = 'STM'")
            stm_count = cursor.fetchone()[0]

            cursor = db.execute("SELECT COUNT(*) FROM user_memory WHERE tier = 'LTM'")
            ltm_count = cursor.fetchone()[0]

            cursor = db.execute("SELECT COUNT(*) FROM user_memory WHERE tier = 'Core_Soul'")
            core_count = cursor.fetchone()[0]

            logger.info(f"当前状态: STM={stm_count}, LTM={ltm_count}, Core_Soul={core_count}")
            logger.info(f"[DRY-RUN] 不会执行任何变更")
            return {'dry_run': True, 'stm_count': stm_count, 'ltm_count': ltm_count, 'core_count': core_count}
        else:
            # 正常执行
            result = metabolism.run_full_metabolism_cycle()
            logger.info(f"新陈代谢周期完成: {result}")
            return result

    except Exception as e:
        logger.error(f"记忆新陈代谢失败: {str(e)}")
        raise


def main():
    parser = argparse.ArgumentParser(description='OpenClaw 记忆新陈代谢定时任务')
    parser.add_argument('--dry-run', action='store_true', help='干运行模式，仅报告预计变更不执行')
    args = parser.parse_args()

    try:
        result = run_metabolism_cycle(dry_run=args.dry_run)
        logger.info("执行成功")
        return 0
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())