# tests/evidence/test_scoring.py
import pytest
from unittest.mock import patch, MagicMock
from django_tenants.utils import schema_context

pytestmark = pytest.mark.django_db


def _adapter_result(output, error=None):
    from apps.evidence.adapters.base import AdapterResult
    return AdapterResult(output=output, latency_ms=100, token_count=50, error=error)


YES_JSON = ('{"answer":"yes","reasoning":"The abstract confirms this.",'
            '"source_sentence":"Drug X reduces tumor size.","confidence":0.9,'
            '"error_types":[]}')

MAYBE_JSON = ('{"answer":"maybe","reasoning":"Evidence is inconclusive.",'
              '"source_sentence":"Results were mixed.","confidence":0.5,'
              '"error_types":["missing_evidence"]}')

FAITHFULNESS_CLEAN = (
    '{"faithful":true,"faithfulness_score":0.9,'
    '"error_types":[],"reasoning":"claim matches source"}'
)

FAITHFULNESS_OVERGENERALIZED = (
    '{"faithful":false,"faithfulness_score":0.3,'
    '"error_types":["overgeneralization","condition_dropping"],'
    '"reasoning":"claim removes population restriction"}'
)


# ── question_answerer tests ────────────────────────────────────────────────────

def test_question_answerer_returns_yes(paper_a):
    with schema_context("demo"):
        with patch("apps.evidence.scoring.question_answerer.OpenAICompatAdapter") as M:
            M.return_value.complete.return_value = _adapter_result(YES_JSON)
            from apps.evidence.scoring.question_answerer import answer_question
            result = answer_question(paper_a, "Does Drug X reduce tumor size?")
            assert result.answer == "yes"
            assert result.reasoning != ""


def test_question_answerer_handles_fence(paper_a):
    with schema_context("demo"):
        fenced = "```json\n" + YES_JSON + "\n```"
        with patch("apps.evidence.scoring.question_answerer.OpenAICompatAdapter") as M:
            M.return_value.complete.return_value = _adapter_result(fenced)
            from apps.evidence.scoring.question_answerer import answer_question
            result = answer_question(paper_a, "Test?")
            assert result.answer == "yes"


def test_question_answerer_handles_parse_error(paper_a):
    with schema_context("demo"):
        with patch("apps.evidence.scoring.question_answerer.OpenAICompatAdapter") as M:
            M.return_value.complete.return_value = _adapter_result("not json")
            from apps.evidence.scoring.question_answerer import answer_question
            result = answer_question(paper_a, "Test?")
            assert result.answer == "maybe"


def test_question_answerer_adapter_error_falls_back(paper_a):
    with schema_context("demo"):
        with patch("apps.evidence.scoring.question_answerer.OpenAICompatAdapter") as M:
            M.return_value.complete.return_value = _adapter_result("", error="connection refused")
            from apps.evidence.scoring.question_answerer import answer_question
            result = answer_question(paper_a, "Test?")
            assert result.answer == "maybe"


# ── faithfulness tests ─────────────────────────────────────────────────────────

def test_faithfulness_clean_claim():
    with patch("apps.evidence.scoring.faithfulness.OpenAICompatAdapter") as Mock:
        Mock.return_value.complete.return_value = _adapter_result(FAITHFULNESS_CLEAN)
        from apps.evidence.scoring.faithfulness import score_faithfulness
        result = score_faithfulness("Drug X reduces tumors.", "Drug X reduces tumors in mice.")
    assert result["faithful"] is True
    assert result["faithfulness_score"] == pytest.approx(0.9)
    assert result["error_types"] == []


def test_faithfulness_overgeneralized_claim():
    with patch("apps.evidence.scoring.faithfulness.OpenAICompatAdapter") as Mock:
        Mock.return_value.complete.return_value = _adapter_result(FAITHFULNESS_OVERGENERALIZED)
        from apps.evidence.scoring.faithfulness import score_faithfulness
        result = score_faithfulness("Drug X always reduces tumors.", "Drug X reduces tumors in mice.")
    assert result["faithful"] is False
    assert "overgeneralization" in result["error_types"]
    assert "condition_dropping" in result["error_types"]


def test_faithfulness_empty_inputs():
    from apps.evidence.scoring.faithfulness import score_faithfulness
    result = score_faithfulness("", "source text")
    assert result["faithful"] is None
    assert result["faithfulness_score"] is None
    assert result["error_types"] == []


def test_faithfulness_score_clamped():
    out_of_range = (
        '{"faithful":true,"faithfulness_score":1.5,'
        '"error_types":[],"reasoning":"test"}'
    )
    with patch("apps.evidence.scoring.faithfulness.OpenAICompatAdapter") as Mock:
        Mock.return_value.complete.return_value = _adapter_result(out_of_range)
        from apps.evidence.scoring.faithfulness import score_faithfulness
        result = score_faithfulness("claim", "source")
    assert result["faithfulness_score"] == pytest.approx(1.0)


# ── reward_voting tests ────────────────────────────────────────────────────────

def test_reward_voting_consistency(paper_a):
    with schema_context("demo"):
        with patch("apps.evidence.scoring.reward_voting.answer_question") as mock_aq:
            from apps.evidence.models import AnswerRecord
            yes_record = AnswerRecord(
                paper=paper_a, question="Test?", answer="yes",
                reasoning="Evidence supports.", source_sentence="Drug X works.",
            )
            mock_aq.return_value = yes_record
            with patch("apps.evidence.scoring.reward_voting.score_faithfulness",
                       return_value={"faithfulness_score": 0.9, "error_types": []}):
                from apps.evidence.scoring.reward_voting import compute_reward
                answer_record, reward = compute_reward(paper_a, "Test?", n_samples=3)
                assert reward.consistency_score == 1.0
                assert answer_record.answer == "yes"


def test_reward_voting_split(paper_a):
    with schema_context("demo"):
        with patch("apps.evidence.scoring.reward_voting.answer_question") as mock_aq:
            from apps.evidence.models import AnswerRecord
            yes = AnswerRecord(paper=paper_a, question="Test?", answer="yes",
                               reasoning="r", source_sentence="s")
            no  = AnswerRecord(paper=paper_a, question="Test?", answer="no",
                               reasoning="r", source_sentence="s")
            mock_aq.side_effect = [yes, yes, no]
            with patch("apps.evidence.scoring.reward_voting.score_faithfulness",
                       return_value={"faithfulness_score": 0.8, "error_types": []}):
                from apps.evidence.scoring.reward_voting import compute_reward
                answer_record, reward = compute_reward(paper_a, "Test?", n_samples=3)
                assert pytest.approx(reward.consistency_score, abs=0.01) == 2/3
                assert answer_record.answer == "yes"


def test_reward_voting_all_fail(paper_a):
    with schema_context("demo"):
        with patch("apps.evidence.scoring.reward_voting.answer_question",
                   side_effect=Exception("LLM unavailable")):
            with patch("apps.evidence.scoring.reward_voting.score_faithfulness",
                       return_value={"faithfulness_score": None, "error_types": []}):
                from apps.evidence.scoring.reward_voting import compute_reward
                answer_record, reward = compute_reward(paper_a, "Test?", n_samples=3)
        assert answer_record.answer == "maybe"
        assert reward.consistency_score == pytest.approx(1.0)
        assert reward.final_confidence == pytest.approx(1.0)


def test_reward_voting_faithfulness_none_uses_consistency(paper_a):
    with schema_context("demo"):
        with patch("apps.evidence.scoring.reward_voting.answer_question") as mock_aq:
            from apps.evidence.models import AnswerRecord
            rec = AnswerRecord(paper=paper_a, question="Test?", answer="yes",
                               reasoning="", source_sentence="")
            mock_aq.return_value = rec
            with patch("apps.evidence.scoring.reward_voting.score_faithfulness",
                       return_value={"faithfulness_score": None, "error_types": []}):
                from apps.evidence.scoring.reward_voting import compute_reward
                _, reward = compute_reward(paper_a, "Test?", n_samples=1)
        assert reward.final_confidence == pytest.approx(1.0)
        assert reward.faithfulness_score is None
