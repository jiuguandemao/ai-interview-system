# 架构设计

AI-Interview 按“入口层、业务层、AI 能力层、异步任务层、数据层”拆分，目标是让大模型能力进入可追踪、可恢复、可解释的后端系统。

## 总体链路

```text
用户浏览器
  -> Streamlit 前端
  -> FastAPI API
  -> PostgreSQL 创建业务记录和 AsyncJob
  -> Redis 投递任务
  -> Celery Worker 执行解析、向量化、LLM、LangGraph
  -> PostgreSQL 保存结果
  -> 前端轮询任务状态并展示报告
```

## 数据模型

| 表 | 职责 |
| --- | --- |
| users | 用户账号、密码哈希、启用状态 |
| resumes | 简历文件、原文、结构化画像、解析状态 |
| job_descriptions | JD 原文、岗位结构化要求、解析状态 |
| documents | RAG 文档元数据 |
| document_chunks | 文档片段、向量、来源、权限字段 |
| async_jobs | 后台任务状态、进度、结果和错误 |
| interview_sessions | 面试会话、当前问题、匹配结果、Agent 状态 |
| interview_messages | 面试官问题、候选人回答、评分结果 |
| interview_reports | 最终报告 |
| llm_call_logs | 模型调用审计预留表 |

## RAG 流程

```text
原文
  -> 文本清洗
  -> split_text 切块
  -> EmbeddingService 生成向量
  -> document_chunks.embedding

用户画像 + JD 要求
  -> 生成检索 query
  -> user_id/source_type 过滤
  -> pgvector cosine distance 排序
  -> top-k chunk 进入出题 Prompt
```

关键点：权限过滤必须在 SQL 检索前完成，不能检索全库后再用 Python 过滤。

## LangGraph 流程

```text
phase=start:
  START -> retrieve_node -> question_node -> END

phase=answer:
  START -> score_node -> followup_node 或 next_question_node -> END
```

LangGraph 负责控制节点和分支，模型只在节点内部生成问题、评分和追问。系统不会让模型自由决定是否访问数据库或执行工具。

## 为什么选这些技术

| 技术 | 选择原因 | 替代方案 |
| --- | --- | --- |
| FastAPI | 类型友好、Swagger 自动生成、适合 Python AI 后端 | Django、Flask |
| PostgreSQL + pgvector | 业务数据和向量数据统一管理，权限过滤简单 | MySQL + Qdrant/Milvus |
| Celery + Redis | 耗时任务异步化，Worker 可独立扩容 | FastAPI BackgroundTasks、RQ |
| LangGraph | 多节点、有状态、有分支的 Agent 流程更清晰 | LangChain Chain、自写 if/else |
| Streamlit | 快速做可操作演示，降低前端成本 | React/Vue |
