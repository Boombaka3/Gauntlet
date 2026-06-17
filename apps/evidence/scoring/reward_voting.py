# apps/evidence/scoring/reward_voting.py
import logging
from collections import Counter
from apps.evidence.models import Paper, AnswerRecord, RewardScore
from apps.evidence.scoring.question_answerer import answer_question
from apps.evidence.scoring.faithfulness import score_faithfulness

logger = logging.getLogger(__name__)


def compute_reward(paper: Paper,
                   question: str,
                   n_samples: int = 3) -> tuple[AnswerRecord, RewardScore]:
    """
    Run answer_question N times on the same paper+question.
    Majority answer wins. Consistency = majority_count / N.
    Faithfulness scores the winning answer against its source sentence.
    Returns unsaved (AnswerRecord, RewardScore).
    """
    answers = []
    last_record = None

    for _ in range(n_samples):
        try:
            record = answer_question(paper, question)
            answers.append(record.answer)
            last_record = record
        except Exception as e:
            logger.error(f"answer_question failed in voting loop: {e}")
            answers.append("maybe")

    counts = Counter(answers)
    majority_answer, majority_count = counts.most_common(1)[0]
    consistency = majority_count / n_samples

    if last_record is None:
        last_record = AnswerRecord(
            paper=paper,
            question=question,
            answer="maybe",
            reasoning="all runs failed",
            source_sentence="",
            error_types=[],
        )

    last_record.answer = majority_answer

    faithfulness_result = None
    if last_record.source_sentence and last_record.reasoning:
        try:
            faithfulness_result = score_faithfulness(
                last_record.reasoning,
                last_record.source_sentence,
            )
        except Exception as e:
            logger.error(f"Faithfulness scoring failed: {e}")

    faithfulness_score = (
        faithfulness_result.get("faithfulness_score")
        if faithfulness_result else None
    )

    if faithfulness_result and faithfulness_result.get("error_types"):
        existing = set(last_record.error_types or [])
        existing.update(faithfulness_result["error_types"])
        last_record.error_types = list(existing)

    if faithfulness_score is not None:
        final_confidence = 0.7 * consistency + 0.3 * faithfulness_score
    else:
        final_confidence = consistency

    reward = RewardScore(
        consistency_score=consistency,
        nli_score=None,
        faithfulness_score=faithfulness_score,
        final_confidence=final_confidence,
        n_samples=n_samples,
    )

    return last_record, reward
