#!/usr/bin/env python3
from db_wrapper import MemoryDBWrapper, MemoryOperations
from memory_search import MemorySearch
import sqlite3

print("Testing memory system installation...")

# 测试数据库连接
with MemoryDBWrapper() as db:
    print("✓ Database connection successful")
    
    # 测试插入记忆
    mem_ops = MemoryOperations(db)
    mem_id = mem_ops.insert_agent_memory(
        l0_summary="记忆系统测试",
        l1_overview="这是新记忆系统的第一条测试记录",
        memory_type="architecture",
        score=9.0,
        tier="LTM"
    )
    print(f"✓ Test memory inserted with ID: {mem_id}")
    
    # 测试搜索
    search = MemorySearch(db)
    results = search.hybrid_search("记忆系统", is_user_memory=False)
    print(f"✓ Search returned {len(results)} results")
    print(f"✓ First result: ID={results[0]['id']}, Score={results[0]['search_score']:.2f}")
    
    # 测试去重
    new_id, is_updated = search.deduplicated_write(
        l0_summary="记忆系统测试",
        l1_overview="这是重复的测试记录，应该被合并",
        memory_type="architecture",
        score=9.5,
        is_user_memory=False
    )
    print(f"✓ Deduplication test: new_id={new_id}, is_updated={is_updated}")
    assert is_updated == True, "Deduplication failed"
    assert new_id == mem_id, "Deduplication returned wrong ID"
    
    print("\n✅ All tests passed! New memory system is working correctly.")
