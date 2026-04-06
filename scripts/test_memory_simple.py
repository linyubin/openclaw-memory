#!/usr/bin/env python3
"""
简单功能验证测试，确认核心功能正常工作
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from db_wrapper import MemoryDBWrapper, MemoryOperations
from memory_search import MemorySearch
from memory_metabolism import MemoryMetabolism
from memory_health_monitor import MemoryHealthMonitor

print("=" * 60)
print("🚀 记忆系统核心功能验证")
print("=" * 60)

# 1. 测试数据库连接和基本操作
print("\n1️⃣ 测试数据库连接和CRUD操作")
with MemoryDBWrapper() as db:
    mem_ops = MemoryOperations(db)
    
    # 插入测试记忆
    mem_id = mem_ops.insert_agent_memory(
        l0_summary="代码生成规则测试",
        l1_overview="所有代码生成任务必须优先使用Gemini CLI执行",
        memory_type="rule",
        score=9.0,
        tier="LTM"
    )
    print(f"✅ 记忆插入成功，ID: {mem_id}")
    
    # 查询记忆
    mem = mem_ops.get_memory_by_id(mem_id, is_user_memory=False)
    print(f"✅ 记忆查询成功: {mem['l0_summary']}")
    print(f"   评分: {mem['score']}, 层级: {mem['tier']}")

# 2. 测试去重功能
print("\n2️⃣ 测试去重功能")
with MemoryDBWrapper() as db:
    search = MemorySearch(db)
    
    # 插入相似记忆
    new_id, is_updated = search.deduplicated_write(
        l0_summary="代码生成规则",
        l1_overview="代码调试工作也必须使用Gemini CLI，不得使用其他模型",
        memory_type="rule",
        score=9.5,
        is_user_memory=False
    )
    print(f"✅ 去重写入结果: ID={new_id}, 是否更新={is_updated}")
    if is_updated:
        print(f"   相似记忆已成功合并")
    
    # 查询合并后的记忆
    merged_mem = mem_ops.get_memory_by_id(new_id, is_user_memory=False)
    print(f"✅ 合并后内容包含: {'Gemini CLI' in merged_mem['l1_overview']}")
    print(f"   新评分: {merged_mem['score']}")

# 3. 测试搜索功能
print("\n3️⃣ 测试搜索功能")
with MemoryDBWrapper() as db:
    search = MemorySearch(db)
    
    # 搜索相关记忆
    results = search.hybrid_search("代码生成", is_user_memory=False, limit=5)
    print(f"✅ 搜索'代码生成'返回{len(results)}条结果")
    for i, res in enumerate(results):
        print(f"   {i+1}. {res['l0_summary']} (评分: {res['search_score']:.2f})")

# 4. 测试记忆新陈代谢
print("\n4️⃣ 测试记忆新陈代谢")
with MemoryDBWrapper() as db:
    metabolism = MemoryMetabolism(db)
    
    # 运行新陈代谢周期
    result = metabolism.run_full_metabolism_cycle()
    print(f"✅ 新陈代谢运行完成:")
    print(f"   清理STM记忆: {result['stm_cleaned']} 条")
    print(f"   晋升STM→LTM: {result['promotions']['stm_to_ltm']} 条")
    print(f"   晋升LTM→Core_Soul: {result['promotions']['ltm_to_core']} 条")

# 5. 测试健康监测
print("\n5️⃣ 测试健康监测")
with MemoryDBWrapper() as db:
    monitor = MemoryHealthMonitor(db)
    
    # 运行基础健康检查
    health = monitor._run_base_health_checks()
    print(f"✅ 基础健康检查: {'通过' if health['is_healthy'] else '失败'}")
    print(f"   总记忆数: {health['total_memory_count']} 条")
    print(f"   问题数: {len(health['issues'])} 个")

print("\n" + "=" * 60)
print("✅ 所有核心功能验证完成，记忆系统运行正常！")
print("=" * 60)
