# 面试答辩手册

## 60 秒项目介绍

AI-Interview 是一个面向 AI 应用开发工程师求职训练的智能模拟面试系统。用户上传简历和目标岗位 JD 后，系统先做文件解析和 LLM 结构化抽取，再用可解释规则计算岗位匹配度。简历、JD 和内置题库会切块并写入 PostgreSQL pgvector，出题前按当前用户权限做 RAG 检索。面试流程用 LangGraph 编排检索、出题、四维评分、追问和下一题分支。解析、向量化、模型调用和报告生成由 Celery + Redis 异步执行，FastAPI 只负责提交任务和查询状态。整个项目通过 Docker Compose 一键启动，重点展示了 AI 能力如何落到一个可追踪、可恢复、可部署的后端系统中。

## 面试官常问

### 1. 这是不是简单套壳？

不是。模型只是其中一个组件。系统还包含文件解析、结构化校验、岗位匹配规则、pgvector RAG、LangGraph 状态图、Celery 异步任务、PostgreSQL 持久化、JWT 权限隔离和 Docker 部署。直接问大模型没有任务状态、权限过滤、引用来源和失败恢复。

### 2. 为什么用 pgvector？

当前项目向量规模不大，但业务关系和权限过滤很重要。pgvector 能把业务数据和向量放在 PostgreSQL 中统一管理，`user_id` 过滤、事务和备份都更简单。规模扩大或需要分布式向量检索时，再评估 Qdrant/Milvus。

### 3. LangGraph 在项目里做了什么？

它不是为了堆技术名词，而是负责有状态、多分支流程。`phase=start` 时执行检索和出题；`phase=answer` 时先评分，再根据 `needs_followup` 选择追问或下一题。这样可以限制节点、成本和最大轮数。

### 4. 为什么需要 Celery？

文件解析、Embedding 和 LLM 调用可能耗时几十秒。API 同步等待会阻塞请求，也容易超时。Celery 把任务交给 Worker，API 返回 job_id，前端轮询状态。失败时 AsyncJob 里有 error_message。

### 5. 如何避免越权？

JWT 只证明用户身份。每次查询资源时还要检查 `resource.user_id == current_user.id`。RAG 检索也在 SQL 排序前按 `user_id` 过滤，不能先全库检索再删除无权结果。

### 6. 如何解释项目指标？

不能说线上准确率。正确口径是：可以准备 20-50 组本地简历/JD 样例，人工标注岗位匹配和技能缺口，再计算匹配准确率、缺口 precision/recall。RAG 评估单独用 Recall@5、MRR 和人工抽检。

### 7. 项目最大不足是什么？

当前是本地工程化原型。生产还需要补 OCR、对象存储、Celery 完整幂等、死信队列、Outbox、监控告警、成本控制、压测和 CI/CD。

## 回答主线

回答项目时按真实数据流讲：

1. 用户登录后上传简历和 JD。
2. API 校验、保存文件并创建 AsyncJob。
3. Celery Worker 解析文本，LLM 结构化抽取。
4. 文本切块、Embedding、写入 pgvector。
5. 创建面试时做岗位匹配和 RAG 检索。
6. LangGraph 生成问题，用户回答后四维评分。
7. 根据缺失点追问，达到轮数后生成报告。
