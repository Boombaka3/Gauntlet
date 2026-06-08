# scripts/first_run.py
"""
First-time setup script.  Run from the project root after cloning.
Executes migrate_schemas, seed, and preflight in sequence and prints
PASS/FAIL for each step.  Exits 0 only if all three pass.
"""
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STEPS = [
    (
        "migrate_schemas --shared",
        ["uv", "run", "python", "manage.py", "migrate_schemas", "--shared"],
    ),
    (
        "seed demo tenant",
        ["uv", "run", "python", "scripts/seed.py"],
    ),
    (
        "preflight checks",
        ["uv", "run", "python", "scripts/preflight.py"],
    ),
]


def run_step(label: str, cmd: list[str]) -> bool:
    print(f"\n{'=' * 60}")
    print(f"STEP : {label}")
    print(f"CMD  : {' '.join(cmd)}")
    print("=" * 60)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        print(f"\n[PASS] {label}")
        return True
    print(f"\n[FAIL] {label}  (exit code {result.returncode})")
    return False


def main() -> None:
    all_passed = True
    for label, cmd in STEPS:
        if not run_step(label, cmd):
            all_passed = False
            break

    print()
    if all_passed:
        print("All steps passed.")
        print(r"First run complete. Start dev servers with: .\bin\dev.ps1")
        print("Add your ANTHROPIC_API_KEY to .env to enable LLM judge scoring.")
        print("Run smoke test with: uv run python scripts/smoke_test.py")
        sys.exit(0)
    else:
        print("First run FAILED. Fix the error above and re-run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
