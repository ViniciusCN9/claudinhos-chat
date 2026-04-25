from __future__ import annotations

import re

from django.conf import settings
from django.db.models import Max

from apps.chat.models import Conversation, Message
from apps.chat.services.context_service import build_conversation_context, estimate_token_count
from apps.chat.services.ollama_service import (
    OllamaServiceError,
    activate_model,
    get_available_models,
    is_local_model,
    release_model,
    request_chat_completion,
    validate_model_name,
)


CHAT_TITLE_PATTERN = re.compile(r"^Chat #(\d+)$")


def list_conversations():
    return Conversation.objects.filter(is_archived=False).prefetch_related("messages")


def get_conversation(conversation_id):
    return Conversation.objects.prefetch_related("messages").get(pk=conversation_id, is_archived=False)


def _next_chat_title() -> str:
    current_max = 0
    for title in Conversation.objects.filter(title__startswith="Chat #").values_list("title", flat=True):
        match = CHAT_TITLE_PATTERN.match(title)
        if match:
            current_max = max(current_max, int(match.group(1)))
    return f"Chat #{current_max + 1:03d}"


def create_conversation(*, title: str | None = None, model_name: str) -> Conversation:
    validated_model = validate_model_name(model_name)
    if is_local_model(validated_model):
        activate_model(validated_model)
    normalized_title = (title or "").strip() or _next_chat_title()
    return Conversation.objects.create(
        title=normalized_title,
        model_name=validated_model,
        system_prompt=settings.CHAT_DEFAULT_SYSTEM_PROMPT,
        context_limit_tokens=settings.CHAT_CONTEXT_LIMIT_TOKENS,
        available_models_snapshot=get_available_models(),
    )


def update_conversation_model(*, conversation: Conversation, model_name: str) -> Conversation:
    validated_model = validate_model_name(model_name)
    current_model = conversation.model_name
    if current_model == validated_model:
        return conversation

    if is_local_model(current_model):
        release_model(current_model)

    if is_local_model(validated_model):
        activate_model(validated_model)

    conversation.model_name = validated_model
    conversation.available_models_snapshot = get_available_models()
    conversation.save(update_fields=["model_name", "available_models_snapshot", "updated_at"])
    return conversation


def rename_conversation(*, conversation: Conversation, title: str) -> Conversation:
    normalized_title = (title or "").strip()
    if not normalized_title:
        raise OllamaServiceError("O nome do chat nao pode estar vazio.")

    if conversation.title == normalized_title:
        return conversation

    conversation.title = normalized_title
    conversation.save(update_fields=["title", "updated_at"])
    return conversation


def _next_sequence_number(conversation: Conversation) -> int:
    last_sequence = conversation.messages.aggregate(max_sequence=Max("sequence_number"))["max_sequence"]
    return (last_sequence or 0) + 1


def send_message(*, conversation: Conversation, content: str) -> tuple[Message, Message]:
    normalized_content = (content or "").strip()
    if not normalized_content:
        raise OllamaServiceError("A mensagem nao pode estar vazia.")

    user_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=normalized_content,
        sequence_number=_next_sequence_number(conversation),
        input_tokens_estimated=estimate_token_count(normalized_content),
    )

    context_messages = build_conversation_context(conversation)
    completion = request_chat_completion(conversation.model_name, context_messages)

    assistant_content = completion["content"]
    assistant_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=assistant_content,
        sequence_number=_next_sequence_number(conversation),
        output_tokens_estimated=estimate_token_count(assistant_content),
        metadata_json={
            "model": completion["model"],
            "unavailable": completion.get("unavailable", False),
            "execution": completion.get("execution", "local"),
        },
    )

    return user_message, assistant_message