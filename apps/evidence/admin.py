# apps/evidence/admin.py
from django.contrib import admin

from .models import AnalysisJob, Claim, ConflictPair, Paper, RewardScore


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "n_samples", "started_at", "finished_at", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["started_at", "finished_at", "result_s3_key"]


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "title", "s3_key", "created_at"]
    list_filter = ["job"]
    search_fields = ["title", "s3_key"]


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ["id", "paper", "claim_type", "confidence", "created_at"]
    list_filter = ["claim_type"]
    search_fields = ["text"]


@admin.register(ConflictPair)
class ConflictPairAdmin(admin.ModelAdmin):
    list_display = ["id", "verdict", "conflict_type", "severity", "created_at"]
    list_filter = ["verdict", "conflict_type"]
    readonly_fields = ["reasoning", "source_sentence_a", "source_sentence_b"]


@admin.register(RewardScore)
class RewardScoreAdmin(admin.ModelAdmin):
    list_display = ["id", "conflict_pair", "consistency_score", "final_confidence", "n_samples", "created_at"]
    readonly_fields = ["consistency_score", "nli_score", "faithfulness_score", "final_confidence"]
