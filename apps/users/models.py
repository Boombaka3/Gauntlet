# llm_eval_harness/apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model in the PUBLIC schema. Extends AbstractUser to keep all
    standard Django auth behaviour while giving us room to add tenant-scoped
    profile fields later without a migration on the built-in User table.
    """
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        app_label = "users"
