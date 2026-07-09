# 部署指南

## 1. 本地启动

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
```

访问：

- 前端：http://localhost:8501
- API：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 2. 常用命令

```powershell
docker compose logs -f api worker
docker compose run --rm api pytest -q
docker compose run --rm api python scripts/smoke_rag.py
docker compose down
```

清空数据库和 Redis 数据卷：

```powershell
docker compose down -v
```

注意：`down -v` 会删除本地数据库数据，只适合开发环境。

## 3. 数据库迁移

```powershell
docker compose run --rm migrate alembic upgrade head
docker compose run --rm migrate alembic current
```

进入数据库检查：

```powershell
docker compose exec db psql -U ai_interview -d ai_interview
```

```sql
\dx
\dt
SELECT count(*) FROM document_chunks WHERE embedding IS NOT NULL;
```

## 4. 接入真实模型

`.env` 示例：

```dotenv
LLM_MOCK=false
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
EMBEDDING_BACKEND=sentence_transformers
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

切换真实 Embedding 后重新上传文档，避免 hash 调试向量与真实向量混用。

## 5. 生产化差距

当前 Compose 适合本地演示和单机原型。生产环境建议补：

- Nginx/HTTPS
- db/redis 内网访问，不暴露公网端口
- Secret Manager 管理密钥
- S3/MinIO 保存上传文件
- Prometheus + OpenTelemetry + Langfuse/LangSmith
- Worker 队列拆分、幂等锁、死信队列
- GitHub Actions 构建镜像和自动测试
