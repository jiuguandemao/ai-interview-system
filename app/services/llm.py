import json
import re

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.schemas import AnswerScore, GeneratedQuestion, JDRequirements, ResumeProfile


KNOWN_SKILLS = [
    "Python", "FastAPI", "Django", "MySQL", "PostgreSQL", "Redis", "Celery",
    "Docker", "LangChain", "LangGraph", "RAG", "pgvector",
]


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    def _chat(self) -> ChatOpenAI:
        if self._client is None:
            if not self.settings.llm_api_key:
                raise RuntimeError("LLM_API_KEY 为空，请设置密钥或保持 LLM_MOCK=true")
            self._client = ChatOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                temperature=self.settings.llm_temperature,
                timeout=60,
                max_retries=2,
            )
        return self._client

    def extract_resume(self, text: str) -> ResumeProfile:
        if self.settings.llm_mock:
            skills = [skill for skill in KNOWN_SKILLS if skill.lower() in text.lower()]
            return ResumeProfile(
                name="本地样例候选人",
                skills=skills,
                projects=[{"name": "简历中的项目", "description": text[:500]}],
                interview_points=[f"请解释 {skill} 在项目中的具体使用" for skill in skills[:5]],
            )
        prompt = f"""你是严格的信息抽取器。只能依据简历原文，不得补写不存在的经历。
缺失字段返回空列表或空字符串。项目必须包含 name、responsibilities、technologies、metrics。

简历原文：
{text[:30000]}
"""
        return self._chat().with_structured_output(ResumeProfile).invoke(prompt)

    def extract_jd(self, text: str, title: str = "") -> JDRequirements:
        if self.settings.llm_mock:
            skills = [skill for skill in KNOWN_SKILLS if skill.lower() in text.lower()]
            midpoint = max(1, len(skills) // 2)
            return JDRequirements(
                title=title or "AI 应用开发工程师",
                required_skills=skills[:midpoint],
                preferred_skills=skills[midpoint:],
                responsibilities=[line.strip() for line in text.splitlines() if line.strip()][:5],
            )
        prompt = f"""把岗位描述抽取为固定结构。required_skills 只放明确必备项，
preferred_skills 放加分项；不要把公司福利当技能。岗位名称提示：{title}

岗位原文：
{text[:30000]}
"""
        return self._chat().with_structured_output(JDRequirements).invoke(prompt)

    def generate_question(
        self, profile: dict, jd: dict, contexts: list[dict], answered_count: int = 0
    ) -> GeneratedQuestion:
        if self.settings.llm_mock:
            skills = jd.get("required_skills") or profile.get("skills") or ["Python"]
            skill = skills[answered_count % len(skills)]
            return GeneratedQuestion(
                question=f"请结合你的项目说明 {skill} 解决了什么问题，为什么选择它？",
                question_type="project",
                why_asked=f"该问题用于验证候选人是否真正使用过 {skill}",
                expected_points=["业务问题", "技术选择", "实现过程", "异常处理", "最终效果"],
                source_chunk_ids=[item["chunk_id"] for item in contexts[:3]],
            )
        context_text = "\n\n".join(f"[{item['chunk_id']}] {item['content']}" for item in contexts)
        prompt = f"""你是技术面试官。根据候选人画像、岗位要求和检索证据生成一个问题。
问题必须能验证真实项目能力，禁止询问年龄、婚育等敏感信息。引用 ID 必须来自证据。
已回答题数：{answered_count}
候选人画像：{json.dumps(profile, ensure_ascii=False)}
岗位要求：{json.dumps(jd, ensure_ascii=False)}
检索证据：{context_text}
"""
        return self._chat().with_structured_output(GeneratedQuestion).invoke(prompt)

    def score_answer(self, question: str, answer: str, expected_points: list[str]) -> AnswerScore:
        if self.settings.llm_mock:
            length_score = min(5.0, max(1.0, len(answer) / 80))
            structure_bonus = 0.5 if re.search(r"首先|其次|最后|因为|所以", answer) else 0
            technical = min(5.0, round(length_score + structure_bonus, 1))
            project_depth = min(5.0, round(length_score, 1))
            communication = min(5.0, round(2.0 + structure_bonus + len(answer) / 200, 1))
            job_fit = min(5.0, round((technical + project_depth) / 2, 1))
            total = round(technical + project_depth + communication + job_fit, 1)
            return AnswerScore(
                technical_accuracy=technical,
                project_depth=project_depth,
                communication=communication,
                job_fit=job_fit,
                total=total,
                evidence=[answer[:120]],
                missing_points=[] if len(answer) >= 120 else expected_points[:3],
                feedback="回答覆盖了基本思路，建议补充具体实现、异常场景和量化结果。",
                needs_followup=total < 14 or len(answer) < 120,
            )
        prompt = f"""按 rubric 给回答评分，每项 0-5 分：
1. technical_accuracy：技术事实和因果是否正确；
2. project_depth：是否讲清本人职责、实现细节、难点和取舍；
3. communication：是否结构清楚、结论先行；
4. job_fit：是否回应岗位能力。
必须引用回答中的短句作为 evidence，证据不足时不能给高分。
问题：{question}
期望点：{expected_points}
回答：{answer}
"""
        return self._chat().with_structured_output(AnswerScore).invoke(prompt)

    def generate_followup(self, question: str, answer: str, score: AnswerScore) -> str:
        if self.settings.llm_mock:
            missing = "、".join(score.missing_points[:2]) or "异常处理和效果验证"
            return f"你刚才没有具体说明{missing}，请结合一次真实处理过程展开。"
        prompt = f"""根据原问题、回答和评分，只生成一个最有价值的追问。
追问要针对缺失证据，不能换到无关话题。
原问题：{question}
回答：{answer}
评分：{score.model_dump_json()}
"""
        return str(self._chat().invoke(prompt).content)
