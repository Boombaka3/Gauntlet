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
    consistency_score = None
    final_confidence = None
    r_obj = getattr(cp, "reward", None)
    if r_obj is not None:
        try:
            reward = RewardScoreOut(
                consistency_score=r_obj.consistency_score,
                nli_score=r_obj.nli_score,
                faithfulness_score=r_obj.faithfulness_score,
                final_confidence=r_obj.final_confidence,
                n_samples=r_obj.n_samples,
            )
            consistency_score = r_obj.consistency_score
            final_confidence = r_obj.final_confidence
        except Exception:
            pass
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
        error_types=list(cp.error_types) if cp.error_types else [],
        consistency_score=consistency_score,
        final_confidence=final_confidence,
        reward=reward,
        created_at=cp.created_at,
    )


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs/", response=list[JobOut])
def list_jobs(request):
    jobs = AnalysisJob.objects.order_by("-created_at")
    return [_job_out(j) for j in jobs]


@router.post("/jobs/", response=JobOut, auth=api_key_auth)
def create_job(request, data: JobIn):
    job = AnalysisJob.objects.create(n_samples=max(1, data.n_samples))
    return _job_out(job)


@router.get("/jobs/{job_id}/", response=JobOut)
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


@router.get("/jobs/{job_id}/papers/", response=list[PaperOut])
def list_papers(request, job_id: int):
    job = _get_or_404(AnalysisJob, job_id)
    return [_paper_out(p) for p in job.papers.all()]


@router.delete("/papers/{paper_id}/", response={204: None}, auth=api_key_auth)
def delete_paper(request, paper_id: int):
    from django.shortcuts import get_object_or_404
    paper = get_object_or_404(Paper, id=paper_id)
    if paper.job.status != AnalysisJob.Status.PENDING:
        raise HttpError(409, "Cannot delete paper after analysis has started")
    paper.delete()
    return 204, None


# ── Dispatch ──────────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/dispatch/", auth=api_key_auth)
def dispatch_job(request, job_id: int):
    job = _get_or_404(AnalysisJob, job_id)
    if job.status not in (AnalysisJob.Status.PENDING, AnalysisJob.Status.FAILED):
        raise HttpError(400, f"Job {job_id} is already {job.status}; cannot dispatch again")

    from apps.evidence.tasks.dispatch import dispatch_analysis_job
    dispatch_analysis_job.delay(job.id)

    return {"status": "dispatched", "job_id": job_id}


@router.post("/jobs/{job_id}/dispatch-sync/", response={200: dict})
def dispatch_sync(request, job_id: int):
    """
    Synchronous pipeline for demo/free-tier deployment.
    Runs inline: extract claims -> build conflict graph -> score.
    Limit: 2 papers max, 3 claims per paper max.
    No Celery or Redis required.
    """
    from django.shortcuts import get_object_or_404
    from apps.evidence.models import RewardScore
    from apps.evidence.utils.pdf_parser import extract_sections, get_main_sections
    from apps.evidence.scoring.reward_voting import compute_reward
    from apps.evidence.adapters.openai import OpenAICompatAdapter
    import os, json, re, logging as _logging
    from pathlib import Path
    from itertools import combinations

    _logger = _logging.getLogger(__name__)
    MAX_PAPERS = 2
    MAX_CLAIMS_PER_PAPER = 3

    job = get_object_or_404(AnalysisJob, id=job_id)
    papers = list(job.papers.all())

    if len(papers) > MAX_PAPERS:
        raise HttpError(400, f"Sync dispatch limited to {MAX_PAPERS} papers. Use /dispatch/ for larger jobs.")

    if job.status not in (AnalysisJob.Status.PENDING,):
        raise HttpError(409, f"Job is already {job.status}")

    job.status = AnalysisJob.Status.RUNNING
    job.save(update_fields=["status"])

    try:
        model = os.environ.get("NAVIGATOR_MODEL", "llama-3.3-70b-versatile")
        adapter = OpenAICompatAdapter(model_id=model)

        EXTRACTOR_PROMPT = (
            Path(__file__).parent / "prompts" / "claim_extractor.txt"
        ).read_text()

        s3 = _s3_client()

        for paper in papers:
            try:
                obj = s3.get_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=paper.s3_key,
                )
                pdf_bytes = obj["Body"].read()
                sections = get_main_sections(extract_sections(pdf_bytes))
            except Exception as e:
                _logger.error(f"Failed to read paper {paper.id}: {e}")
                sections = {}

            claims_created = 0
            for section_name, section_text in list(sections.items())[:2]:
                if claims_created >= MAX_CLAIMS_PER_PAPER:
                    break
                if not section_text.strip():
                    continue
                prompt = EXTRACTOR_PROMPT.replace("{section_text}", section_text[:2000])
                try:
                    result = adapter.complete(
                        system_prompt="You are a scientific claim extractor. Respond only with valid JSON.",
                        user_prompt=prompt,
                        max_tokens=512,
                    )
                    raw = result.output or ""
                    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
                    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE).strip()
                    data = json.loads(raw)
                    for c in data.get("claims", [])[:MAX_CLAIMS_PER_PAPER]:
                        if claims_created >= MAX_CLAIMS_PER_PAPER:
                            break
                        Claim.objects.create(
                            paper=paper,
                            text=c.get("text", ""),
                            claim_type=c.get("type", "factual"),
                            entities=c.get("entities", []),
                            section=c.get("section", section_name),
                            source_sentence=c.get("source_sentence", ""),
                            confidence=c.get("confidence"),
                        )
                        claims_created += 1
                except Exception as e:
                    _logger.error(f"Claim extraction failed: {e}")

        paper_ids = [p.id for p in papers]
        all_claims = {
            pid: list(Claim.objects.filter(paper_id=pid))
            for pid in paper_ids
        }

        pairs_created = 0
        for pid_a, pid_b in combinations(paper_ids, 2):
            claims_a = all_claims.get(pid_a, [])
            claims_b = all_claims.get(pid_b, [])
            for ca in claims_a:
                for cb in claims_b:
                    try:
                        conflict_pair, reward = compute_reward(
                            ca, cb, n_samples=job.n_samples
                        )
                        conflict_pair.save()
                        reward.conflict_pair = conflict_pair
                        reward.save()
                        pairs_created += 1
                    except Exception as e:
                        _logger.error(f"Conflict pair failed: {e}")

        job.status = AnalysisJob.Status.DONE
        job.save(update_fields=["status"])

        return {
            "job_id": job_id,
            "status": "DONE",
            "papers": len(papers),
            "claims": sum(len(v) for v in all_claims.values()),
            "conflicts": pairs_created,
        }

    except Exception as e:
        _logger.error(f"Sync dispatch failed for job {job_id}: {e}")
        job.status = AnalysisJob.Status.FAILED
        job.save(update_fields=["status"])
        raise HttpError(500, f"Pipeline failed: {str(e)}")


# ── Claims & Conflicts ────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/claims/", response=list[ClaimOut])
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


@router.get("/jobs/{job_id}/conflicts/", response=list[ConflictPairOut])
def list_conflicts(request, job_id: int):
    _get_or_404(AnalysisJob, job_id)
    conflicts = (
        ConflictPair.objects
        .filter(claim_a__paper__job_id=job_id)
        .select_related("claim_a__paper", "claim_b__paper", "reward")
        .order_by("created_at")
    )
    return [_conflict_out(cp) for cp in conflicts]


@router.get("/jobs/{job_id}/report/", response=ReportOut)
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
