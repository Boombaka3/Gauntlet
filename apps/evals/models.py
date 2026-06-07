# llm_eval_harness/apps/evals/models.py
from django.db import models


class EvalSuite(models.Model):
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    rubric = models.JSONField(
        default=list,
        help_text="List of {criterion: str, weight: float} objects",
    )
    regression_threshold = models.FloatField(
        default=0.3,
        help_text="Minimum acceptable regression delta before marking passed=False",
    )
    # Pinned via POST /runs/{id}/pin-baseline/
    baseline_run = models.ForeignKey(
        "EvalRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pinned_for_suites",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "evals"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class PromptCase(models.Model):
    suite = models.ForeignKey(EvalSuite, on_delete=models.CASCADE, related_name="cases")
    name = models.CharField(max_length=255)
    system_prompt = models.TextField()
    user_prompt = models.TextField()
    expected_output = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "evals"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.suite.name} / {self.name}"


class EvalRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DISPATCHED = "DISPATCHED", "Dispatched"
        RUNNING = "RUNNING", "Running"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    class ScoreMode(models.TextChoices):
        EXACT_MATCH = "exact_match", "Exact Match"
        RUBRIC = "rubric", "Rubric"
        LLM_JUDGE = "llm_judge", "LLM Judge"
        REGRESSION = "regression", "Regression"

    suite = models.ForeignKey(EvalSuite, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    model_ids = models.JSONField(
        help_text="List of model identifier strings to fan out against",
    )
    baseline_run = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="derived_runs",
    )
    score_mode = models.CharField(
        max_length=20,
        choices=ScoreMode.choices,
        default=ScoreMode.LLM_JUDGE,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result_s3_key = models.CharField(max_length=512, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "evals"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"EvalRun {self.pk} [{self.status}] — {self.suite.name}"


class ModelRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    eval_run = models.ForeignKey(EvalRun, on_delete=models.CASCADE, related_name="model_runs")
    prompt_case = models.ForeignKey(PromptCase, on_delete=models.CASCADE, related_name="model_runs")
    model_id = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    raw_output = models.TextField(blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    token_count = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    s3_key = models.CharField(max_length=512, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "evals"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"ModelRun {self.pk} [{self.model_id}] [{self.status}]"


class ScoreResult(models.Model):
    model_run = models.OneToOneField(ModelRun, on_delete=models.CASCADE, related_name="score")
    scores = models.JSONField(
        default=dict,
        help_text="{criterion: score} mapping; scores are floats 1–5 or None",
    )
    overall = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    judge_reasoning = models.TextField(blank=True, null=True)
    regression_delta = models.FloatField(
        null=True,
        blank=True,
        help_text="current.overall - baseline.overall; negative = regression",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "evals"

    def __str__(self) -> str:
        return f"ScoreResult for ModelRun {self.model_run_id} overall={self.overall:.2f}"
