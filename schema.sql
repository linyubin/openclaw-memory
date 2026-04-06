-- OpenClaw 记忆系统数据库架构
-- 分为两个核心域：用户记忆（User_Memory）和代理记忆（Agent_Memory）

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- =============================================
-- 用户记忆域：存储用户偏好、个人信息、交互历史
-- =============================================

-- 用户记忆主表
CREATE TABLE IF NOT EXISTS user_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    l0_summary TEXT NOT NULL, -- ~100 tokens 摘要，用于快速索引和去重
    l1_overview TEXT NOT NULL, -- ~500 tokens 概述，用于结构化上下文注入
    l2_full_text TEXT, -- 完整文本，冷存储，仅显式深度检索时获取
    memory_type TEXT NOT NULL CHECK (memory_type IN ('preference', 'fact', 'interaction', 'task')),
    score REAL NOT NULL DEFAULT 0, -- 记忆重要性评分 0-10
    access_count INTEGER NOT NULL DEFAULT 0, -- 访问次数，用于晋升机制
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tier TEXT NOT NULL DEFAULT 'STM' CHECK (tier IN ('STM', 'LTM', 'Core_Soul')) -- 记忆层级：短期/长期/核心灵魂
);

-- 用户记忆向量索引表（用于语义搜索）
CREATE TABLE IF NOT EXISTS user_memory_embeddings (
    memory_id INTEGER PRIMARY KEY,
    embedding BLOB NOT NULL, -- 向量嵌入二进制数据
    FOREIGN KEY (memory_id) REFERENCES user_memory(id) ON DELETE CASCADE
);

-- =============================================
-- 代理记忆域：存储技能、系统状态、规则、运行时数据
-- =============================================

-- 代理记忆主表
CREATE TABLE IF NOT EXISTS agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    l0_summary TEXT NOT NULL, -- ~100 tokens 摘要，用于快速索引和去重
    l1_overview TEXT NOT NULL, -- ~500 tokens 概述，用于结构化上下文注入
    l2_full_text TEXT, -- 完整文本，冷存储，仅显式深度检索时获取
    memory_type TEXT NOT NULL CHECK (memory_type IN ('skill', 'rule', 'state', 'tool', 'architecture')),
    score REAL NOT NULL DEFAULT 0, -- 记忆重要性评分 0-10
    access_count INTEGER NOT NULL DEFAULT 0, -- 访问次数，用于晋升机制
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tier TEXT NOT NULL DEFAULT 'STM' CHECK (tier IN ('STM', 'LTM', 'Core_Soul')) -- 记忆层级：短期/长期/核心灵魂
);

-- 代理记忆向量索引表（用于语义搜索）
CREATE TABLE IF NOT EXISTS agent_memory_embeddings (
    memory_id INTEGER PRIMARY KEY,
    embedding BLOB NOT NULL, -- 向量嵌入二进制数据
    FOREIGN KEY (memory_id) REFERENCES agent_memory(id) ON DELETE CASCADE
);

-- =============================================
-- 系统元数据表
-- =============================================

CREATE TABLE IF NOT EXISTS memory_system_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 初始化系统元数据
INSERT OR IGNORE INTO memory_system_metadata (key, value) VALUES 
('schema_version', '1.0.0'),
('last_maintenance_run', ''),
('total_memory_count', '0'),
('core_soul_count', '0');

-- =============================================
-- 索引优化
-- =============================================

CREATE INDEX IF NOT EXISTS idx_user_memory_tier ON user_memory(tier);
CREATE INDEX IF NOT EXISTS idx_user_memory_score ON user_memory(score);
CREATE INDEX IF NOT EXISTS idx_user_memory_access_count ON user_memory(access_count);
CREATE INDEX IF NOT EXISTS idx_user_memory_created_at ON user_memory(created_at);

CREATE INDEX IF NOT EXISTS idx_agent_memory_tier ON agent_memory(tier);
CREATE INDEX IF NOT EXISTS idx_agent_memory_score ON agent_memory(score);
CREATE INDEX IF NOT EXISTS idx_agent_memory_access_count ON agent_memory(access_count);
CREATE INDEX IF NOT EXISTS idx_agent_memory_created_at ON agent_memory(created_at);
