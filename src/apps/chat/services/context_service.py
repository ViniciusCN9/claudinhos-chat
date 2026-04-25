from __future__ import annotations

import math

from apps.chat.models import Conversation


def estimate_token_count(text: str) -> int:
    normalized = " ".join((text or "").split())
    if not normalized:
        return 0
    return max(1, math.ceil(len(normalized) / 4))


def build_conversation_context(conversation: Conversation) -> list[dict[str, str]]:
    budget = conversation.context_limit_tokens
    context: list[dict[str, str]] = []

    if conversation.system_prompt:
        system_tokens = estimate_token_count(conversation.system_prompt)
        if system_tokens < budget:
            context.append({"role": "system", "content": conversation.system_prompt})
            budget -= system_tokens

    selected_messages: list[dict[str, str]] = []
    for message in conversation.messages.order_by("-sequence_number"):
        token_cost = estimate_token_count(message.content)
        if token_cost > budget:
            break
        selected_messages.append({"role": message.role, "content": message.content})
        budget -= token_cost

    context.extend(reversed(selected_messages))
    return context