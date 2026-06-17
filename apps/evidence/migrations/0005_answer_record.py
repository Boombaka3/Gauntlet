# Generated manually for Phase 1 pivot: ConflictPair -> AnswerRecord
import django.db.models.deletion
from django.db import migrations, models


def delete_old_reward_and_conflict(apps, schema_editor):
    """Clear ConflictPair-linked rows before dropping the old schema."""
    RewardScore = apps.get_model("evidence", "RewardScore")
    ConflictPair = apps.get_model("evidence", "ConflictPair")
    RewardScore.objects.all().delete()
    ConflictPair.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("evidence", "0004_error_types_blank"),
    ]

    operations = [
        # 1. Wipe old rows so FK constraints are safe to drop
        migrations.RunPython(
            delete_old_reward_and_conflict,
            reverse_code=migrations.RunPython.noop,
        ),

        # 2. Remove old FK from RewardScore
        migrations.RemoveField(
            model_name="rewardscore",
            name="conflict_pair",
        ),

        # 3. Drop ConflictPair (and its FKs to Claim)
        migrations.DeleteModel(
            name="ConflictPair",
        ),

        # 4. Create AnswerRecord
        migrations.CreateModel(
            name="AnswerRecord",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.TextField()),
                ("answer", models.CharField(
                    choices=[("yes", "Yes"), ("no", "No"), ("maybe", "Maybe")],
                    max_length=10,
                )),
                ("gold_label", models.CharField(blank=True, max_length=10)),
                ("reasoning", models.TextField(blank=True)),
                ("source_sentence", models.TextField(blank=True)),
                ("error_types", models.JSONField(
                    default=list,
                    help_text=(
                        "EvidenceLens error taxonomy: "
                        "overgeneralization, condition_dropping, "
                        "false_certainty, missing_evidence, "
                        "unsupported_claim, wrong_evidence, "
                        "missing_limitation, "
                        "contradiction_with_source, "
                        "conflict_ignored, paper_section_misread"
                    ),
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paper", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="answers",
                    to="evidence.paper",
                )),
            ],
            options={"app_label": "evidence"},
        ),

        # 5. Add answer_record FK to RewardScore (table is empty from step 1)
        migrations.AddField(
            model_name="rewardscore",
            name="answer_record",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reward",
                to="evidence.answerrecord",
                null=True,
            ),
        ),

        # 6. Make answer_record non-nullable now that all rows are fresh
        migrations.AlterField(
            model_name="rewardscore",
            name="answer_record",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reward",
                to="evidence.answerrecord",
            ),
        ),
    ]
