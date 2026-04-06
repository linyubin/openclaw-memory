#!/usr/bin/env python3
# test_embedding.py

import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载当前目录下的 .env 文件
load_dotenv()

# 尝试获取你可能配置的 API Key 名称
api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("EMBEDDING_API_KEY")

if not api_key:
    print("❌ 错误: 未在 .env 文件中找到 API Key (SILICONFLOW_API_KEY 或 EMBEDDING_API_KEY)。")
    exit(1)

# 隐码打印 Key 确认读取正确
print(f"🔑 成功读取 API Key: {api_key[:8]}......{api_key[-4:]}")
print("🚀 正在向 SiliconFlow 发送请求，模型: BAAI/bge-m3 ...\n")

try:
    # 初始化客户端
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1"
    )
    
    # 发送测试请求
    response = client.embeddings.create(
        model="BAAI/bge-m3",
        input=["你好，这是测试记忆系统向量引擎的一段话。"],
        encoding_format="float"
    )
    
    # 提取结果
    vector = response.data[0].embedding
    dim = len(vector)
    
    print("🎉 测试成功！账号余额充足，API 工作正常。")
    print(f"📊 向量维度: {dim} 维")
    print(f"🔢 向量前 5 个数值预览: {vector[:5]}")
    
except Exception as e:
    print("❌ 测试失败，云端返回了以下错误:")
    print(f"   {str(e)}")
    print("\n💡 提示: 如果依然显示 '403 ... insufficient balance'，说明充值还没到账，或者使用的是免费额度不支持的模型。")