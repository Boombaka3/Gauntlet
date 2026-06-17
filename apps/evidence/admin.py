# apps/evidence/admin.py
from django.contrib import admin

from .models import AnalysisJob, AnswerRecord, Claim, Paper, RewardScore


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'n_samples', 'created_at']
    list_filter  = ['status']


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display  = ['id', 'title', 'job', 'created_at']
    search_fields = ['title']


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['id', 'claim_type', 'section', 'confidence', 'paper']
    list_filter  = ['claim_type', 'section']


@admin.register(AnswerRecord)
class AnswerRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'answer', 'question_preview', 'paper']
    list_filter  = ['answer']

    def question_preview(self, obj):
        return obj.question[:60]
    question_preview.short_description = 'Question'


@admin.register(RewardScore)
class RewardScoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'consistency_score', 'final_confidence', 'n_samples']
