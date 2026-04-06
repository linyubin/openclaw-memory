#!/usr/bin/env python3
"""
混合搜索与主动去重模块 (SiliconFlow 重构版)
实现70%云端向量嵌入(BGE-M3) + 30%本地关键词BM25的混合搜索
"""
import os
import sqlite3
import numpy as np
import jieba
import logging
import jieba
jieba.setLogLevel(logging.ERROR) # <--- 新增这行，让 jieba 闭嘴
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from db_wrapper import MemoryDBWrapper, MemoryDBException

load_dotenv()
logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.7 # 注意：真向量的相似度通常比 TF-IDF 高，阈值需上调至 0.85 左右

class MemorySearch:
    def __init__(self, db: MemoryDBWrapper):
        self.db = db
        # 初始化 SiliconFlow 客户端
        self.client = OpenAI(
            api_key=os.getenv("EMBEDDING_API_KEY"),
            base_url=os.getenv("EMBEDDING_ENDPOINT")
        )
        self.model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """调用 SiliconFlow 获取向量，并转换为 Numpy 数组"""
        try:
            # 清理换行符以优化嵌入质量
            clean_text = text.replace("\n", " ")
            response = self.client.embeddings.create(
                model=self.model,
                input=[clean_text],
                encoding_format="float"
            )
            # 强制转换为 float32 格式，节省树莓派内存
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"SiliconFlow API 调用失败: {e}")
            # 返回 1024 维的零向量作为降级保护
            return np.zeros(1024, dtype=np.float32)

    def calculate_semantic_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """使用 Numpy 计算余弦相似度（在树莓派上极快）"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def check_duplicate(self, new_summary: str, new_vector: np.ndarray, is_user_memory: bool = True) -> Tuple[bool, Optional[int], float]:
        table = 'user_memory' if is_user_memory else 'agent_memory'
        # 只取出包含向量的记录
        cursor = self.db.execute(f"SELECT id, embedding FROM {table} WHERE embedding IS NOT NULL")
        existing_memories = cursor.fetchall()
        
        max_similarity = 0.0
        duplicate_id = None
        
        for mem_id, embedding_blob in existing_memories:
            # 将 SQLite 中的 BLOB 二进制数据反序列化为 Numpy 数组
            existing_vector = np.frombuffer(embedding_blob, dtype=np.float32)
            similarity = self.calculate_semantic_similarity(new_vector, existing_vector)
            
            if similarity > max_similarity:
                max_similarity = similarity
                if similarity >= SIMILARITY_THRESHOLD:
                    duplicate_id = mem_id
        
        return (duplicate_id is not None, duplicate_id, max_similarity)
    
    def deduplicated_write(self, l0_summary: str, l1_overview: str, l2_full_text: Optional[str] = None, memory_type: str = 'fact', score: float = 0.0, tier: str = 'STM', is_user_memory: bool = True) -> Tuple[int, bool]:
        # 写入前，先获取新记忆的向量
        new_vector = self.get_embedding(f"{l0_summary} {l1_overview}")
        # 将向量序列化为二进制以便存入 SQLite
        vector_blob = new_vector.tobytes()
        
        is_duplicate, duplicate_id, similarity = self.check_duplicate(l0_summary, new_vector, is_user_memory)
        table = 'user_memory' if is_user_memory else 'agent_memory'
        
        if is_duplicate and duplicate_id is not None:
            # 存在重复，执行 UPSERT（合并逻辑保持不变，但更新 embedding）
            existing = self.db.execute(f"SELECT l1_overview, l2_full_text, score FROM {table} WHERE id = ?", (duplicate_id,)).fetchone()
            if existing:
                existing_l1, existing_l2, existing_score = existing
                merged_l1 = f"{existing_l1}\n\n更新于 {datetime.now().isoformat()}:\n{l1_overview}"
                merged_l2 = existing_l2 or ""
                if l2_full_text:
                    merged_l2 = f"{merged_l2}\n\n{l2_full_text}" if merged_l2 else l2_full_text
                merged_score = max(existing_score, score)
                
                self.db.execute(f"""
                    UPDATE {table}
                    SET l0_summary = ?, l1_overview = ?, l2_full_text = ?, 
                        score = ?, updated_at = ?, access_count = access_count + 1,
                        embedding = ?
                    WHERE id = ?
                """, (l0_summary, merged_l1, merged_l2, merged_score, datetime.now().isoformat(), vector_blob, duplicate_id))
                self.db.commit()
                return (duplicate_id, True)
        
        # 插入新记录，带有 embedding_blob
        cursor = self.db.execute(f"""
            INSERT INTO {table} (l0_summary, l1_overview, l2_full_text, memory_type, score, tier, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (l0_summary, l1_overview, l2_full_text, memory_type, score, tier, vector_blob))
        self.db.commit()
        return (cursor.lastrowid, False)
    
    def hybrid_search(self, query: str, is_user_memory: bool = True, tier: Optional[str] = None, limit: int = 10, vector_weight: float = 0.7, keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        table = 'user_memory' if is_user_memory else 'agent_memory'
        query_vector = self.get_embedding(query)
        query_terms = set(jieba.cut(query.lower())) # 保留 jieba 做精确分词
        
        cursor = self.db.execute(f"SELECT id, l0_summary, l1_overview, embedding FROM {table} WHERE embedding IS NOT NULL")
        all_memories = cursor.fetchall()
        
        if not all_memories: return []
        
        combined_scores = []
        for mem_id, summary, overview, embedding_blob in all_memories:
            text = f"{summary} {overview}".lower()
            
            # 计算 30% 的 BM25 近似分
            match_count = sum(1 for term in query_terms if term in text)
            keyword_score = match_count / len(query_terms) if query_terms else 0.0
            
            # 计算 70% 的向量余弦分
            existing_vector = np.frombuffer(embedding_blob, dtype=np.float32)
            semantic_score = self.calculate_semantic_similarity(query_vector, existing_vector)
            
            # 综合评分
            final_score = (semantic_score * vector_weight) + (keyword_score * keyword_weight)
            combined_scores.append((mem_id, final_score))
            
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for mem_id, score in combined_scores[:limit]:
            cursor = self.db.execute(f"SELECT * FROM {table} WHERE id = ?", (mem_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                mem_dict = dict(zip(columns, row))
                # 过滤掉体积庞大的 embedding 字段，不返回给 LLM
                if 'embedding' in mem_dict:
                    del mem_dict['embedding']
                if tier and mem_dict['tier'] != tier: continue
                mem_dict['search_score'] = score
                results.append(mem_dict)
                
        return results