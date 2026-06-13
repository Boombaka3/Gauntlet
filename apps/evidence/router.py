# apps/evidence/router.py
import logging

import boto3
from django.conf import settings
from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.evidence.models import AnalysisJob, Claim, ConflictPair, Paper
from apps.evidence.schemas import (
    ClaimOut,
    ConflictPairOut,
    JobIn,
    JobOut,
    PaperOut,
    ReportOut,
    RewardScoreOut,
)
from apps.users.auth import ApiKeyAuth

logger = logging.getLogger(__name__)
api_key_auth = ApiKeyAuth()
router = Router(tags=["evidence"])


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def _get_or_404(model_class, pk: int):
    obj = model_class.objects.filter(pk=pk).first()
    if obj is None:
        raise HttpError(404, f"{model_class.__name__} {pk} not found")
    return obj


def _job_out(job: AnalysisJob) -> JobOut:
    papers_count = job.papers.count()
    claims_count = Claim.objects.filter(paper__job=job).count()
    conflicts_count = ConflictPair.objects.filter(claim_a__paper__job=job).count()
    return JobOut(
        id=job.id,
        status=job.status,
        n_samples=job.n_samples,
        papers_count=papers_count,
        claims_count=claims_count,
        conflicts_count=conflicts_count,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


def _paper_out(paper: Paper) -> PaperOut:
    return PaperOut(
        id=paper.id,
        job_id=paper.job_id,
        title=paper.title,
        abstract=paper.abstract,
        s3_key=paper.s3_key,
        claims_count=paper.claims.count(),
        created_at=paper.created_at,
    )


def _conflict_out(cp: ConflictPair) -> ConflictPairOut:
    reward = None
    if hasattr(cp, "reward"):
        r = cp.reward
        reward = RewardScoreOut(
            consistency_score=r.consistency_score,
            nli_score=r.nli_score,
            faithfulness_score=r.faithfulness_score,
            final_confidence=r.final_confidence,
            n_samples=r.n_samples,
        )
    return ConflictPairOut(
        id=cp.id,
        claim_a_id=cp.claim_a_id,
        claim_b_id=cp.claim_b_id,
        verdict=cp.verdict,
        conflict_type=cp.conflict_type,
        severity=cp.severity,
        reasoning=cp.reasoning,
        source_sentence_a=cp.source_sentence_a,
        source_sentence_b=cp.source_sentence_b,
        reward=reward,
        created_at=cp.created_at,
    )


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.post("/jobs/", response=JobOut, auth=api_key_auth)
def create_job(request, data: JobIn):
    job = AnalysisJob.objects.create(n_samples=max(1, data.n_samples))
    return _job_out(job)


@router.get("/jobs/{job_id}/", response=JobOut, auth=api_key_auth)
def get_job(request, job_id: int):
    job = _get_or_404(AnalysisJob, job_id)
    return _job_out(job)


# ── Papers ────────────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/papers/", response=PaperOut, auth=api_key_auth)
def upload_paper(request, job_id: int, pdf_file: UploadedFile = File(...), title: str = ""):
    job = _get_or_404(AnalysisJob, job_id)
    filename = pdf_file.name or f"paper_{job_id}.pdf"
    s3_key = f"jobs/{job_id}/papers/{filename}"

    s3 = _s3_client()
    try:
        s3.create_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
    except Exception:
        pass

    s3.upload_fileobj(pdf_file.file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)

    paper = Paper.objects.create(
        job=job,
        title=title or filename,
        s3_key=s3_key,
    )
    return _paper_out(paper)


@router.get("/jobs/{job_id}/papers/", response=list[PaperOut], auth=api_key_auth)
def list_papers(request, job_id: int):
    job = _get_or_404(AnalysisJob, job_id)
    return [_paper_out(p) for p in job.papers.all()]


# ── Dispatch ──────────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/dispatch/", auth=api_key_auth)
def dispatch_job(request, job_id: int):
    job = _get_or_404(AnalysisJob, job_id)
    if job.status not in (AnalysisJob.Status.PENDING, AnalysisJob.Status.FAILED):
        raise HttpError(400, f"Job {job_id} is already {job.status}; cannot dispatch again")

    from apps.evidence.tasks.dispatch import dispatch_analysis_job
    dispatch_analysis_job.delay(job.id)

    return {"status": "dispatched", "job_id": job_id}


# ── Claims & Conflicts ────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/claims/", response=list[ClaimOut], auth=api_key_auth)
def list_claims(request, job_id: int):
    _get_or_404(AnalysisJob, job_id)
    claims = Claim.objects.filter(paper__job_id=job_id).select_related("paper").order_by("created_at")
    return [
        ClaimOut(
            id=c.id,
            paper_id=c.paper_id,
            text=c.text,
            claim_type=c.claim_type,
            entities=c.entities,
            section=c.section,
            source_sentence=c.source_sentence,
            confidence=c.confidence,
            created_at=c.created_at,
        )
        for c in claims
    ]


@router.get("/jobs/{job_id}/conflicts/", response=list[ConflictPairOut], auth=api_key_auth)
def list_conflicts(request, job_id: int):
    _get_or_404(AnalysisJob, job_id)
    conflicts = (
        ConflictPair.objects
        .filter(claim_a__paper__job_id=job_id)
        .select_related("claim_a__paper", "claim_b__paper", "reward")
        .order_by("created_at")
    )
    return [_conflict_out(cp) for cp in conflicts]


@router.get("/jobs/{job_id}/report/", response=ReportOut, auth=api_key_auth)
def get_report(request, job_id: int):
    job = _get_or_404(AnalysisJob, job_id)
    papers = list(job.papers.all())
    conflicts = list(
        ConflictPair.objects
        .filter(claim_a__paper__job_id=job_id)
        .select_related("claim_a__paper", "claim_b__paper", "reward")
        .order_by("created_at")
    )
    total_claims = Claim.objects.filter(paper__job=job).count()

    return ReportOut(
        job_id=job.id,
        status=job.status,
        papers=[_paper_out(p) for p in papers],
        total_claims=total_claims,
        total_conflicts=len(conflicts),
        contradictions=sum(1 for c in conflicts if c.verdict == ConflictPair.Verdict.CONTRADICTS),
        supports=sum(1 for c in conflicts if c.verdict == ConflictPair.Verdict.SUPPORTS),
        partial=sum(1 for c in conflicts if c.verdict == ConflictPair.Verdict.PARTIAL),
        nei=sum(1 for c in conflicts if c.verdict == ConflictPair.Verdict.NEI),
        conflicts=[_conflict_out(cp) for cp in conflicts],
    )
