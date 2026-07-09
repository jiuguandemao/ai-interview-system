# 安全与上传前检查

## 不能上传 GitHub 的内容

- `.env`
- 真实 API Key、JWT Secret、数据库密码
- 用户简历、JD、报告、上传文件
- 本地虚拟环境：`.venv/`、`.verify_deps/`
- 缓存：`.pytest_cache/`、`__pycache__/`
- 数据库文件：`*.db`、`*.sqlite`
- 日志：`*.log`

## 本地检查命令

```powershell
git status --short
git check-ignore -v .env
git check-ignore -v .verify_deps
git check-ignore -v data/uploads
git check-ignore -v data/reports
```

确认 `.env`、缓存和上传文件都被 ignore。

## 敏感词扫描

```powershell
git grep -n -i "api_key\\|secret\\|token\\|password" -- . ":(exclude).env.example" ":(exclude)docs/SECURITY_CHECKLIST.md"
```

出现 `.env.example` 里的占位字段是正常的；出现真实 Key、真实 token 或真实密码必须删除并轮换。

## GitHub 页面建议

仓库 Description：

```text
AI-Interview: 基于 FastAPI + pgvector RAG + LangGraph + Celery 的智能模拟面试系统
```

Topics：

```text
ai-agent, rag, langgraph, langchain, fastapi, pgvector, celery, redis, postgresql, llm, interview-preparation, python
```
