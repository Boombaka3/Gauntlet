# apps/evidence/schemas.py
from ninja import Schema
from pydantic import Field
from typing import Optional


class JobIn(Schema):
    n_samples: int = Field(default=3, ge=1, le=5)


class JobOut(Schema):
    id: int
    status: str
    n_samples: int
    paper_count: int
    claim_count: int
    answer_count: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: str


class PaperOut(Schema):
    id: int
    title: str
    claim_count: int
    answer_count: int
    created_at: str


class ClaimOut(Schema):
    id: int
    text: str
    claim_type: str
    section: str
    confidence: Optional[float] = None
    paper_id: int


class RewardScoreOut(Schema):
    consistency_score: Optional[float] = None
    nli_score: Optional[float] = None
    faithfulness_score: Optional[float] = None
    final_confidence: Optional[float] = None
    n_samples: int


class AnswerRecordOut(Schema):
    id: int
    question: str
    answer: str
    gold_label: str
    reasoning: str
    source_sentence: str
    error_types: list[str]
    final_confidence: Optional[float] = None
    consistency_score: Optional[float] = None
    faithfulness_score: Optional[float] = None
    paper_id: int
    paper_title: str


class AskIn(Schema):
    question: str


class ReportOut(Schema):
    job_id: int
    status: str
    total_papers: int
    total_claims: int
    total_answers: int
    yes_count: int
    no_count: int
    maybe_count: int
    avg_confidence: Optional[float] = None
