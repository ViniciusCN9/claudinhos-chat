from __future__ import annotations

from http import HTTPStatus

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ConversationCreateForm, MessageForm
from .services.conversation_service import (
    create_conversation,
    get_conversation,
    list_conversations,
    send_message,
)
from .services.ollama_service import (
    OllamaServiceError,
    get_available_models,
    get_health_status,
    get_model_config,
    get_model_display_name,
)


def _wants_json(request) -> bool:
    accept_header = request.headers.get("Accept", "")
    requested_with = request.headers.get("X-Requested-With", "")
    return "application/json" in accept_header or requested_with == "XMLHttpRequest"


def _build_page_context(*, request, selected_conversation=None, message_form=None, create_form=None):
    return {
        "conversations": list_conversations(),
        "selected_conversation": selected_conversation,
        "selected_model": get_model_config(selected_conversation.model_name) if selected_conversation else None,
        "messages": selected_conversation.messages.all() if selected_conversation else [],
        "conversation_form": create_form or ConversationCreateForm(),
        "message_form": message_form or MessageForm(),
        "available_models": get_available_models(),
    }


@require_GET
def home(request):
    context = _build_page_context(request=request)
    return render(request, "chat/index.html", context)


@require_http_methods(["GET"])
def conversation_detail(request, conversation_id):
    try:
        conversation = get_conversation(conversation_id)
    except Exception as exc:
        raise Http404("Conversa nao encontrada.") from exc

    context = _build_page_context(request=request, selected_conversation=conversation)
    return render(request, "chat/index.html", context)


@require_http_methods(["GET", "POST"])
def conversation_list_create(request):
    if request.method == "GET":
        data = [
            {
                "id": str(conversation.id),
                "title": conversation.title,
                "model_name": conversation.model_name,
                "model_label": conversation.model_label,
                "updated_at": conversation.updated_at.isoformat(),
            }
            for conversation in list_conversations()
        ]
        return JsonResponse({"conversations": data})

    form = ConversationCreateForm(request.POST)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({"errors": form.errors}, status=HTTPStatus.BAD_REQUEST)
        context = _build_page_context(request=request, create_form=form)
        return render(request, "chat/index.html", context, status=HTTPStatus.BAD_REQUEST)

    try:
        conversation = create_conversation(
            model_name=form.cleaned_data["model_name"],
        )
        if not _wants_json(request):
            send_message(
                conversation=conversation,
                content=form.cleaned_data["content"],
            )
    except OllamaServiceError as exc:
        if _wants_json(request):
            return JsonResponse({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
        context = _build_page_context(request=request, create_form=form)
        context["assistant_error"] = str(exc)
        return render(request, "chat/index.html", context, status=HTTPStatus.BAD_GATEWAY)

    if _wants_json(request):
        return JsonResponse(
            {
                "id": str(conversation.id),
                "title": conversation.title,
                "model_name": conversation.model_name,
                "detail_url": request.build_absolute_uri(conversation.get_absolute_url())
                if hasattr(conversation, "get_absolute_url")
                else request.build_absolute_uri(f"/conversations/{conversation.id}/"),
            },
            status=HTTPStatus.CREATED,
        )

    return redirect("chat:conversation_detail", conversation_id=conversation.id)


@require_http_methods(["POST"])
def conversation_title_update(request, conversation_id):
    try:
        conversation = get_conversation(conversation_id)
    except Exception as exc:
        raise Http404("Conversa nao encontrada.") from exc

    message = "Renomear chats pela interface foi desabilitado."
    if _wants_json(request):
        return JsonResponse({"error": message}, status=HTTPStatus.FORBIDDEN)

    context = _build_page_context(request=request, selected_conversation=conversation)
    context["assistant_error"] = message
    return render(request, "chat/index.html", context, status=HTTPStatus.FORBIDDEN)


@require_http_methods(["POST"])
def message_create(request, conversation_id):
    try:
        conversation = get_conversation(conversation_id)
    except Exception as exc:
        raise Http404("Conversa nao encontrada.") from exc

    form = MessageForm(request.POST)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({"errors": form.errors}, status=HTTPStatus.BAD_REQUEST)
        context = _build_page_context(request=request, selected_conversation=conversation, message_form=form)
        return render(request, "chat/index.html", context, status=HTTPStatus.BAD_REQUEST)

    try:
        user_message, assistant_message = send_message(
            conversation=conversation,
            content=form.cleaned_data["content"],
        )
    except OllamaServiceError as exc:
        if _wants_json(request):
            return JsonResponse({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
        context = _build_page_context(request=request, selected_conversation=conversation, message_form=form)
        context["assistant_error"] = str(exc)
        return render(request, "chat/index.html", context, status=HTTPStatus.BAD_GATEWAY)

    if _wants_json(request):
        return JsonResponse(
            {
                "user_message": {
                    "id": str(user_message.id),
                    "role": user_message.role,
                    "content": user_message.content,
                },
                "assistant_message": {
                    "id": str(assistant_message.id),
                    "role": assistant_message.role,
                    "content": assistant_message.content,
                    "model": get_model_display_name(
                        assistant_message.metadata_json.get("model", conversation.model_name)
                    ),
                    "unavailable": assistant_message.metadata_json.get("unavailable", False),
                },
            },
            status=HTTPStatus.CREATED,
        )

    return redirect("chat:conversation_detail", conversation_id=conversation.id)


@require_http_methods(["POST"])
def conversation_model_update(request, conversation_id):
    try:
        conversation = get_conversation(conversation_id)
    except Exception as exc:
        raise Http404("Conversa nao encontrada.") from exc

    message = "Trocar o modelo apos iniciar o chat foi desabilitado."
    if _wants_json(request):
        return JsonResponse({"error": message}, status=HTTPStatus.FORBIDDEN)

    context = _build_page_context(request=request, selected_conversation=conversation)
    context["assistant_error"] = message
    return render(request, "chat/index.html", context, status=HTTPStatus.FORBIDDEN)


@require_GET
def models_list(request):
    return JsonResponse({"models": get_available_models()})


@require_GET
def health_check(request):
    health = get_health_status()
    status = HTTPStatus.OK if health.get("ok") else HTTPStatus.BAD_GATEWAY
    return JsonResponse(health, status=status)