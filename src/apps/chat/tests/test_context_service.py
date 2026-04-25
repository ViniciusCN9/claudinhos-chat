from django.test import TestCase

from apps.chat.models import Conversation, Message
from apps.chat.services.context_service import build_conversation_context


class BuildConversationContextTests(TestCase):
    def test_keeps_latest_messages_within_budget(self):
        conversation = Conversation.objects.create(
            title="Teste",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=6,
            available_models_snapshot=[{"name": "gemma3:1b", "label": "local (gemma3:1b)", "execution": "local", "api_model": "gemma3:1b"}],
        )

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="1234",
            sequence_number=1,
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="12345678",
            sequence_number=2,
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="123456789012",
            sequence_number=3,
        )

        context = build_conversation_context(conversation)

        self.assertEqual(
            context,
            [
                {"role": "system", "content": "Sistema"},
                {"role": "user", "content": "123456789012"},
            ],
        )