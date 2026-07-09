# GitHub 上传指南

## 1. 在 GitHub 新建仓库

建议仓库名：

```text
ai-interview-system
```

创建时不要勾选 README、.gitignore、License，因为本地已经准备好了。

## 2. 初始化并首次提交

```powershell
cd "D:\桌面\自己课题\agent\AI-Interview智能模拟面试系统实战\ai-interview-system"
git init
git branch -M main
git status
git add .
git status
git commit -m "feat: build ai interview agent system"
```

## 3. 关联远程仓库

把下面地址换成你的 GitHub 用户名：

```powershell
git remote add origin https://github.com/<your-name>/ai-interview-system.git
git remote -v
```

## 4. 推送

```powershell
git push -u origin main
```

如果弹出登录窗口，按 GitHub 提示登录即可。

## 5. 更新仓库页面

进入 GitHub 仓库主页，右侧 About 区域填写：

Description：

```text
AI-Interview: 基于 FastAPI + pgvector RAG + LangGraph + Celery 的智能模拟面试系统
```

Topics：

```text
ai-agent
rag
langgraph
langchain
fastapi
pgvector
celery
redis
postgresql
llm
interview-preparation
python
```

## 6. 后续更新

```powershell
git status
git add .
git commit -m "docs: improve project documentation"
git push origin main
```
