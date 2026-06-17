# tests/evidence/test_models.py
import pytest
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def test_analysis_job_default_status(db):
    with schema_context("demo"):
        from apps.evidence.models import AnalysisJob
        job = AnalysisJob.objects.create()
        assert job.status == "PENDING"
        assert job.n_samples == 3


def test_analysis_job_str(job):
    with schema_context("demo"):
        assert "PENDING" in str(job)


def test_paper_fk_to_job(paper_a, job):
    with schema_context("demo"):
        assert paper_a.job_id == job.id
        assert paper_a.title == "Paper A"


def test_claim_fk_to_paper(claim_a, paper_a):
    with schema_context("demo"):
        assert claim_a.paper_id == paper_a.id
        assert claim_a.claim_type == "causal"
        assert claim_a.text == "Drug X reduces tumor size by 40%."


def test_answer_record_default(paper_a):
    with schema_context("demo"):
        from apps.evidence.models import AnswerRecord
        ar = AnswerRecord.objects.create(
            paper=paper_a,
            question="Does Drug X reduce tumor size?",
            answer="yes",
            reasoning="The abstract states a 40% reduction.",
            source_sentence="Drug X reduces tumor size by 40%.",
        )
        assert ar.answer == "yes"
        assert ar.error_types == []
        ar.delete()


def test_answer_choices(paper_a):
    with schema_context("demo"):
        from apps.evidence.models import AnswerRecord
        for answer in ("yes", "no", "maybe"):
            ar = AnswerRecord(
                paper=paper_a,
                question="Test?",
                answer=answer,
            )
            ar.full_clean()


def test_reward_score_linked_to_answer(paper_a):
    with schema_context("demo"):
        from apps.evidence.models import AnswerRecord, RewardScore
        ar = AnswerRecord.objects.create(
            paper=paper_a,
            question="Test?",
            answer="maybe",
        )
        r = RewardScore.objects.create(
            answer_record=ar,
            consistency_score=0.67,
            final_confidence=0.67,
        )
        assert r.answer_record_id == ar.id
        r.delete()
        ar.delete()


def test_reward_score_all_nullable(paper_a):
    with schema_context("demo"):
        from apps.evidence.models import AnswerRecord, RewardScore
        ar = AnswerRecord.objects.create(
            paper=paper_a,
            question="Test?",
            answer="maybe",
        )
        r = RewardScore.objects.create(answer_record=ar)
        assert r.consistency_score is None
        assert r.nli_score is None
        assert r.faithfulness_score is None
        assert r.final_confidence is None
        r.delete()
        ar.delete()


def test_reward_score_one_to_one(paper_a):
    with schema_context("demo"):
        from apps.evidence.models import AnswerRecord, RewardScore
        ar = AnswerRecord.objects.create(
            paper=paper_a,
            question="Test?",
            answer="yes",
        )
        r = RewardScore.objects.create(
            answer_record=ar,
            consistency_score=1.0,
            faithfulness_score=0.9,
            final_confidence=0.97,
            n_samples=3,
        )
        refreshed = AnswerRecord.objects.select_related("reward").get(pk=ar.pk)
        assert refreshed.reward.pk == r.pk
        r.delete()
        ar.delete()
