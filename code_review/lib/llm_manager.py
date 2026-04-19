import json
import time
from typing import Any

import requests

# Временные сбои провайдера / шлюза (OpenRouter может вернуть error в JSON с code 524 и т.п.)
_RETRYABLE_HTTP_STATUSES = frozenset({408, 409, 429, 500, 502, 503, 504, 520, 522, 524})
_RETRYABLE_ERROR_CODES = frozenset({408, 409, 429, 500, 502, 503, 504, 520, 522, 524})


def _coerce_int_code(code: Any) -> int | None:
    if code is None:
        return None
    if isinstance(code, bool):
        return None
    if isinstance(code, int):
        return code
    if isinstance(code, str) and code.isdigit():
        return int(code)
    return None


def _should_retry_http_status(status: int) -> bool:
    return status in _RETRYABLE_HTTP_STATUSES


def _should_retry_openrouter_error(err: dict[str, Any]) -> bool:
    code = _coerce_int_code(err.get("code"))
    if code is not None and code in _RETRYABLE_ERROR_CODES:
        return True
    msg = (err.get("message") or "").lower()
    return any(
        s in msg
        for s in (
            "timeout",
            "timed out",
            "overloaded",
            "provider",
            "try again",
            "temporarily",
            "rate limit",
        )
    )


def _sleep_backoff(attempt: int) -> None:
    delay = min(2.0 ** min(attempt - 1, 6), 45.0)
    time.sleep(delay)


def _extract_content_from_message(message: dict[str, Any]) -> str | None:
    """Достаёт текст ответа из OpenAI-совместимого message (строка или список частей)."""
    if not message:
        return None
    raw = message.get("content")
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for block in raw:
            if isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(str(block["text"]))
                elif "text" in block:
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts) if parts else None
    return str(raw)


class LLMAPIManager:
    def __init__(self, api_key, nodel_id):
        self.api_key = api_key
        self.model_id = nodel_id

    def get_response(self, prompt):
        max_attempts = 8
        for attempt in range(1, max_attempts + 1):
            # TODO: системные сообщения к модели user/tool/dev/system
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": prompt}],
                }),
                timeout=180,
            )

            if response.status_code != 200:
                if (
                    _should_retry_http_status(response.status_code)
                    and attempt < max_attempts
                ):
                    print(
                        f"[WARN] Попытка {attempt}/{max_attempts}: HTTP "
                        f"{response.status_code}, повтор через backoff…"
                    )
                    _sleep_backoff(attempt)
                    continue
                raise RuntimeError(
                    f"Ошибка OpenRouter API: {response.status_code} - {response.text}"
                )

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                if attempt < max_attempts:
                    print(
                        f"[WARN] Попытка {attempt}/{max_attempts}: не-JSON ответ, повтор…"
                    )
                    _sleep_backoff(attempt)
                    continue
                raise RuntimeError(
                    f"OpenRouter вернул не-JSON: {response.text[:2000]}"
                ) from e

            if not isinstance(data, dict):
                raise RuntimeError(
                    f"OpenRouter: неожиданный ответ (не объект): {response.text[:2000]}"
                )

            if "error" in data:
                err = data["error"]
                if isinstance(err, dict):
                    msg = err.get("message", json.dumps(err, ensure_ascii=False))
                    code = err.get("code", "")
                    extra = f" ({code})" if code else ""
                    if _should_retry_openrouter_error(err) and attempt < max_attempts:
                        print(
                            f"[WARN] Попытка {attempt}/{max_attempts}: "
                            f"временная ошибка провайдера{extra}: {msg}. Повтор…"
                        )
                        _sleep_backoff(attempt)
                        continue
                else:
                    msg = str(err)
                    extra = ""
                raise RuntimeError(f"Ошибка OpenRouter API{extra}: {msg}")

            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                if attempt < max_attempts:
                    print(
                        f"[WARN] Попытка {attempt}/{max_attempts}: нет choices, повтор…"
                    )
                    _sleep_backoff(attempt)
                    continue
                raise RuntimeError(
                    "OpenRouter: в ответе нет поля choices (возможно, сбой провайдера или "
                    f"другой формат). Фрагмент ответа: {response.text[:2000]}"
                )

            first = choices[0]
            if not isinstance(first, dict):
                raise RuntimeError(
                    "OpenRouter: choices[0] имеет неожиданный формат. "
                    f"Фрагмент ответа: {response.text[:2000]}"
                )
            raw_msg = first.get("message")
            message = raw_msg if isinstance(raw_msg, dict) else {}
            content = _extract_content_from_message(message)

            if content is None or (isinstance(content, str) and not content.strip()):
                refusal = message.get("refusal")
                if refusal:
                    raise RuntimeError(f"Модель отказала ответить: {refusal}")
                raise RuntimeError(
                    "OpenRouter: пустой content в ответе модели. "
                    f"Фрагмент ответа: {response.text[:2000]}"
                )

            # Пробуем распарсить JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(
                    f"[WARN] Попытка {attempt}/{max_attempts}: модель вернула невалидный JSON, "
                    "пробуем снова"
                )
                print(f"Content={content}")
                if attempt >= max_attempts:
                    raise RuntimeError(
                        f"Максимальное число попыток превышено ({max_attempts})"
                    ) from e
                time.sleep(1)

                prompt = "Исправь некорректный возвращенный json, json должен быть строго в формате" \
                "{\n" \
                "  \"comments\": [\n" \
                "    {\n" \
                "      \"file\": \"<путь_к_файлу>\",\n" \
                "      \"line\": <номер_строки>,\n" \
                "      \"comment\": \"<markdown-комментарий>\",\n" \
                "      \"suggestion\": \"<предлагаемый diff или исправление кода>\"\n" \
                "    }\n" \
                "  ],\n" \
                "  \"summary\": \"<markdown-резюме с общими выводами>\"\n" \
                "}\n\n" \
                f"Ошибка: {e}" \
                f"JSON: {content}"