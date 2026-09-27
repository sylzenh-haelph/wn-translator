import json
import os
import re

import requests


class GeminiClient:
    def __init__(
        self,
        model="gemini-3.5-flash-lite",
        api_key=None,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY belum tersedia."
            )

        self.url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{self.model}:generateContent"
        )

    def generate(self, prompt):
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        response = requests.post(
            self.url,
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        return self._extract_text(data)

    @staticmethod
    def _extract_text(data):
        candidates = data.get("candidates", [])

        if not candidates:
            raise RuntimeError(
                "API tidak mengembalikan candidate."
            )

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        texts = []

        for part in parts:
            if part.get("thought"):
                continue

            text = part.get("text")

            if text:
                texts.append(text)

        if not texts:
            raise RuntimeError(
                "Tidak menemukan output text dari model."
            )

        return texts[-1]


def extract_json(text):
    """
    Parse JSON langsung.
    Jika model membungkus JSON dengan ```json ... ```,
    wrapper tersebut dibersihkan.
    """

    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    return json.loads(text)
