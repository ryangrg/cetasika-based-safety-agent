"""
Unified LLM client — wraps Anthropic and OpenAI-compatible APIs
(Ollama, LM Studio, etc.) behind a single interface.
"""

import re


class LLMClient:
    """Provider-agnostic LLM client."""

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-6",
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.provider = provider
        self.model = model

        if provider == "anthropic":
            import anthropic
            self._anthropic = anthropic.Anthropic(api_key=api_key)
        elif provider in ("ollama", "openai"):
            import openai
            kwargs = {}
            if provider == "ollama":
                kwargs["base_url"] = base_url or "http://localhost:11434/v1"
                kwargs["api_key"] = api_key or "ollama"
            else:
                if base_url:
                    kwargs["base_url"] = base_url
                if api_key:
                    kwargs["api_key"] = api_key
            self._openai = openai.OpenAI(**kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'anthropic', 'ollama', or 'openai'.")

    @property
    def model_name(self) -> str:
        """Model name sanitized for use in filenames."""
        return re.sub(r'[^a-zA-Z0-9._-]', '-', self.model)

    def chat(self, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        """Send a chat request and return the response text."""
        if self.provider == "anthropic":
            response = self._anthropic.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        else:
            # OpenAI-compatible format (Ollama, OpenAI, LM Studio, etc.)
            oai_messages = [{"role": "system", "content": system}]
            for msg in messages:
                oai_messages.append({"role": msg["role"], "content": msg["content"]})
            response = self._openai.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=oai_messages,
            )
            return response.choices[0].message.content
