#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path("/home/andy/.openclaw/workspace/memory/memory.db")

try:
    conn = sqlite3.connect(db_path)
    # 给用户记忆表和代理记忆表增加 embedding 字段
    conn.execute("ALTER TABLE user_memory ADD COLUMN embedding BLOB;")
    conn.execute("ALTER TABLE agent_memory ADD COLUMN embedding BLOB;")
    conn.commit()
    print("✅ 数据库修补成功！已添加 embedding 字段。")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("⚠️ 字段已经存在，无需重复添加。")
    else:
        print(f"❌ 发生错误: {e}")
finally:
    conn.close()