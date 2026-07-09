# API 调用示例

以下示例可直接在 Swagger 页面执行：http://localhost:8000/docs

## 1. 注册

`POST /api/v1/auth/register`

```json
{
  "email": "demo@example.com",
  "username": "demo_user",
  "password": "ChangeMe123!"
}
```

## 2. 登录

`POST /api/v1/auth/token`

表单字段：

```text
username=demo_user
password=ChangeMe123!
```

复制返回的 `access_token`，点击 Swagger 右上角 `Authorize`，填入 token。

## 3. 上传简历

`POST /api/v1/resumes`

上传 PDF、DOCX、TXT 或 Markdown 文件。返回：

```json
{
  "resume_id": "...",
  "job_id": "...",
  "status": "pending"
}
```

## 4. 查询任务

`GET /api/v1/jobs/{job_id}`

等待：

```json
{
  "status": "success",
  "progress": 100
}
```

## 5. 创建 JD

`POST /api/v1/job-descriptions`

表单字段：

```text
title=AI 应用开发工程师
text=熟悉 Python、FastAPI、PostgreSQL、Redis、Celery、RAG、LangGraph 和 Docker
```

## 6. 创建面试

`POST /api/v1/interviews`

```json
{
  "resume_id": "你的 resume_id",
  "jd_id": "你的 jd_id",
  "max_questions": 3
}
```

## 7. 提交回答

`POST /api/v1/interviews/{session_id}/answers`

```json
{
  "answer": "我使用 FastAPI 提供 REST API，用 JWT 完成登录鉴权。简历解析、Embedding 和 LLM 调用交给 Celery Worker，Redis 负责消息投递，PostgreSQL 保存业务状态和向量。"
}
```

## 8. 查看报告

`GET /api/v1/interviews/{session_id}/report`

报告包含总分、四维评分、薄弱点和下一步复习建议。
