from app.schemas import JDRequirements, ResumeProfile
from app.services.matching import calculate_match


def test_required_skill_coverage_has_highest_weight():
    profile = ResumeProfile(skills=["Python", "FastAPI", "Redis"])
    jd = JDRequirements(
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Redis", "Docker"],
    )
    result = calculate_match(profile, jd)
    assert result.required_coverage == 0.667
    assert "postgresql" in result.missing_required_skills
    assert "redis" in result.matched_skills


def test_empty_skill_requirements_do_not_divide_by_zero():
    result = calculate_match(ResumeProfile(), JDRequirements())
    assert result.score == 100
