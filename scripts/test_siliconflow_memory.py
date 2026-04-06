#!/usr/bin/env python3
"""
SiliconFlow 混合记忆系统端到端测试脚本
"""
import os
import sys
from dotenv import load_dotenv
from db_wrapper import MemoryDBWrapper
from memory_search import MemorySearch

def run_diagnostics():
    print("=== 🧠 OpenClaw 记忆系统诊断启动 ===")
    
    # 1. 环境检查
    load_dotenv()
    api_key = os.getenv("EMBEDDING_API_KEY")
    if not api_key:
        print("❌ 致命错误: 未在 .env 中找到 EMBEDDING_API_KEY")
        sys.exit(1)
    print("✅ 环境变量加载成功")

    try:
        db = MemoryDBWrapper()
        searcher = MemorySearch(db)
        print("✅ 数据库包装器与搜索器初始化成功")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)

    # 2. SiliconFlow API 与向量化测试
    print("\n--- 阶段 1: 向量引擎测试 ---")
    test_text = "这是一段用于测试云端模型的文本。"
    print("正在请求 SiliconFlow 获取 BGE-M3 向量...")
    vector = searcher.get_embedding(test_text)
    
    if len(vector) == 1024:
        print(f"✅ 成功获取 1024 维浮点向量 (前三位: {vector[:3]})")
    else:
        print(f"❌ 向量维度异常: {len(vector)}，期望值为 1024")
        sys.exit(1)

    # 3. 基础写入与重复检测测试
    print("\n--- 阶段 2: 认知去重与合并测试 ---")
    
    # 写入第一条记忆
    print("写入记忆 A: '用户是一名 Python 初学者'")
    id_1, is_update_1 = searcher.deduplicated_write(
        l0_summary="用户技能：Python 初学者",
        l1_overview="用户能读懂基础 Python 代码，但主要依赖 AI 编写。",
        is_user_memory=True
    )
    print(f"结果 -> ID: {id_1}, 是否为更新(合并): {is_update_1} (预期: False)")

    # 写入语义高度相似的第二条记忆
    print("\n写入记忆 B: '用户刚开始学 Python 编程'")
    id_2, is_update_2 = searcher.deduplicated_write(
        l0_summary="用户状态：刚开始学 Python",
        l1_overview="用户编程经验不多，需要简单明了的代码解释。",
        is_user_memory=True
    )
    print(f"结果 -> ID: {id_2}, 是否为更新(合并): {is_update_2} (预期: True)")
    
    if id_1 == id_2 and is_update_2:
        print("✅ 语义去重成功！系统准确识别了意思相同的记忆并执行了合并。")
    else:
        print("⚠️ 语义去重未触发。如果两个 ID 不同，说明 SIMILARITY_THRESHOLD 阈值可能设置得过高（当前通常为 0.85）。")

    # 写入一条完全不同的记忆
    id_3, _ = searcher.deduplicated_write(
        l0_summary="偏好：喜欢吃麻辣火锅",
        l1_overview="用户口味偏重，最喜欢四川火锅。",
        is_user_memory=True
    )

    # 4. 混合搜索测试
    print("\n--- 阶段 3: 混合检索测试 (70% 向量 + 30% BM25) ---")
    query = "用户的编程水平怎么样？"
    print(f"搜索词: '{query}'")
    
    results = searcher.hybrid_search(query, is_user_memory=True, limit=2)
    
    if results:
        print(f"✅ 找到 {len(results)} 条相关记忆:")
        for idx, res in enumerate(results):
            print(f"  [{idx+1}] 得分: {res.get('search_score', 0):.4f} | 摘要: {res['l0_summary']}")
        
        # 验证排名第一的是否是编程相关的记忆
        if "Python" in results[0]['l0_summary']:
            print("✅ 检索精准度测试通过！")
        else:
            print("❌ 检索精准度不佳，最高分记忆与查询意图不符。")
    else:
        print("❌ 未检索到任何记忆。")

    print("\n=== 诊断完成 ===")

if __name__ == "__main__":
    run_diagnostics()