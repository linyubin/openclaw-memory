#!/usr/bin/env python3
"""
OpenClaw 记忆系统本地 API 网关
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from db_wrapper import MemoryDBWrapper
from memory_search import MemorySearch
from memory_metabolism import MemoryMetabolism
from pathlib import Path
import logging

# 屏蔽 jieba 的日志
import jieba
jieba.setLogLevel(logging.ERROR)

app = FastAPI(title="OpenClaw Memory API")

# 全局初始化数据库和搜索器，常驻内存
db = MemoryDBWrapper()
searcher = MemorySearch(db)

# 初始化 metabolism 时传入 dreams_dir
MEMORY_DIR = Path(__file__).parent
DREAMS_DIR = MEMORY_DIR / '.dreams'

class WriteRequest(BaseModel):
    l0_summary: str
    l1_overview: str
    l2_full_text: Optional[str] = None
    is_user_memory: bool = True

class SearchRequest(BaseModel):
    query: str
    is_user_memory: bool = True
    limit: int = 5

@app.post("/api/memory/write")
async def write_memory(req: WriteRequest):
    try:
        mem_id, is_update = searcher.deduplicated_write(
            l0_summary=req.l0_summary,
            l1_overview=req.l1_overview,
            l2_full_text=req.l2_full_text,
            is_user_memory=req.is_user_memory
        )
        return {"status": "success", "id": mem_id, "merged": is_update}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/search")
async def search_memory(req: SearchRequest):
    try:
        results = searcher.hybrid_search(
            query=req.query,
            is_user_memory=req.is_user_memory,
            limit=req.limit
        )
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/metabolism")
async def run_metabolism():
    """触发记忆新陈代谢周期：清理过期STM、晋升记忆、更新元数据"""
    try:
        metabolism = MemoryMetabolism(db, dreams_dir=DREAMS_DIR)
        result = metabolism.run_full_metabolism_cycle()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 在本地 8000 端口启动服务
    uvicorn.run(app, host="127.0.0.1", port=8000)