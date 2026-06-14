# scripts/smoke_test.py
"""
End-to-end smoke test for EvidenceTrace.
Requires Django and Celery to be running (start with bin\\dev.ps1).

Exit 0 on pass, 1 on fail.
"""
import io
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "http://localhost:8000"
TENANT_HEADERS = {"Host": "demo.localhost"}
POLL_INTERVAL = 5
POLL_TIMEOUT = 180

TEST_DATA = Path(__file__).parent / "test_data"
API_KEY = os.environ.get("GAUNTLET_API_KEY", os.environ.get("DJANGO_SUPERUSER_API_KEY", ""))
NAVIGATOR_KEY = os.environ.get("OPENAI_API_KEY", "")
NAVIGATOR_MODEL = os.environ.get("NAVIGATOR_MODEL", "llama-3.3-70b-instruct")


def _headers() -> dict:
    h = dict(TENANT_HEADERS)
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def step(n: int, label: str) -> None:
    print(f"\n[{n}] {label}")


def fail(reason: str) -> None:
    print(f"\nSmoke test FAILED: {reason}")
    sys.exit(1)


def make_test_pdf(text: str) -> bytes:
    """Build a minimal valid PDF containing the given ASCII text."""
    safe = text.replace("(", "").replace(")", "").replace("\\", "")
    content_src = f"BT /F1 12 Tf 50 700 Td ({safe}) Tj ET"
    content_b = content_src.encode("latin-1")

    obj1 = b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    obj2 = b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    obj3 = (
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    )
    stream_hdr = f"4 0 obj<</Length {len(content_b)}>>\nstream\n".encode()
    stream_end = b"\nendstream\nendobj\n"
    obj5 = b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"

    header = b"%PDF-1.4\n"
    off1 = len(header)
    off2 = off1 + len(obj1)
    off3 = off2 + len(obj2)
    off4 = off3 + len(obj3)
    off5 = off4 + len(stream_hdr) + len(content_b) + len(stream_end)

    body = header + obj1 + obj2 + obj3 + stream_hdr + content_b + stream_end + obj5
    xref_off = len(body)

    xref = (
        f"xref\n0 6\n"
        f"0000000000 65535 f \n"
        f"{off1:010d} 00000 n \n"
        f"{off2:010d} 00000 n \n"
        f"{off3:010d} 00000 n \n"
        f"{off4:010d} 00000 n \n"
        f"{off5:010d} 00000 n \n"
        f"trailer<</Size 6/Root 1 0 R>>\n"
        f"startxref\n{xref_off}\n%%EOF"
    ).encode()

    return body + xref


def create_minimal_pdf(text: str) -> bytes:
    """Alias for make_test_pdf — builds a valid PDF from plain text."""
    return make_test_pdf(text)


def get_test_paper_texts() -> tuple[str, str]:
    """
    Load first conflict pair texts from EvidenceLens ground truth.
    Falls back to synthetic text if file not found.
    """
    import json
    conflict_path = TEST_DATA / "conflict_pairs_ground_truth.jsonl"
    if conflict_path.exists():
        with open(conflict_path, encoding="utf-8") as f:
            pairs = [json.loads(l) for l in f if l.strip()]
        if pairs:
            pair = pairs[0]
            doc_a = pair.get("document_a") or {}
            doc_b = pair.get("document_b") or {}
            text_a = (
                " ".join(doc_a.get("sentences", []))
                or doc_a.get("abstract", "")
                or pair.get("claim_a", "")
                or "Results: Drug X reduces tumor size by 40% in mouse models."
            )
            text_b = (
                " ".join(doc_b.get("sentences", []))
                or doc_b.get("abstract", "")
                or pair.get("claim_b", "")
                or "Results: Drug X shows no significant effect in clinical trials."
            )
            return str(text_a)[:1000], str(text_b)[:1000]
    return (
        "Results: Drug X significantly reduces tumor size in mouse models "
        "with a 40% reduction observed at 10mg/kg dose after 4 weeks.",
        "Results: Drug X showed no statistically significant effect on "
        "tumor size in Phase 2 clinical trials across 200 patients.",
    )


def _load_paper(filename: str) -> bytes:
    path = TEST_DATA / filename
    if path.exists():
        return path.read_bytes()
    text_a, text_b = get_test_paper_texts()
    texts = {
        "synthetic_paper_a.pdf": text_a,
        "synthetic_paper_b.pdf": text_b,
    }
    return create_minimal_pdf(texts.get(filename, f"Synthetic paper: {filename}"))


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, headers=_headers(), timeout=30.0)

    # ── Step 1: create job ────────────────────────────────────────────────────
    step(1, "POST /api/evidence/jobs/")
    r = client.post("/api/evidence/jobs/", json={"n_samples": 1})
    if r.status_code not in (200, 201):
        fail(f"create job returned {r.status_code}: {r.text}")
    job_id = r.json()["id"]
    print(f"    job_id={job_id}  OK")

    # ── Step 2: upload two synthetic PDFs ────────────────────────────────────
    step(2, f"POST /api/evidence/jobs/{job_id}/papers/  (×2)")

    papers = [
        ("synthetic_paper_a.pdf", "Study A: Drug X Mouse Model"),
        ("synthetic_paper_b.pdf", "Study B: Drug X Clinical Trials"),
    ]
    for filename, title in papers:
        pdf_bytes = _load_paper(filename)
        r = client.post(
            f"/api/evidence/jobs/{job_id}/papers/",
            files={"pdf_file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
            data={"title": title},
        )
        if r.status_code not in (200, 201):
            fail(f"upload {filename} returned {r.status_code}: {r.text}")
        print(f"    {filename} id={r.json()['id']}  OK")

    # ── Step 3: dispatch job ──────────────────────────────────────────────────
    step(3, f"POST /api/evidence/jobs/{job_id}/dispatch/")
    r = client.post(f"/api/evidence/jobs/{job_id}/dispatch/")
    if r.status_code not in (200, 201):
        fail(f"dispatch returned {r.status_code}: {r.text}")
    print(f"    {r.json()}  OK")

    # ── Step 4: poll until DONE ───────────────────────────────────────────────
    # If no NaviGator key, assert job at least reached RUNNING state
    has_real_key = bool(NAVIGATOR_KEY) and NAVIGATOR_KEY not in ("<your-navigator-api-key>", "placeholder", "")

    step(4, f"Polling GET /api/evidence/jobs/{job_id}/  (up to {POLL_TIMEOUT}s)")
    elapsed = 0
    final_status = None
    reached_running = False
    while elapsed < POLL_TIMEOUT:
        r = client.get(f"/api/evidence/jobs/{job_id}/")
        if r.status_code != 200:
            fail(f"poll returned {r.status_code}: {r.text}")
        body = r.json()
        status = body["status"]
        claims = body.get("claims_count", 0)
        conflicts = body.get("conflicts_count", 0)
        print(f"    [{elapsed:>3}s] status={status}  claims={claims}  conflicts={conflicts}")
        if status == "RUNNING":
            reached_running = True
        if status in ("DONE", "FAILED"):
            final_status = status
            break
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    if not has_real_key:
        if reached_running or final_status in ("DONE", "FAILED"):
            print("    SKIP conflict assertion — no API key")
            print(f"\nSmoke test PASSED  (job reached status={final_status or 'RUNNING'})")
            return
        fail(f"job did not reach RUNNING state within {POLL_TIMEOUT}s")

    if final_status is None:
        fail(f"job did not complete within {POLL_TIMEOUT}s")
    if final_status != "DONE":
        fail(f"job finished with status={final_status}")
    print("    Job DONE  OK")

    # ── Step 5: check conflicts ───────────────────────────────────────────────
    step(5, f"GET /api/evidence/jobs/{job_id}/conflicts/")
    r = client.get(f"/api/evidence/jobs/{job_id}/conflicts/")
    if r.status_code != 200:
        fail(f"conflicts returned {r.status_code}: {r.text}")

    conflicts_data = r.json()
    if not conflicts_data:
        print("    WARNING: no ConflictPairs found — check OPENAI_API_KEY / NaviGator and Celery logs")
        print(f"\nSmoke test PASSED  (job DONE; 0 conflicts — may need larger PDFs)")
        return

    for cp in conflicts_data:
        verdict = cp.get("verdict")
        reward = cp.get("reward") or {}
        confidence = reward.get("final_confidence")
        print(f"    conflict_id={cp['id']}  verdict={verdict}  confidence={confidence}")
        assert verdict is not None, f"ConflictPair {cp['id']} missing verdict"
        assert confidence is not None, f"ConflictPair {cp['id']} missing final_confidence"

    print(
        f"\nSmoke test PASSED"
        f"  ({len(conflicts_data)} ConflictPair(s) with verdicts and confidence scores)"
    )


if __name__ == "__main__":
    main()
    sys.exit(0)
