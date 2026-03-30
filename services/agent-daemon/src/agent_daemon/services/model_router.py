"""Model routing and provider integrations for chat responses."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderStatus:
    provider_id: str
    is_available: bool
    detail: str
    model_id: str = ""


@dataclass(frozen=True)
class ChatCompletion:
    content: str
    provider_id: str
    model_id: str


class ChatProvider:
    provider_id = ""

    def status(self) -> ProviderStatus:
        raise NotImplementedError

    def complete(self, prompt: str) -> ChatCompletion:
        raise NotImplementedError


class PlaceholderProvider(ChatProvider):
    provider_id = "placeholder"

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            provider_id=self.provider_id,
            is_available=True,
            detail="Fallback placeholder chat response is available.",
            model_id="placeholder-echo-v1",
        )

    def complete(self, prompt: str) -> ChatCompletion:
        prompt_summary = prompt.strip() or "your last message"
        return ChatCompletion(
            content=(
                "Thanks! I received your message and the daemon chat loop is working. "
                f"(Echo summary: \"{prompt_summary[:120]}\")"
            ),
            provider_id=self.provider_id,
            model_id="placeholder-echo-v1",
        )


class OllamaProvider(ChatProvider):
    provider_id = "ollama"

    def __init__(self, base_url: str, model_id: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id

    def status(self) -> ProviderStatus:
        request = urllib.request.Request(
            url=f"{self._base_url}/api/tags",
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=2.0) as response:  # noqa: S310
                _ = response.read()
        except urllib.error.URLError:
            return ProviderStatus(
                provider_id=self.provider_id,
                is_available=False,
                detail=(
                    "Ollama is not reachable. Please install Ollama and start it first "
                    "(for example, run `ollama serve`)."
                ),
                model_id=self._model_id,
            )

        return ProviderStatus(
            provider_id=self.provider_id,
            is_available=True,
            detail="Ollama is running and ready for local model requests.",
            model_id=self._model_id,
        )

    def complete(self, prompt: str) -> ChatCompletion:
        payload = json.dumps(
            {
                "model": self._model_id,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            url=f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=60.0) as response:  # noqa: S310
            raw = response.read()

        parsed = json.loads(raw.decode("utf-8"))
        generated_text = str(parsed.get("response", "")).strip()
        if not generated_text:
            generated_text = "Ollama returned an empty response. Please try again with a more specific prompt."

        return ChatCompletion(
            content=generated_text,
            provider_id=self.provider_id,
            model_id=self._model_id,
        )


class ModelRouter:
    """Routes chat requests to providers according to app settings."""

    def __init__(self, *, ollama_base_url: str, default_ollama_model: str) -> None:
        self._placeholder_provider = PlaceholderProvider()
        self._ollama_base_url = ollama_base_url
        self._default_ollama_model = default_ollama_model

    def get_status(self) -> list[ProviderStatus]:
        ollama_provider = OllamaProvider(
            base_url=self._ollama_base_url,
            model_id=self._default_ollama_model,
        )
        return [ollama_provider.status(), self._placeholder_provider.status()]

    def complete(self, prompt: str, settings_payload: dict) -> ChatCompletion:
        local_provider = self._resolve_local_provider(settings_payload)
        if local_provider is None:
            return self._placeholder_provider.complete(prompt)

        status = local_provider.status()
        if status.is_available:
            try:
                return local_provider.complete(prompt)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass

        fallback = self._placeholder_provider.complete(prompt)
        return ChatCompletion(
            content=(
                f"{status.detail}\n\n"
                "I used the built-in placeholder responder instead so chat still works.\n\n"
                f"{fallback.content}"
            ),
            provider_id=fallback.provider_id,
            model_id=fallback.model_id,
        )

    def _resolve_local_provider(self, settings_payload: dict) -> ChatProvider | None:
        provider_preference = str(settings_payload.get("provider_preference", "")).strip()
        if provider_preference == "PROVIDER_PREFERENCE_CLOUD_PREFERRED":
            return None

        providers = settings_payload.get("providers", [])
        for provider in providers:
            if not isinstance(provider, dict):
                continue

            provider_id = str(provider.get("provider_id", "")).strip().lower()
            display_name = str(provider.get("display_name", "")).strip().lower()

            if "ollama" not in provider_id and "ollama" not in display_name:
                continue

            model_id = self._extract_model_id(provider_id) or self._extract_model_id(display_name)
            return OllamaProvider(
                base_url=self._ollama_base_url,
                model_id=model_id or self._default_ollama_model,
            )

        return OllamaProvider(
            base_url=self._ollama_base_url,
            model_id=self._default_ollama_model,
        )

    @staticmethod
    def _extract_model_id(value: str) -> str:
        for separator in (":", "/"):
            if separator in value:
                candidate = value.split(separator, maxsplit=1)[1].strip()
                if candidate and candidate != "ollama":
                    return candidate
        return ""
