# apps/evidence/scoring/reward_voting.py
from collections import Counter

from apps.evidence.models import Claim, ConflictPair, RewardScore
from apps.evidence.scoring.conflict_judge import judge_conflict
from apps.evidence.scoring.faithfulness import score_faithfulness


def compute_reward(
    claim_a: Claim,
    claim_b: Claim,
    n_samples: int = 3,
) -> tuple[ConflictPair, RewardScore]:
    verdicts = []
    last_pair = None

    for _ in range(n_samples):
        try:
            pair = judge_conflict(claim_a, claim_b)
            verdicts.append(pair.verdict)
            last_pair = pair
        except Exception:
            verdicts.append("NEI")

    counts = Counter(verdicts)
    majority_verdict, majority_count = counts.most_common(1)[0]
    consistency = majority_count / n_samples

    if last_pair is None:
        last_pair = ConflictPair(
            claim_a=claim_a,
            claim_b=claim_b,
            verdict="NEI",
            conflict_type="none",
            severity=1,
            reasoning="all runs failed",
            error_types=[],
        )
    last_pair.verdict = majority_verdict

    fa = score_faithfulness(claim_a.text, claim_a.source_sentence)
    fb = score_faithfulness(claim_b.text, claim_b.source_sentence)

    scores = [
        s
        for s in [fa.get("faithfulness_score"), fb.get("faithfulness_score")]
        if s is not None
    ]
    faithfulness = sum(scores) / len(scores) if scores else None

    error_types = list(set(fa.get("error_types", []) + fb.get("error_types", [])))
    last_pair.error_types = error_types

    if faithfulness is not None:
        final_confidence = 0.7 * consistency + 0.3 * faithfulness
    else:
        final_confidence = consistency

    reward = RewardScore(
        consistency_score=consistency,
        nli_score=None,
        faithfulness_score=faithfulness,
        final_confidence=final_confidence,
        n_samples=n_samples,
    )
    return last_pair, reward
