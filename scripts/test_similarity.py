#!/usr/bin/env python3
from memory_search import MemorySearch
from db_wrapper import MemoryDBWrapper

with MemoryDBWrapper() as db:
    search = MemorySearch(db)
    
    text1 = "代码执行规则 所有代码生成任务必须使用Gemini CLI执行"
    text2 = "代码生成规则 涉及代码生成、调试的工作必须优先使用Gemini CLI，不得使用其他模型"
    
    similarity = search.calculate_semantic_similarity(text1, text2)
    print(f"相似度: {similarity:.4f}")
    print(f"阈值: {search.SIMILARITY_THRESHOLD}")
    print(f"是否判定为重复: {similarity >= search.SIMILARITY_THRESHOLD}")
