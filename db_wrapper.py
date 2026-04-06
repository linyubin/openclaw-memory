#!/usr/bin/env python3
"""
OpenClaw 记忆系统数据库包装器
实现严格的异常抛出机制，禁止静默失败
"""
import sqlite3
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.ERROR,
    format='\033[91m%(asctime)s - MEMORY_DB_ERROR - %(message)s\033[0m'  # 红色错误日志
)

class MemoryDBException(Exception):
    """记忆系统数据库自定义异常"""
    pass

class MemoryDBWrapper:
    """
    记忆系统数据库包装器
    所有数据库操作都通过此类执行，确保异常被正确抛出
    """
    
    def __init__(self, db_path: str = "/home/andy/.openclaw/workspace/memory/memory.db"):
        """
        初始化数据库连接
        :param db_path: SQLite数据库文件路径
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()
    
    def _connect(self) -> None:
        """建立数据库连接，失败则抛出异常"""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False,
                timeout=20  # 20秒超时，避免无限等待
            )
            # 启用外键约束
            self.conn.execute("PRAGMA foreign_keys = ON")
            # 启用 WAL 模式以提高并发性能
            self.conn.execute("PRAGMA journal_mode = WAL")
            # 设置同步模式为 FULL 确保数据持久化
            self.conn.execute("PRAGMA synchronous = FULL")
        except Exception as e:
            error_msg = f"数据库连接失败: {str(e)}"
            logging.error(error_msg)
            raise MemoryDBException(error_msg) from e
    
    def _init_schema(self) -> None:
        """初始化数据库架构，失败则抛出异常"""
        # schema.sql 与数据库文件在同一目录
        schema_path = self.db_path.parent / "schema.sql"
        if not schema_path.exists():
            error_msg = f"数据库架构文件不存在: {schema_path}"
            logging.error(error_msg)
            raise MemoryDBException(error_msg)
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = f.read()
            
            cursor = self.conn.cursor()
            cursor.executescript(schema)
            self.conn.commit()
        except Exception as e:
            error_msg = f"数据库架构初始化失败: {str(e)}"
            logging.error(error_msg)
            self.conn.rollback()
            raise MemoryDBException(error_msg) from e
    
    def _check_connection(self) -> None:
        """检查数据库连接是否有效，无效则尝试重连，重连失败则抛出异常"""
        if self.conn is None:
            self._connect()
            return
        
        try:
            # 执行简单查询测试连接
            self.conn.execute("SELECT 1")
        except sqlite3.ProgrammingError:
            # 连接已关闭，尝试重连
            try:
                self._connect()
            except Exception as e:
                error_msg = f"数据库连接已断开，重连失败: {str(e)}"
                logging.error(error_msg)
                raise MemoryDBException(error_msg) from e
        except Exception as e:
            error_msg = f"数据库连接异常: {str(e)}"
            logging.error(error_msg)
            raise MemoryDBException(error_msg) from e
    
    def execute(self, query: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        """
        执行SQL查询，失败则抛出异常
        :param query: SQL查询语句
        :param params: 查询参数
        :return: 游标对象
        """
        self._check_connection()
        params = params or ()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.IntegrityError as e:
            error_msg = f"数据完整性错误: {str(e)}，查询: {query}，参数: {params}"
            logging.error(error_msg)
            self.conn.rollback()
            raise MemoryDBException(error_msg) from e
        except sqlite3.OperationalError as e:
            error_msg = f"数据库操作错误: {str(e)}，查询: {query}，参数: {params}"
            logging.error(error_msg)
            self.conn.rollback()
            raise MemoryDBException(error_msg) from e
        except Exception as e:
            error_msg = f"SQL执行失败: {str(e)}，查询: {query}，参数: {params}"
            logging.error(error_msg)
            self.conn.rollback()
            raise MemoryDBException(error_msg) from e
    
    def commit(self) -> None:
        """提交事务，失败则抛出异常"""
        self._check_connection()
        try:
            self.conn.commit()
        except Exception as e:
            error_msg = f"事务提交失败: {str(e)}"
            logging.error(error_msg)
            self.conn.rollback()
            raise MemoryDBException(error_msg) from e
    
    def rollback(self) -> None:
        """回滚事务，失败则抛出异常"""
        self._check_connection()
        try:
            self.conn.rollback()
        except Exception as e:
            error_msg = f"事务回滚失败: {str(e)}"
            logging.error(error_msg)
            raise MemoryDBException(error_msg) from e
    
    def close(self) -> None:
        """关闭数据库连接，失败则抛出异常"""
        if self.conn is None:
            return
        
        try:
            self.conn.close()
            self.conn = None
        except Exception as e:
            error_msg = f"数据库连接关闭失败: {str(e)}"
            logging.error(error_msg)
            raise MemoryDBException(error_msg) from e
    
    def __enter__(self) -> 'MemoryDBWrapper':
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口，自动关闭连接"""
        self.close()

# 记忆操作封装
class MemoryOperations:
    """记忆系统操作封装"""
    
    def __init__(self, db: MemoryDBWrapper):
        self.db = db
    
# 修改 db_wrapper.py 中的 MemoryOperations 类下的两个方法

    def insert_user_memory(
        self,
        l0_summary: str,
        l1_overview: str,
        l2_full_text: Optional[str] = None,
        memory_type: str = 'fact',
        score: float = 0.0,
        tier: str = 'STM',
        embedding: Optional[bytes] = None  # 新增向量参数
    ) -> int:
        cursor = self.db.execute("""
            INSERT INTO user_memory (l0_summary, l1_overview, l2_full_text, memory_type, score, tier, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (l0_summary, l1_overview, l2_full_text, memory_type, score, tier, embedding))
        self.db.commit()
        return cursor.lastrowid
    
    def insert_agent_memory(
        self,
        l0_summary: str,
        l1_overview: str,
        l2_full_text: Optional[str] = None,
        memory_type: str = 'skill',
        score: float = 0.0,
        tier: str = 'STM',
        embedding: Optional[bytes] = None  # 新增向量参数
    ) -> int:
        cursor = self.db.execute("""
            INSERT INTO agent_memory (l0_summary, l1_overview, l2_full_text, memory_type, score, tier, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (l0_summary, l1_overview, l2_full_text, memory_type, score, tier, embedding))
        self.db.commit()
        return cursor.lastrowid
    
    def update_memory_access(self, memory_id: int, is_user_memory: bool = True) -> None:
        """更新记忆的访问时间和访问次数"""
        table = 'user_memory' if is_user_memory else 'agent_memory'
        self.db.execute(f"""
            UPDATE {table}
            SET access_count = access_count + 1, last_accessed_at = ?
            WHERE id = ?
        """, (datetime.now(), memory_id))
        self.db.commit()
    
    def get_memory_by_id(self, memory_id: int, is_user_memory: bool = True) -> Optional[Dict[str, Any]]:
        """根据ID获取记忆"""
        table = 'user_memory' if is_user_memory else 'agent_memory'
        cursor = self.db.execute(f"SELECT * FROM {table} WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    
    def search_memories(
        self,
        query: str,
        is_user_memory: bool = True,
        tier: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索记忆（基础关键词搜索，语义搜索需配合向量引擎）"""
        table = 'user_memory' if is_user_memory else 'agent_memory'
        params = []
        sql = f"SELECT * FROM {table} WHERE (l0_summary LIKE ? OR l1_overview LIKE ?)"
        params.extend([f'%{query}%', f'%{query}%'])
        
        if tier:
            sql += " AND tier = ?"
            params.append(tier)
        
        sql += " ORDER BY score DESC, access_count DESC, last_accessed_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.db.execute(sql, tuple(params))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
