#!/usr/bin/env python3
"""
OpenClaw 历史日志提纯与记忆导入工具 (Memory Harvester)
"""
import os
import glob
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 屏蔽 jieba 的加载日志
import jieba
jieba.setLogLevel(logging.ERROR)

# 导入本地记忆中枢
from db_wrapper import MemoryDBWrapper
from memory_search import MemorySearch

# 加载环境变量 (获取 API Key)
load_dotenv()
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY") # 请确保 .env 中有此配置

# 初始化大模型客户端 (使用 SiliconFlow 节点)
client = OpenAI(
    api_key=SILICONFLOW_API_KEY,
    base_url="https://api.siliconflow.cn/v1"
)

# 初始化本地数据库
db = MemoryDBWrapper()
searcher = MemorySearch(db)

# 提纯提示词：强制输出严格的 JSON 数组
HARVEST_PROMPT = """
你是一个高级认知提纯引擎。你的任务是阅读用户的历史聊天日志，提取出具有长期保留价值的记忆。
过滤掉：无意义的闲聊、临时的代码报错、已经解决的短期 Bug、打招呼。
提取出：用户的技术栈、编程习惯、生活偏好、系统架构决定、核心规则、重要事实。

请严格输出 JSON 数组格式，不要包含任何 Markdown 标记（如 ```json），直接输出方括号包裹的数组：
[
  {
    "l0_summary": "简短摘要（约10-20字，例如：系统架构：采用 SQLite 存储记忆）",
    "l1_overview": "详细背景和规则陈述（一两句话说明具体事实）",
    "is_user_memory": true
  }
]
如果日志中没有任何有价值的信息，请输出空的数组：[]
"""

def extract_memories_from_file(file_path):
    print(f"\n📄 正在阅读日志: {Path(file_path).name} ...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 如果文件太小，通常是空日志，直接跳过
    if len(content) < 50:
        print("   -> 文件过小，跳过。")
        return []

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3.2", # 使用性价比极高的 V3 模型进行阅读
            messages=[
                {"role": "system", "content": HARVEST_PROMPT},
                {"role": "user", "content": f"请提纯以下日志：\n{content[:8000]}"} # 截取前8000字符防止超长
            ],
            temperature=0.1 # 保持极低的温度，确保输出格式稳定
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # 清理可能残留的 markdown 标记
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:-3].strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output[3:-3].strip()

        memories = json.loads(raw_output)
        return memories

    except Exception as e:
        print(f"   ❌ 提纯失败: {e}")
        return []

def main():
    print("=== 🚜 启动 OpenClaw 记忆拾荒者 ===")
    
    # 查找上一级目录中所有的 Markdown 日志文件
    log_pattern = "/home/andy/.openclaw/workspace/memory/2026-*.md"
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        print("未找到匹配的历史日志文件。")
        return

    print(f"找到 {len(log_files)} 个历史日志文件，准备开始提纯...")
    
    total_extracted = 0
    total_merged = 0
    
    for file_path in log_files:
        memories = extract_memories_from_file(file_path)
        
        if not memories:
            continue
            
        print(f"   💡 提取到 {len(memories)} 条有价值的记忆，正在注入神经网络...")
        
        for mem in memories:
            try:
                mem_id, is_update = searcher.deduplicated_write(
                    l0_summary=mem["l0_summary"],
                    l1_overview=mem["l1_overview"],
                    is_user_memory=mem.get("is_user_memory", True)
                )
                if is_update:
                    total_merged += 1
                    print(f"      🔄 [合并/强化] {mem['l0_summary']}")
                else:
                    total_extracted += 1
                    print(f"      ✨ [新增事实] {mem['l0_summary']}")
            except Exception as e:
                print(f"      ❌ 注入失败: {e}")
                
    print(f"\n=== 🎉 拾荒完成 ===")
    print(f"共扫描 {len(log_files)} 个文件。")
    print(f"成功新增 {total_extracted} 条记忆，合并强化了 {total_merged} 条记忆。")

if __name__ == "__main__":
    main()