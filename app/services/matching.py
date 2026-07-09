import re

from app.schemas import JDRequirements, MatchResult, ResumeProfile


ALIASES = {
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "pgvector": "pgvector",
    "langgraph": "langgraph",
    "langchain": "langchain",
    "fast api": "fastapi",
    "fastapi": "fastapi",
    "redis": "redis",
    "celery": "celery",
    "python": "python",
}


def normalize_skill(skill: str) -> str:
    value = re.sub(r"[^a-z0-9+#.]+", " ", skill.lower()).strip()
    return ALIASES.get(value, value)


def calculate_match(profile: ResumeProfile, jd: JDRequirements) -> MatchResult:
    resume_skills = {normalize_skill(skill) for skill in profile.skills if normalize_skill(skill)}
    required = {normalize_skill(skill) for skill in jd.required_skills if normalize_skill(skill)}
    preferred = {normalize_skill(skill) for skill in jd.preferred_skills if normalize_skill(skill)}
    matched_required = required & resume_skills
    matched_preferred = preferred & resume_skills
    required_coverage = len(matched_required) / len(required) if required else 1.0
    preferred_coverage = len(matched_preferred) / len(preferred) if preferred else 1.0

    project_text = " ".join(str(project) for project in profile.projects).lower()
    responsibility_hits = sum(
        1 for item in jd.responsibilities if any(word in project_text for word in normalize_skill(item).split())
    )
    project_coverage = responsibility_hits / len(jd.responsibilities) if jd.responsibilities else 1.0
    score = round((required_coverage * 0.6 + preferred_coverage * 0.2 + project_coverage * 0.2) * 100, 1)

    missing_required = sorted(required - resume_skills)
    missing_preferred = sorted(preferred - resume_skills)
    return MatchResult(
        score=score,
        required_coverage=round(required_coverage, 3),
        preferred_coverage=round(preferred_coverage, 3),
        matched_skills=sorted(matched_required | matched_preferred),
        missing_required_skills=missing_required,
        missing_preferred_skills=missing_preferred,
        strengths=[f"已覆盖岗位技能：{skill}" for skill in sorted(matched_required)[:5]],
        risks=[f"必备技能缺口：{skill}" for skill in missing_required[:5]],
        preparation_priority=missing_required + missing_preferred[:3],
    )
