from statistics import mean


def build_report(score_items: list[dict], match_result: dict) -> dict:
    if not score_items:
        return {
            "overall_score": 0.0,
            "dimension_scores": {},
            "strengths": [],
            "weaknesses": ["尚无有效回答"],
            "next_actions": ["完成至少一轮问答"],
        }
    dimensions = ["technical_accuracy", "project_depth", "communication", "job_fit"]
    averages = {name: round(mean(float(item[name]) for item in score_items), 2) for name in dimensions}
    overall = round(mean(float(item["total"]) for item in score_items) / 20 * 100, 1)
    weaknesses = sorted(averages, key=lambda name: averages[name])[:2]
    return {
        "overall_score": overall,
        "dimension_scores": averages,
        "match_score": match_result.get("score", 0),
        "strengths": [name for name, value in averages.items() if value >= 4],
        "weaknesses": weaknesses,
        "missing_skills": match_result.get("missing_required_skills", []),
        "next_actions": [f"针对 {name} 补充 STAR 案例并重新录答" for name in weaknesses],
    }
