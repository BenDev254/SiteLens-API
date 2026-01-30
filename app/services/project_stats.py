from typing import List
from app.models.assessment_result import AssessmentResult
from app.services.gemini_classifier import extract_gemini_text, classify 



def compute_stats(assessments: List[AssessmentResult]) -> dict:
    total = len(assessments)
    scores = [a.score for a in assessments if a.score is not None]


    classified = [
        classify(extract_gemini_text(a.gemini_response))
        for a in assessments
    ]


    return {
        "totalAssessments": total,
        "criticalRisks": sum(1 for c in classified if c["critical"]),
        "averageSafetyScore": (
            round(sum(scores) / len(scores), 2) if scores else None
        ),
        "complianceRate":(
            round(
                100 * sum(1 for c in classified if c["complaint"]) / total,
                2
            ) if total > 0 else None
        )
    }