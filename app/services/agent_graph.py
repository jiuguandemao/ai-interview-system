from typing import Any, Literal, TypedDict
import uuid

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.schemas import AnswerScore
from app.services.llm import LLMService
from app.services.rag import RAGService


class InterviewState(TypedDict, total=False):
    phase: Literal["start", "answer"]
    user_id: str
    profile: dict
    jd: dict
    answered_count: int
    context: list[dict]
    question: str
    question_type: str
    expected_points: list[str]
    source_chunk_ids: list[str]
    answer: str
    score: dict
    next_question: str


def build_interview_graph(db: Session, llm: LLMService | None = None, rag: RAGService | None = None):
    llm_service = llm or LLMService()
    rag_service = rag or RAGService()

    def retrieve_context(state: InterviewState) -> dict[str, Any]:
        required = state.get("jd", {}).get("required_skills", [])
        interview_points = state.get("profile", {}).get("interview_points", [])
        query = " ".join(required[:8] + interview_points[:5]) or "项目技术难点"
        contexts = rag_service.retrieve(
            db,
            user_id=uuid.UUID(state["user_id"]),
            query=query,
            top_k=5,
            source_types=["resume", "jd", "question_bank"],
        )
        return {"context": contexts}

    def generate_question(state: InterviewState) -> dict[str, Any]:
        result = llm_service.generate_question(
            state.get("profile", {}), state.get("jd", {}), state.get("context", []),
            state.get("answered_count", 0),
        )
        return {
            "question": result.question,
            "question_type": result.question_type,
            "expected_points": result.expected_points,
            "source_chunk_ids": result.source_chunk_ids,
        }

    def score_answer(state: InterviewState) -> dict[str, Any]:
        score = llm_service.score_answer(
            state["question"], state["answer"], state.get("expected_points", [])
        )
        return {"score": score.model_dump()}

    def route_after_score(state: InterviewState) -> Literal["followup", "next_question"]:
        return "followup" if state["score"]["needs_followup"] else "next_question"

    def generate_followup(state: InterviewState) -> dict[str, Any]:
        score = AnswerScore.model_validate(state["score"])
        question = llm_service.generate_followup(state["question"], state["answer"], score)
        return {"next_question": question, "question_type": "followup"}

    def generate_next_question(state: InterviewState) -> dict[str, Any]:
        result = llm_service.generate_question(
            state.get("profile", {}), state.get("jd", {}), state.get("context", []),
            state.get("answered_count", 0) + 1,
        )
        return {
            "next_question": result.question,
            "question_type": result.question_type,
            "expected_points": result.expected_points,
            "source_chunk_ids": result.source_chunk_ids,
        }

    def route_phase(state: InterviewState) -> Literal["retrieve", "score"]:
        return "retrieve" if state.get("phase") == "start" else "score"

    graph = StateGraph(InterviewState)
    graph.add_node("retrieve_node", retrieve_context)
    graph.add_node("question_node", generate_question)
    graph.add_node("score_node", score_answer)
    graph.add_node("followup_node", generate_followup)
    graph.add_node("next_question_node", generate_next_question)
    graph.add_conditional_edges(
        START, route_phase, {"retrieve": "retrieve_node", "score": "score_node"}
    )
    graph.add_edge("retrieve_node", "question_node")
    graph.add_edge("question_node", END)
    graph.add_conditional_edges(
        "score_node",
        route_after_score,
        {"followup": "followup_node", "next_question": "next_question_node"},
    )
    graph.add_edge("followup_node", END)
    graph.add_edge("next_question_node", END)
    return graph.compile()
