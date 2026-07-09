"""Example offline evaluation for a manually labelled resume/JD set."""

import json
from pathlib import Path

from app.schemas import JDRequirements, ResumeProfile
from app.services.matching import calculate_match


def evaluate(dataset_path: Path, threshold: float = 60.0) -> dict:
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    correct = 0
    details = []
    for case in cases:
        result = calculate_match(
            ResumeProfile.model_validate(case["resume"]),
            JDRequirements.model_validate(case["jd"]),
        )
        predicted = result.score >= threshold
        expected = bool(case["human_match"])
        correct += int(predicted == expected)
        details.append({"id": case["id"], "score": result.score, "predicted": predicted, "expected": expected})
    return {
        "sample_count": len(cases),
        "accuracy": round(correct / len(cases), 4) if cases else 0,
        "threshold": threshold,
        "details": details,
    }


if __name__ == "__main__":
    source = Path("evaluation/matching_cases.json")
    print(json.dumps(evaluate(source), ensure_ascii=False, indent=2))
