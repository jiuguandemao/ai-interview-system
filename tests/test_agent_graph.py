import uuid

from app.schemas import AnswerScore, GeneratedQuestion
from app.services.agent_graph import build_interview_graph


class FakeRAG:
    def retrieve(self, *args, **kwargs):
        return [
            {
                "chunk_id": "chunk-1",
                "content": "候选人使用 FastAPI 构建后端接口",
                "title": "resume",
                "source_type": "resume",
                "similarity": 0.9,
            }
        ]


class FakeLLM:
    def __init__(self, needs_followup: bool):
        self.needs_followup = needs_followup

    def generate_question(self, *args, **kwargs):
        return GeneratedQuestion(
            question="请说明 FastAPI 在项目中的用途",
            question_type="project",
            why_asked="验证真实使用",
            expected_points=["接口", "鉴权"],
            source_chunk_ids=["chunk-1"],
        )

    def score_answer(self, *args, **kwargs):
        return AnswerScore(
            technical_accuracy=3,
            project_depth=3,
            communication=3,
            job_fit=3,
            total=12,
            evidence=["使用 FastAPI"],
            missing_points=["鉴权"],
            feedback="需要补充实现细节",
            needs_followup=self.needs_followup,
        )

    def generate_followup(self, *args, **kwargs):
        return "JWT 鉴权具体怎么实现？"


def test_start_phase_retrieves_context_then_generates_question():
    graph = build_interview_graph(None, FakeLLM(True), FakeRAG())
    state = graph.invoke(
        {"phase": "start", "user_id": str(uuid.uuid4()), "profile": {}, "jd": {}, "answered_count": 0}
    )
    assert state["question"] == "请说明 FastAPI 在项目中的用途"
    assert state["source_chunk_ids"] == ["chunk-1"]


def test_answer_phase_routes_to_followup_when_evidence_is_missing():
    graph = build_interview_graph(None, FakeLLM(True), FakeRAG())
    state = graph.invoke(
        {
            "phase": "answer",
            "user_id": str(uuid.uuid4()),
            "profile": {},
            "jd": {},
            "question": "请说明 FastAPI 在项目中的用途",
            "answer": "我用过 FastAPI",
            "expected_points": ["接口", "鉴权"],
        }
    )
    assert state["next_question"] == "JWT 鉴权具体怎么实现？"
    assert state["question_type"] == "followup"
