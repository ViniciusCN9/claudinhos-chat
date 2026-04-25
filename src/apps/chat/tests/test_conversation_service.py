from unittest.mock import patch

from django.test import TestCase, override_settings
import requests

from apps.chat.models import Conversation, Message
from apps.chat.services.conversation_service import create_conversation, send_message, update_conversation_model
from apps.chat.services.ollama_service import LLM_UNAVAILABLE_MESSAGE, OllamaServiceError


TEST_MODEL_CATALOG = [
    {"name": "gemma3:1b", "label": "Local", "execution": "local", "api_model": "gemma3:1b"},
    {"name": "gemma4:31b-cloud", "label": "Cloud", "execution": "cloud", "api_model": "gemma4:31b"},
]


@override_settings(OLLAMA_MODEL_CATALOG=TEST_MODEL_CATALOG, OLLAMA_AVAILABLE_MODELS=[item["name"] for item in TEST_MODEL_CATALOG])
class ConversationServiceTests(TestCase):
    def test_create_conversation_rejects_disabled_model(self):
        with self.assertRaises(OllamaServiceError):
            create_conversation(title="Teste", model_name="modelo-invalido")

    @patch("apps.chat.services.conversation_service.activate_model")
    def test_create_conversation_carrega_modelo_local_ao_selecionar(self, mocked_activate_model):
        conversation = create_conversation(model_name="gemma3:1b")

        self.assertEqual(conversation.model_name, "gemma3:1b")
        self.assertEqual(conversation.title, "Chat #001")
        self.assertEqual(conversation.available_models_snapshot, TEST_MODEL_CATALOG)
        mocked_activate_model.assert_called_once_with("gemma3:1b")

    @patch("apps.chat.services.conversation_service.request_chat_completion")
    def test_send_message_persists_user_and_assistant_messages(self, mocked_completion):
        mocked_completion.return_value = {
            "model": "gemma3:1b",
            "content": "Resposta local",
            "raw": {},
            "execution": "local",
        }
        conversation = Conversation.objects.create(
            title="Chat #001",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=120,
            available_models_snapshot=TEST_MODEL_CATALOG,
        )

        user_message, assistant_message = send_message(conversation=conversation, content="Primeira pergunta")

        conversation.refresh_from_db()
        self.assertEqual(user_message.sequence_number, 1)
        self.assertEqual(assistant_message.sequence_number, 2)
        self.assertEqual(conversation.title, "Chat #001")
        self.assertEqual(Message.objects.filter(conversation=conversation).count(), 2)

    @patch("apps.chat.services.ollama_service.requests.post")
    def test_send_message_returns_warning_when_llm_is_unavailable(self, mocked_post):
        mocked_post.side_effect = requests.RequestException("offline")
        conversation = Conversation.objects.create(
            title="Projeto",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=120,
            available_models_snapshot=TEST_MODEL_CATALOG,
        )

        _, assistant_message = send_message(conversation=conversation, content="Status?")

        self.assertEqual(assistant_message.content, LLM_UNAVAILABLE_MESSAGE)
        self.assertTrue(assistant_message.metadata_json["unavailable"])

    @patch("apps.chat.services.conversation_service.activate_model")
    @patch("apps.chat.services.conversation_service.release_model")
    def test_update_conversation_model_unloads_local_anterior(self, mocked_release_model, mocked_activate_model):
        conversation = Conversation.objects.create(
            title="Projeto",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=120,
            available_models_snapshot=TEST_MODEL_CATALOG,
        )

        update_conversation_model(conversation=conversation, model_name="gemma4:31b-cloud")

        conversation.refresh_from_db()
        self.assertEqual(conversation.model_name, "gemma4:31b-cloud")
        self.assertEqual(conversation.available_models_snapshot, TEST_MODEL_CATALOG)
        mocked_release_model.assert_called_once_with("gemma3:1b")
        mocked_activate_model.assert_not_called()