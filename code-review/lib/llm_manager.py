import json
import time

import requests


class LLMAPIManager:
    def __init__(self, api_key, nodel_id):
        self.api_key = api_key
        self.model_id = nodel_id

    def get_response(self, prompt):
        for attempt in range(1, 4):
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
                raise RuntimeError(
                    f"Ошибка OpenRouter API: {response.status_code} - {response.text}"
                )

            content = response.json()["choices"][0]["message"]["content"]

            # Пробуем распарсить JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"[WARN] Попытка {attempt}: модель вернула невалидный JSON, пробуем снова...")
                time.sleep(1)

                prompt = "Исправь некорректный возвращенный json, json должен быть в формате"
                "{\n"
                "  \"comments\": [\n"
                "    {\n"
                "      \"file\": \"<путь_к_файлу>\",\n"
                "      \"line\": <номер_строки>,\n"
                "      \"comment\": \"<markdown-комментарий>\",\n"
                "      \"suggestion\": \"<предлагаемый diff или исправление кода>\"\n"
                "    }\n"
                "  ],\n"
                "  \"summary\": \"<markdown-резюме с общими выводами>\"\n"
                "}\n\n"
                f"Ошибка: {e}"
                f"JSON: {content}"

                if attempt == 3:
                    raise RuntimeError(
                        f"Максимальное число попыток превышено, попыток было {attempt}"
                    )