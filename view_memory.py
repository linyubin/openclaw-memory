#!/usr/bin/env python3
# memory/view_memory.py

import sqlite3
from pathlib import Path

DB_PATH = "memory.db"

def print_table(title, rows):
    print(f"\n=== {title} ===")
    if not rows:
        print("  (空)")
        return
    
    # 打印表头
    print(f"{'ID':<4} | {'层级 (Tier)':<10} | {'类型 (Type)':<12} | {'评分':<5} | {'访问':<4} | {'创建时间':<20} | {'L0 摘要 (Summary)'}")
    print("-" * 110)
    
    for row in rows:
        id_, tier, m_type, score, access_count, created_at, summary = row
        
        # 格式化数据，防止超长导致错位
        summary_short = summary.replace('\n', ' ')[:40] + "..." if summary and len(summary) > 40 else summary
        time_short = str(created_at).split('.')[0].replace('T', ' ') if created_at else ""
        score_str = f"{score:.1f}" if score is not None else "0.0"
        
        print(f"{id_:<4} | {tier:<10} | {m_type:<12} | {score_str:<5} | {access_count:<4} | {time_short:<20} | {summary_short}")

def main():
    if not Path(DB_PATH).exists():
        print(f"[!] 找不到数据库文件: {DB_PATH}")
        return
        
    print("🔍 正在扫描认知数据库...")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # --- 1. 查询 Agent 记忆 (技能、规则、状态/错误) ---
            cursor.execute('''
                SELECT id, tier, memory_type, score, access_count, created_at, l0_summary 
                FROM agent_memory 
                ORDER BY 
                    CASE tier WHEN 'Core_Soul' THEN 1 WHEN 'LTM' THEN 2 ELSE 3 END, 
                    created_at DESC 
                LIMIT 15
            ''')
            print_table("🤖 代理记忆库 (Agent Memory)", cursor.fetchall())
            
            # --- 2. 查询 User 记忆 (用户偏好、项目事实) ---
            cursor.execute('''
                SELECT id, tier, memory_type, score, access_count, created_at, l0_summary 
                FROM user_memory 
                ORDER BY 
                    CASE tier WHEN 'Core_Soul' THEN 1 WHEN 'LTM' THEN 2 ELSE 3 END, 
                    created_at DESC 
                LIMIT 15
            ''')
            print_table("👤 用户记忆库 (User Memory)", cursor.fetchall())
            
    except Exception as e:
        print(f"[!] 查询失败: {e}")

if __name__ == "__main__":
    main()
