"""Insert and retrieve one private document to verify the pgvector pipeline."""

import uuid

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password
from app.services.rag import RAGService


DEMO_EMAIL = "rag-smoke@example.com"


def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if not user:
            user = User(
                email=DEMO_EMAIL,
                username="rag_smoke_user",
                password_hash=hash_password("ChangeMe123!"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        source_id = uuid.uuid5(uuid.NAMESPACE_URL, "rag-smoke-document")
        service = RAGService()
        service.index_document(
            db,
            user_id=user.id,
            source_type="question_bank",
            source_id=source_id,
            title="RAG 冒烟测试材料",
            text=(
                "我在项目中使用 FastAPI 提供 REST API，使用 JWT 完成登录鉴权。\n\n"
                "耗时的简历解析和大模型调用交给 Celery Worker，Redis 作为消息代理。\n\n"
                "简历、岗位 JD 和题库切块后生成向量，并保存到 PostgreSQL 的 pgvector。"
            ),
            metadata={"purpose": "smoke_test"},
        )
        results = service.retrieve(
            db,
            user_id=user.id,
            query="项目如何处理耗时的大模型任务？",
            top_k=3,
            source_types=["question_bank"],
        )
        if not results:
            raise RuntimeError("没有召回结果，请检查文档切块、向量和 user_id 过滤")
        print("RAG_SMOKE_OK")
        for item in results:
            print(item["similarity"], item["title"], item["content"][:100])


if __name__ == "__main__":
    main()
