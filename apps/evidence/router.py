# apps/evidence/router.py
import logging

import boto3
from django.conf import settings
from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.evidence.models import AnalysisJob, AnswerRecord, Claim, Paper, RewardScore
from apps.evidence.schemas import (
    AnswerRecordOut,
    AskIn,
    ClaimOut,
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
    paper_count = job.papers.count()
    claim_count = Claim.objects.filter(paper__job=job).count()
    answer_count = AnswerRecord.objects.filter(paper__job=job).count()
    return JobOut(
        id=job.id,
        status=job.status,
        n_samples=job.n_samples,
        paper_count=paper_count,
        claim_count=claim_count,
        answer_count=answer_count,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        created_at=job.created_at.isoformat(),
    )


def _paper_out(paper: Paper) -> PaperOut:
    return PaperOut(
        id=paper.id,
        title=paper.title,
        claim_count=paper.claims.count(),
        answer_count=paper.answers.count(),
        created_at=paper.created_at.isoformat(),
    )


def _answer_out(ar: AnswerRecord) -> dict:
    reward = getattr(ar, 'reward', None)
    return {
        "id": ar.id,
        "question": ar.question,
        "answer": ar.answer,
        "gold_label": ar.gold_label,
        "reasoning": ar.reasoning,
        "source_sentence": ar.source_sentence,
        "error_types": ar.error_types or [],
        "final_confidence": reward.final_confidence if reward else None,
        "consistency_score": reward.consistency_score if reward else None,
        "faithfulness_score": reward.faithfulness_score if reward else None,
        "paper_id": ar.paper_id,
        "paper_title": ar.paper.title if ar.paper_id else "",
    }


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
    Runs inline: extract claims -> answer questions per paper.
    Limit: 2 papers max, 3 claims per paper max.
    No Celery or Redis required.
    """
    from django.shortcuts import get_object_or_404
    from apps.evidence.scoring.reward_voting import compute_reward
    from apps.evidence.adapters.openai import OpenAICompatAdapter
    from apps.evidence.utils.pdf_parser import extract_sections, get_main_sections
    from apps.evidence.tasks.answer_questions import _claim_to_question
    import os, json, re, logging as _logging
    from pathlib import Path

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

        answers_created = 0
        for paper in papers:
            claims = list(paper.claims.all())
            for claim in claims:
                if not claim.text.strip():
                    continue
                try:
                    question = _claim_to_question(claim.text)
                    answer_record, reward = compute_reward(
                        paper, question, n_samples=job.n_samples
                    )
                    answer_record.gold_label = ""
                    answer_record.save()
                    reward.answer_record = answer_record
                    reward.save()
                    answers_created += 1
                except Exception as e:
                    _logger.error(f"Answer question failed for claim {claim.id}: {e}")

        job.status = AnalysisJob.Status.DONE
        job.save(update_fields=["status"])

        total_claims = sum(paper.claims.count() for paper in papers)
        return {
            "job_id": job_id,
            "status": "DONE",
            "papers": len(papers),
            "claims": total_claims,
            "answers": answers_created,
        }

    except Exception as e:
        _logger.error(f"Sync dispatch failed for job {job_id}: {e}")
        job.status = AnalysisJob.Status.FAILED
        job.save(update_fields=["status"])
        raise HttpError(500, f"Pipeline failed: {str(e)}")


# ── Claims ────────────────────────────────────────────────────────────────────

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
            section=c.section,
            confidence=c.confidence,
        )
        for c in claims
    ]


# ── Answers ───────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/answers/", response=list[AnswerRecordOut])
def list_answers(request, job_id: int):
    _get_or_404(AnalysisJob, job_id)
    answers = (
        AnswerRecord.objects
        .filter(paper__job_id=job_id)
        .select_related("paper", "reward")
        .order_by("created_at")
    )
    return [AnswerRecordOut(**_answer_out(ar)) for ar in answers]


@router.post("/jobs/{job_id}/ask/", response=list[AnswerRecordOut], auth=api_key_auth)
def ask_question(request, job_id: int, payload: AskIn):
    from apps.evidence.scoring.reward_voting import compute_reward

    job = _get_or_404(AnalysisJob, job_id)
    question = payload.question.strip()
    if not question:
        raise HttpError(400, "question is required")

    papers = list(job.papers.all())
    results = []
    for paper in papers:
        try:
            answer_record, reward = compute_reward(
                paper, question, n_samples=job.n_samples
            )
            answer_record.gold_label = ""
            answer_record.save()
            reward.answer_record = answer_record
            reward.save()
            ar = AnswerRecord.objects.select_related("paper", "reward").get(
                pk=answer_record.pk
            )
            results.append(AnswerRecordOut(**_answer_out(ar)))
        except Exception as e:
            logger.error(f"ask_question failed for paper {paper.id}: {e}")

    return results


# ── Report ────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/report/", response=ReportOut)
def get_report(request, job_id: int):
    job = _get_or_404(AnalysisJob, job_id)
    total_papers = job.papers.count()
    total_claims = Claim.objects.filter(paper__job=job).count()
    total_answers = AnswerRecord.objects.filter(paper__job=job).count()
    yes_count   = AnswerRecord.objects.filter(paper__job=job, answer='yes').count()
    no_count    = AnswerRecord.objects.filter(paper__job=job, answer='no').count()
    maybe_count = AnswerRecord.objects.filter(paper__job=job, answer='maybe').count()

    reward_scores = RewardScore.objects.filter(
        answer_record__paper__job=job
    ).values_list("final_confidence", flat=True)
    valid_scores = [s for s in reward_scores if s is not None]
    avg_confidence = sum(valid_scores) / len(valid_scores) if valid_scores else None

    return ReportOut(
        job_id=job.id,
        status=job.status,
        total_papers=total_papers,
        total_claims=total_claims,
        total_answers=total_answers,
        yes_count=yes_count,
        no_count=no_count,
        maybe_count=maybe_count,
        avg_confidence=avg_confidence,
    )
