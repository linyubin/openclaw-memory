#!/usr/bin/env python3
# memory/verify_embedding.py

import sqlite3
import numpy as np
from pathlib import Path

DB_PATH = "/home/andy/.openclaw/workspace/memory/memory.db"

def verify_latest_memory():
    if not Path(DB_PATH).exists():
        print(f"[!] 找不到数据库文件: {DB_PATH}")
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 获取最新写入的一条代理记忆（就是刚才刚生成的那个错误记录）
            cursor.execute('''
                SELECT id, l0_summary, created_at, embedding 
                FROM agent_memory 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            
            if not row:
                print("📭 数据库中没有找到任何记录。")
                return
                
            mem_id, summary, created_at, embedding_blob = row
            
            print(f"📌 正在检查最新记忆 [ID: {mem_id}]")
            print(f"🕒 时间: {created_at}")
            print(f"📝 摘要: {summary}")
            
            if not embedding_blob:
                print("\n❌ 严重错误：该记忆完全没有 embedding 数据（BLOB为空）！")
                return
                
            # 将 SQLite 中的二进制 BLOB 反序列化为 numpy 浮点数组
            vector = np.frombuffer(embedding_blob, dtype=np.float32)
            
            print(f"\n📊 向量维度: {len(vector)}")
            
            # 核心验证逻辑：检查是否全为 0
            # np.any() 如果数组中有任何非 0 元素，返回 True
            if not np.any(vector):
                print("\n⚠️ 警告：这是一个【全零向量】！")
                print("这意味着 API 调用依然失败了，系统再次触发了降级保护。请检查网络或 API Key。")
            else:
                print("\n✅ 验证完美通过！这不是全零向量，底层大模型已成功赋予这段记忆几何语义。")
                print(f"🔢 真实高维坐标前 5 位预览: {vector[:5]}")
                
    except Exception as e:
        print(f"❌ 验证过程中发生异常: {e}")

if __name__ == "__main__":
    verify_latest_memory()