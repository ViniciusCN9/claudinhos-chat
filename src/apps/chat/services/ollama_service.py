from __future__ import annotations

from typing import Any

from django.conf import settings
import requests


class OllamaServiceError(Exception):
    pass


LLM_UNAVAILABLE_MESSAGE = (
    "Aviso: nenhum LLM esta disponivel para uso no momento. "
    "Verifique se o Ollama e um modelo local estao ativos para obter respostas reais."
)


def get_available_models() -> list[dict[str, str]]:
    return [dict(model) for model in settings.OLLAMA_MODEL_CATALOG]


def get_allowed_models() -> list[str]:
    return [model["name"] for model in get_available_models()]


def get_model_choices() -> list[tuple[str, str]]:
    return [(model["name"], model["label"]) for model in get_available_models()]


def get_model_config(model_name: str) -> dict[str, str]:
    for model in get_available_models():
        if model["name"] == model_name:
            return model
    raise OllamaServiceError("O modelo selecionado nao esta habilitado.")


def get_model_display_name(model_name: str) -> str:
    try:
        return get_model_config(model_name)["label"]
    except OllamaServiceError:
        return model_name


def is_local_model(model_name: str) -> bool:
    return get_model_config(model_name)["execution"] == "local"


def _build_request_context(model_name: str) -> tuple[dict[str, str], dict[str, str]]:
    model_config = get_model_config(model_name)
    execution = model_config["execution"]

    if execution == "cloud":
        if not settings.OLLAMA_API_KEY:
            raise OllamaServiceError(
                "Os modelos em nuvem exigem a variavel OLLAMA_API_KEY configurada."
            )
        return model_config, {
            "base_url": settings.OLLAMA_CLOUD_BASE_URL,
            "Authorization": f"Bearer {settings.OLLAMA_API_KEY}",
        }

    return model_config, {"base_url": settings.OLLAMA_BASE_URL}


def _post_ollama_request(
    *,
    base_url: str,
    path: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> requests.Response:
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    response = requests.post(
        f"{base_url}{path}",
        json=payload,
        headers=request_headers,
        timeout=settings.OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    return response


def activate_model(model_name: str) -> None:
    if not is_local_model(model_name):
        return

    _, request_context = _build_request_context(model_name)
    try:
        _post_ollama_request(
            base_url=request_context["base_url"],
            path="/api/generate",
            payload={
                "model": get_model_config(model_name)["api_model"],
                "prompt": "",
                "stream": False,
                "keep_alive": settings.OLLAMA_LOCAL_MODEL_KEEP_ALIVE,
            },
        )
    except requests.RequestException as exc:
        raise OllamaServiceError(
            f"Nao foi possivel carregar o modelo local {model_name}."
        ) from exc


def release_model(model_name: str) -> None:
    if not is_local_model(model_name):
        return

    _, request_context = _build_request_context(model_name)
    try:
        _post_ollama_request(
            base_url=request_context["base_url"],
            path="/api/generate",
            payload={
                "model": get_model_config(model_name)["api_model"],
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            },
        )
    except requests.RequestException:
        return


def validate_model_name(model_name: str) -> str:
    return get_model_config(model_name)["name"]


def request_chat_completion(model_name: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    validated_model = validate_model_name(model_name)

    try:
        model_config, request_context = _build_request_context(validated_model)
    except OllamaServiceError as exc:
        return {
            "model": validated_model,
            "content": str(exc),
            "raw": {},
            "unavailable": True,
            "error": str(exc),
        }

    if model_config["execution"] == "local":
        try:
            activate_model(validated_model)
        except OllamaServiceError as exc:
            return {
                "model": validated_model,
                "content": LLM_UNAVAILABLE_MESSAGE,
                "raw": {},
                "unavailable": True,
                "error": str(exc),
            }

    try:
        response = _post_ollama_request(
            base_url=request_context["base_url"],
            path="/api/chat",
            payload={
                "model": model_config["api_model"],
                "messages": messages,
                "stream": False,
                **(
                    {"keep_alive": settings.OLLAMA_LOCAL_MODEL_KEEP_ALIVE}
                    if model_config["execution"] == "local"
                    else {}
                ),
            },
            headers={
                key: value
                for key, value in request_context.items()
                if key != "base_url"
            },
        )
    except requests.RequestException as exc:
        return {
            "model": validated_model,
            "content": LLM_UNAVAILABLE_MESSAGE,
            "raw": {},
            "unavailable": True,
            "error": str(exc),
        }

    payload = response.json()
    message_payload = payload.get("message") or {}
    content = (message_payload.get("content") or "").strip()
    if not content:
        raise OllamaServiceError("O Ollama retornou uma resposta vazia.")

    return {
        "model": validated_model,
        "content": content,
        "raw": payload,
        "unavailable": False,
        "execution": model_config["execution"],
    }


def get_health_status() -> dict[str, Any]:
    local_status: dict[str, Any]
    try:
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags",
            timeout=max(5, min(settings.OLLAMA_TIMEOUT, 15)),
        )
        response.raise_for_status()
        payload = response.json()
        local_status = {
            "ok": True,
            "detail": "Ollama local disponivel.",
            "remote_models": [item.get("name", "") for item in payload.get("models", []) if item.get("name")],
        }
    except requests.RequestException as exc:
        local_status = {
            "ok": False,
            "detail": "Nao foi possivel conectar ao Ollama.",
            "error": str(exc),
        }

    cloud_status: dict[str, Any] = {
        "ok": False,
        "detail": "API key de nuvem nao configurada.",
    }
    if settings.OLLAMA_API_KEY:
        try:
            response = requests.get(
                f"{settings.OLLAMA_CLOUD_BASE_URL}/api/tags",
                headers={"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"},
                timeout=max(5, min(settings.OLLAMA_TIMEOUT, 15)),
            )
            response.raise_for_status()
            payload = response.json()
            cloud_status = {
                "ok": True,
                "detail": "Ollama cloud disponivel.",
                "remote_models": [item.get("name", "") for item in payload.get("models", []) if item.get("name")],
            }
        except requests.RequestException as exc:
            cloud_status = {
                "ok": False,
                "detail": "Nao foi possivel conectar a API cloud do Ollama.",
                "error": str(exc),
            }

    return {
        "ok": local_status["ok"] or cloud_status["ok"],
        "detail": "Ao menos um provedor de modelos esta disponivel."
        if local_status["ok"] or cloud_status["ok"]
        else "Nenhum provedor de modelos esta disponivel.",
        "available_models": get_available_models(),
        "local": local_status,
        "cloud": cloud_status,
    }