# apps/evidence/tasks/answer_questions.py
import logging
from celery import shared_task
from apps.evidence.models import AnalysisJob, Paper, Claim
from apps.evidence.scoring.reward_voting import compute_reward

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def answer_paper_questions(self, paper_id: int, n_samples: int = 3):
    """
    For each claim extracted from a paper, ask it as a yes/no/maybe question
    against the paper's own abstract. Saves AnswerRecord + RewardScore.
    """
    try:
        paper = Paper.objects.get(id=paper_id)
        claims = list(paper.claims.all())

        if not claims:
            logger.warning(f"Paper {paper_id}: no claims to answer")
            return

        answered = 0
        for claim in claims:
            if not claim.text.strip():
                continue
            try:
                question = _claim_to_question(claim.text)
                answer_record, reward = compute_reward(
                    paper, question, n_samples=n_samples
                )
                answer_record.gold_label = ""
                answer_record.save()
                reward.answer_record = answer_record
                reward.save()
                answered += 1
            except Exception as e:
                logger.error(
                    f"Failed to answer question for claim {claim.id}: {e}"
                )

        logger.info(
            f"Paper {paper_id}: answered {answered}/{len(claims)} claims"
        )

    except Exception as e:
        logger.error(f"answer_paper_questions failed for paper {paper_id}: {e}")


def _claim_to_question(claim_text: str) -> str:
    """
    Convert a declarative claim into a yes/no research question.
    Simple heuristic: prepend "Does the evidence support that" and
    lowercase the claim. Works well enough for biomedical claims.
    """
    text = claim_text.strip().rstrip(".")
    text = text[0].lower() + text[1:] if text else text
    return f"Does the evidence support that {text}?"
