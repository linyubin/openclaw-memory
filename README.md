# OpenClaw Memory System

OpenClaw 多层级认知记忆系统，支持 STM → LTM → Core_Soul 自动晋升，以及与 Dreaming 的集成。

## 核心模块

| 文件 | 功能 |
|------|------|
| `memory_metabolism.py` | 记忆新陈代谢：晋升、清理、评分 |
| `memory_search.py` | 混合搜索：70% 向量 + 30% BM25 |
| `db_wrapper.py` | SQLite 封装，严格异常机制 |
| `memory_api.py` | FastAPI 端口，提供 `/api/memory/write`、`/api/memory/search`、`/api/memory/metabolism` |
| `memory_executor.py` | Python 代码执行，自动错误记忆化 |
| `memory_health_monitor.py` | 健康监测：Serial Collapse、Memory Misevolution |

## 记忆层级

```
STM (Short-Term) ──晋升──> LTM (Long-Term) ──晋升──> Core_Soul
  7天保留                    评分≥7 或              访问≥20 且
  评分<3 清理                access_count≥5         评分≥8
```

## Dreaming 集成

当 `.dreams/` 目录存在时（memory-core 插件），Metabolism 自动读取 6 维评分信号：

| 信号 | 权重 | 说明 |
|------|------|------|
| Frequency | 0.24 | 访问频率 |
| Relevance | 0.30 | 向量相似度 |
| Recency | 0.15 | 时间衰减 |
| Consolidation | 0.10 | 梦境晋升候选 |
| Conceptual richness | 0.06 | 内容丰富度 |
| Query diversity | 0.15 | 查询多样性 |

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动 API 服务

```bash
cd workspace/memory
python memory_api.py
# 服务运行在 http://127.0.0.1:8000
```

### 触发新陈代谢

```bash
# 直接运行
python scripts/run_metabolism.py

# 干运行（不执行变更）
python scripts/run_metabolism.py --dry-run
```

### 定时任务配置

```bash
# 每天凌晨 3:00 执行
0 3 * * * cd /home/andy/tech_tools/openclaw && python3 workspace/memory/scripts/run_metabolism.py >> /var/log/openclaw_metabolism.log 2>&1
```

## API 端点

```
POST /api/memory/write     # 写入记忆
POST /api/memory/search    # 混合搜索
POST /api/memory/metabolism # 触发新陈代谢
```

## 目录结构

```
memory/
├── memory_metabolism.py      # 新陈代谢核心
├── memory_search.py          # 混合搜索引擎
├── memory_api.py             # FastAPI 服务
├── db_wrapper.py             # 数据库封装
├── schema.sql                # 数据库 schema
├── scripts/
│   ├── run_metabolism.py     # 定时任务入口
│   └── test_metabolism_dreaming.py  # 集成测试
└── .dreams/                  # Dreaming 输出（可选）
    └── YYYY-MM-DD/
        ├── deep.json
        ├── light.json
        └── rem.json
```

## 测试

```bash
python scripts/test_metabolism_dreaming.py
```

## License

MIT
