from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160)
    model_name = models.CharField(max_length=120)
    system_prompt = models.TextField(blank=True, default=settings.CHAT_DEFAULT_SYSTEM_PROMPT)
    context_limit_tokens = models.PositiveIntegerField(default=settings.CHAT_CONTEXT_LIMIT_TOKENS)
    available_models_snapshot = models.JSONField(default=list, blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def model_label(self) -> str:
        for model in settings.OLLAMA_MODEL_CATALOG:
            if model.get("name") == self.model_name:
                return model.get("label", self.model_name)
        return self.model_name

    def get_absolute_url(self) -> str:
        return reverse("chat:conversation_detail", kwargs={"conversation_id": self.id})


class Message(models.Model):
    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    sequence_number = models.PositiveIntegerField()
    input_tokens_estimated = models.PositiveIntegerField(null=True, blank=True)
    output_tokens_estimated = models.PositiveIntegerField(null=True, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence_number", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence_number"],
                name="unique_message_sequence_per_conversation",
            )
        ]

    def __str__(self) -> str:
        return f"{self.conversation_id}:{self.sequence_number}:{self.role}"