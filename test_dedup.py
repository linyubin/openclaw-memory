#!/usr/bin/env python3
# memory/test_dedup.py

from db_wrapper import MemoryDBWrapper
from memory_search import MemorySearch

def test_semantic_deduplication():
    db = MemoryDBWrapper()
    searcher = MemorySearch(db)

    print("=== 🧪 测试 1: 写入初始记忆 ===")
    summary1 = "Andy周末喜欢喝冰美式"
    overview1 = "用户Andy提到他周末放松的时候，最喜欢的饮料是加冰的美式咖啡。"
    
    id1, is_merged1 = searcher.deduplicated_write(
        l0_summary=summary1,
        l1_overview=overview1,
        memory_type="preference",
        score=7.0,  # 初始评分 7.0
        tier="STM",
        is_user_memory=True
    )
    print(f"✅ 写入结果 -> 分配 ID: {id1} | 是否触发合并: {is_merged1}")
    
    print("\n=== 🧪 测试 2: 写入字面不同但语义相似的记忆 ===")
    # 注意：这里的汉字几乎和上面完全不同
    summary2 = "双休日Andy爱点冷咖啡"
    overview2 = "用户表示周六周日休息时，经常会喝冰镇的黑咖。"
    
    id2, is_merged2 = searcher.deduplicated_write(
        l0_summary=summary2,
        l1_overview=overview2,
        memory_type="preference",
        score=8.5,  # 假设这次评估的分数更高
        tier="STM",
        is_user_memory=True
    )
    print(f"✅ 写入结果 -> 分配 ID: {id2} | 是否触发合并: {is_merged2}")
    
    print("\n=== 🔍 验证数据库底层数据 ===")
    if id1 == id2 and is_merged2:
        print("🎉 完美成功！系统准确识别出了语义重复，没有创建新记录。")
        
        # 读取合并后的内容
        cursor = db.execute("SELECT score, access_count, l1_overview FROM user_memory WHERE id = ?", (id1,))
        row = cursor.fetchone()
        if row:
            print(f"⭐ 当前评分: {row[0]} (预期: 8.5，取两次评分的最大值)")
            print(f"📈 访问频次: {row[1]} (预期: 1，因为合并相当于被强化调用了一次)")
            print("📝 智能合并后的 L1 概述内容:")
            print("-" * 50)
            print(row[2])
            print("-" * 50)
    else:
        print("❌ 测试未达到预期！系统判定这两句话是不同的记忆，生成了两个 ID。")
        print("💡 可能原因：相似度阈值 (SIMILARITY_THRESHOLD) 设置过高，或者 embedding 模型的区分度不够。")

if __name__ == "__main__":
    test_semantic_deduplication()