from http import HTTPStatus
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
import requests

from apps.chat.models import Conversation
from apps.chat.services.ollama_service import LLM_UNAVAILABLE_MESSAGE


TEST_MODEL_CATALOG = [
    {"name": "gemma3:1b", "label": "Local", "execution": "local", "api_model": "gemma3:1b"},
    {"name": "gemma4:31b-cloud", "label": "Cloud", "execution": "cloud", "api_model": "gemma4:31b"},
]


@override_settings(OLLAMA_MODEL_CATALOG=TEST_MODEL_CATALOG, OLLAMA_AVAILABLE_MODELS=[item["name"] for item in TEST_MODEL_CATALOG])
class ChatViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_loads(self):
        response = self.client.get(reverse("chat:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Claudinhos Chat")
        self.assertContains(response, "Local")
        self.assertContains(response, "Cloud")
        self.assertIsNone(response.context["selected_conversation"])

    def test_create_conversation_returns_json(self):
        response = self.client.post(
            reverse("chat:conversation_list_create"),
            data={"content": "Projeto", "model_name": "gemma4:31b-cloud"},
            HTTP_ACCEPT="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["title"], "Chat #001")
        self.assertEqual(payload["model_name"], "gemma4:31b-cloud")

    @patch("apps.chat.services.conversation_service.request_chat_completion")
    def test_send_message_returns_json_payload(self, mocked_completion):
        mocked_completion.return_value = {
            "model": "gemma3:1b",
            "content": "Tudo certo por aqui.",
            "raw": {},
            "execution": "local",
        }
        conversation = Conversation.objects.create(
            title="Projeto",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=120,
            available_models_snapshot=TEST_MODEL_CATALOG,
        )

        response = self.client.post(
            reverse("chat:message_create", kwargs={"conversation_id": conversation.id}),
            data={"content": "Status?"},
            HTTP_ACCEPT="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["assistant_message"]["content"], "Tudo certo por aqui.")
        self.assertEqual(payload["assistant_message"]["model"], "Local")

    @patch("apps.chat.services.ollama_service.requests.post")
    def test_send_message_returns_warning_payload_when_llm_is_unavailable(self, mocked_post):
        mocked_post.side_effect = requests.RequestException("offline")
        conversation = Conversation.objects.create(
            title="Projeto",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=120,
            available_models_snapshot=TEST_MODEL_CATALOG,
        )

        response = self.client.post(
            reverse("chat:message_create", kwargs={"conversation_id": conversation.id}),
            data={"content": "Status?"},
            HTTP_ACCEPT="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["assistant_message"]["content"], LLM_UNAVAILABLE_MESSAGE)

    def test_switch_model_returns_forbidden_when_chat_already_started(self):
        conversation = Conversation.objects.create(
            title="Projeto",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=120,
            available_models_snapshot=TEST_MODEL_CATALOG,
        )

        response = self.client.post(
            reverse("chat:conversation_model_update", kwargs={"conversation_id": conversation.id}),
            data={"switch-model_name": "gemma4:31b-cloud"},
            HTTP_ACCEPT="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        payload = response.json()
        self.assertIn("desabilitado", payload["error"])

    def test_rename_conversation_returns_forbidden(self):
        conversation = Conversation.objects.create(
            title="Chat #001",
            model_name="gemma3:1b",
            system_prompt="Sistema",
            context_limit_tokens=120,
            available_models_snapshot=TEST_MODEL_CATALOG,
        )

        response = self.client.post(
            reverse("chat:conversation_title_update", kwargs={"conversation_id": conversation.id}),
            data={"title": "Planejamento"},
            HTTP_ACCEPT="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        conversation.refresh_from_db()
        self.assertEqual(conversation.title, "Chat #001")