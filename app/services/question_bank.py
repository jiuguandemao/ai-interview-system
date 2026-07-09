import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document
from app.services.rag import RAGService


DEFAULT_QUESTIONS = [
    "Python 的 GIL 解决了什么问题，对 CPU 密集型和 IO 密集型任务分别有什么影响？",
    "FastAPI 的依赖注入如何实现鉴权、数据库会话和公共参数复用？",
    "JWT 登录流程是什么，访问令牌泄漏后应如何控制风险？",
    "PostgreSQL B-Tree 索引何时有效，为什么对索引列做函数运算可能失效？",
    "Redis 缓存穿透、击穿和雪崩分别是什么，如何治理？",
    "Celery 中 broker、worker、result backend 分别负责什么？",
    "异步任务怎样做到幂等，重试为什么可能产生重复数据？",
    "RAG 从文档切块到最终回答经过哪些步骤，如何评估召回质量？",
    "向量相似度高是否等于答案相关，为什么还需要元数据过滤和重排？",
    "LangGraph 的 State、Node、Edge 各自是什么，为什么适合有分支的 Agent？",
    "结构化输出为什么仍需 Pydantic 校验，模型返回非法 JSON 时怎样兜底？",
    "Docker Compose 中 depends_on 和 healthcheck 有什么区别？",
    "如何设计日志字段，才能串起一次 API 请求、Celery 任务和模型调用？",
    "简历属于敏感数据，上传、存储、日志和模型调用分别要做哪些保护？",
    "如何用本地样例和人工抽检评估岗位匹配与面试评分，而不夸大指标？",
]


def ensure_default_question_bank(db: Session, user_id: uuid.UUID) -> None:
    source_id = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-interview-question-bank:{user_id}")
    exists = db.scalar(
        select(Document.id).where(
            Document.user_id == user_id,
            Document.source_type == "question_bank",
            Document.source_id == source_id,
        )
    )
    if exists:
        return
    text = "\n\n".join(f"题目 {index + 1}：{question}" for index, question in enumerate(DEFAULT_QUESTIONS))
    RAGService().index_document(
        db,
        user_id=user_id,
        source_type="question_bank",
        source_id=source_id,
        title="内置高频题库",
        text=text,
        metadata={"version": "1.0"},
    )
