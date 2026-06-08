# scripts/smoke_test.py
"""
End-to-end smoke test against the live dev server.
Requires Django and Celery to be running (start with bin\dev.ps1).

Exit 0 on pass, 1 on fail.
"""
import sys
import time

import httpx

BASE_URL = "http://localhost:8000"
# TenantMainMiddleware routes to the demo schema based on this header.
TENANT_HEADERS = {"Host": "demo.localhost"}
POLL_INTERVAL = 5   # seconds between status polls
POLL_TIMEOUT = 120  # seconds before giving up


def step(n: int, label: str) -> None:
    print(f"\n[{n}] {label}")


def fail(reason: str) -> None:
    print(f"\nSmoke test FAILED: {reason}")
    sys.exit(1)


def main() -> None:
    client = httpx.Client(
        base_url=BASE_URL,
        headers=TENANT_HEADERS,
        timeout=30.0,
    )

    # ── Step 1: create suite ──────────────────────────────────────────────────
    step(1, "POST /api/evals/suites/")
    r = client.post(
        "/api/evals/suites/",
        json={
            "name": "Smoke Test Suite",
            "version": 1,
            "rubric": [{"criterion": "quality", "weight": 1.0}],
            "regression_threshold": 0.3,
        },
    )
    if r.status_code not in (200, 201):
        fail(f"create suite returned {r.status_code}: {r.text}")
    suite_id = r.json()["id"]
    print(f"    suite_id={suite_id}  OK")

    # ── Step 2: create prompt case ────────────────────────────────────────────
    step(2, f"POST /api/evals/suites/{suite_id}/cases/")
    r = client.post(
        f"/api/evals/suites/{suite_id}/cases/",
        json={
            "name": "Basic case",
            "system_prompt": "You are helpful.",
            "user_prompt": "Say hello in one word.",
            "expected_output": "Hello",
        },
    )
    if r.status_code not in (200, 201):
        fail(f"create case returned {r.status_code}: {r.text}")
    case_id = r.json()["id"]
    print(f"    case_id={case_id}  OK")

    # ── Step 3: create eval run ───────────────────────────────────────────────
    step(3, "POST /api/evals/runs/")
    r = client.post(
        "/api/evals/runs/",
        json={
            "suite_id": suite_id,
            "model_ids": ["claude-haiku-4-5-20251001"],
            "score_mode": "exact_match",
        },
    )
    if r.status_code not in (200, 201):
        fail(f"create run returned {r.status_code}: {r.text}")
    run_id = r.json()["id"]
    print(f"    run_id={run_id}  status={r.json()['status']}  OK")

    # ── Step 4: poll until DONE or FAILED ────────────────────────────────────
    step(4, f"Polling GET /api/evals/runs/{run_id}/ (up to {POLL_TIMEOUT}s)")
    elapsed = 0
    final_status = None
    while elapsed < POLL_TIMEOUT:
        r = client.get(f"/api/evals/runs/{run_id}/")
        if r.status_code != 200:
            fail(f"poll returned {r.status_code}: {r.text}")
        body = r.json()
        status = body["status"]
        progress = body.get("progress", 0)
        total = body.get("total", 0)
        print(f"    [{elapsed:>3}s] status={status}  progress={progress}/{total}")
        if status in ("DONE", "FAILED"):
            final_status = status
            break
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    if final_status is None:
        fail(f"run did not complete within {POLL_TIMEOUT}s")
    if final_status != "DONE":
        fail(f"run finished with status={final_status}")
    print("    Run DONE  OK")

    # ── Step 5: fetch results ─────────────────────────────────────────────────
    step(5, f"GET /api/evals/runs/{run_id}/results/")
    r = client.get(f"/api/evals/runs/{run_id}/results/")
    if r.status_code != 200:
        fail(f"results returned {r.status_code}: {r.text}")
    results = r.json()
    if not results:
        fail("no ScoreResults returned")

    for res in results:
        model_id = res.get("model_run_id")
        overall = res.get("overall")
        passed = res.get("passed")
        print(f"    model_run_id={model_id}  overall={overall}  passed={passed}")
        assert res["passed"] is not None

    print(f"\nSmoke test PASSED  ({len(results)} result(s))")


def smoke_test_llm_judge() -> None:
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "placeholder":
        print("\nSKIP llm_judge smoke test — no API key")
        return

    client = httpx.Client(base_url=BASE_URL, headers=TENANT_HEADERS, timeout=30.0)

    r = client.post(
        "/api/evals/suites/",
        json={
            "name": "Smoke Test Suite (llm_judge)",
            "version": 1,
            "rubric": [{"criterion": "quality", "weight": 1.0}],
            "regression_threshold": 0.3,
        },
    )
    if r.status_code not in (200, 201):
        print(f"llm_judge smoke test FAILED: create suite returned {r.status_code}: {r.text}")
        return
    suite_id = r.json()["id"]

    r = client.post(
        f"/api/evals/suites/{suite_id}/cases/",
        json={
            "name": "Basic case",
            "system_prompt": "You are helpful.",
            "user_prompt": "Say hello in one word.",
            "expected_output": "Hello",
        },
    )
    if r.status_code not in (200, 201):
        print(f"llm_judge smoke test FAILED: create case returned {r.status_code}: {r.text}")
        return

    r = client.post(
        "/api/evals/runs/",
        json={
            "suite_id": suite_id,
            "model_ids": ["claude-haiku-4-5-20251001"],
            "score_mode": "llm_judge",
        },
    )
    if r.status_code not in (200, 201):
        print(f"llm_judge smoke test FAILED: create run returned {r.status_code}: {r.text}")
        return
    run_id = r.json()["id"]

    elapsed = 0
    final_status = None
    while elapsed < POLL_TIMEOUT:
        r = client.get(f"/api/evals/runs/{run_id}/")
        if r.status_code != 200:
            print(f"llm_judge smoke test FAILED: poll returned {r.status_code}: {r.text}")
            return
        status = r.json()["status"]
        if status in ("DONE", "FAILED"):
            final_status = status
            break
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    if final_status != "DONE":
        print(f"llm_judge smoke test FAILED: run finished with status={final_status}")
        return

    r = client.get(f"/api/evals/runs/{run_id}/results/")
    if r.status_code != 200:
        print(f"llm_judge smoke test FAILED: results returned {r.status_code}: {r.text}")
        return
    results = r.json()
    if not results:
        print("llm_judge smoke test FAILED: no ScoreResults returned")
        return

    for res in results:
        model_id = res.get("model_run_id")
        overall = res.get("overall")
        passed = res.get("passed")
        print(f"    model_run_id={model_id}  overall={overall}  passed={passed}")
        if overall is None:
            print("llm_judge smoke test FAILED: overall=None")
            return

    print("llm_judge smoke test PASSED")


if __name__ == "__main__":
    main()
    smoke_test_llm_judge()
    sys.exit(0)
