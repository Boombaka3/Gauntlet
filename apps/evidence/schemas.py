# apps/evidence/schemas.py
from datetime import datetime

from ninja import Schema
from pydantic import ConfigDict


class JobIn(Schema):
    n_samples: int = 3


class JobOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    n_samples: int
    papers_count: int
    claims_count: int
    conflicts_count: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class PaperOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    title: str
    abstract: str
    s3_key: str
    claims_count: int
    created_at: datetime


class ClaimOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paper_id: int
    text: str
    claim_type: str
    entities: list
    section: str
    source_sentence: str
    confidence: float | None
    created_at: datetime


class RewardScoreOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    consistency_score: float | None
    nli_score: float | None
    faithfulness_score: float | None
    final_confidence: float | None
    n_samples: int


class ConflictPairOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim_a_id: int
    claim_b_id: int
    verdict: str
    conflict_type: str
    severity: int | None
    reasoning: str
    source_sentence_a: str
    source_sentence_b: str
    reward: RewardScoreOut | None
    created_at: datetime


class ReportOut(Schema):
    job_id: int
    status: str
    papers: list[PaperOut]
    total_claims: int
    total_conflicts: int
    contradictions: int
    supports: int
    partial: int
    nei: int
    conflicts: list[ConflictPairOut]
