import json
import os
import re
import time

import requests


class GeminiClient:
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        model="gemini-3.5-flash-lite",
        api_key=None,
        max_retries=3,
        timeout=120,
        backoff_base=2.0,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY belum tersedia.")

        if max_retries < 0:
            raise ValueError("max_retries tidak boleh negatif.")

        if timeout <= 0:
            raise ValueError("timeout harus lebih besar dari 0.")

        if backoff_base <= 0:
            raise ValueError("backoff_base harus lebih besar dari 0.")

        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_base = backoff_base

        self.url = (
            f"https://generativelanguage.googleapis.com/"
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
                "thinkingConfig": {
                    "thinkingLevel": "minimal"
                },
                "responseMimeType": "application/json",
            },
        }

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = self._build_api_error(response)

                    if attempt >= self.max_retries:
                        break

                    self._sleep_before_retry(response, attempt)
                    continue

                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError as exc:
                    raise RuntimeError(
                        "API mengembalikan response yang bukan JSON."
                    ) from exc

                return self._extract_text(data)

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = RuntimeError(
                    f"Koneksi ke Gemini gagal: {exc}"
                )

                if attempt >= self.max_retries:
                    break

                self._sleep_before_retry(
                    response=None,
                    attempt=attempt,
                )

            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Request ke Gemini gagal: {exc}"
                ) from exc

        raise last_error or RuntimeError(
            "Request ke Gemini gagal setelah seluruh retry."
        )

    def _sleep_before_retry(self, response, attempt):
        retry_after = self._get_retry_after(response)

        if retry_after is not None:
            delay = retry_after
        else:
            delay = self.backoff_base * (2 ** attempt)

        delay = min(delay, 60.0)

        print(
            f"  Gemini retry {attempt + 1}/{self.max_retries} "
            f"dalam {delay:.1f}s..."
        )

        time.sleep(delay)

    @staticmethod
    def _get_retry_after(response):
        if response is None:
            return None

        value = response.headers.get("Retry-After")

        if value is None:
            return None

        try:
            delay = float(value)
        except (TypeError, ValueError):
            return None

        if delay < 0:
            return None

        return delay

    @staticmethod
    def _build_api_error(response):
        status = response.status_code

        try:
            data = response.json()
            message = (
                data.get("error", {}).get("message")
                or data.get("message")
            )
        except (ValueError, AttributeError):
            message = None

        if message:
            return RuntimeError(
                f"Gemini API HTTP {status}: {message}"
            )

        return RuntimeError(f"Gemini API HTTP {status}.")

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



class OpenRouterClient:
    RETRYABLE_STATUS_CODES={429,500,502,503,504}
    URL="https://openrouter.ai/api/v1/chat/completions"

    def __init__(self,model,api_key=None,max_retries=3,
                 timeout=120,backoff_base=2.0):
        self.model=model
        self.api_key=api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY belum tersedia.")
        if max_retries<0:
            raise ValueError("max_retries tidak boleh negatif.")
        if timeout<=0:
            raise ValueError("timeout harus lebih besar dari 0.")
        if backoff_base<=0:
            raise ValueError("backoff_base harus lebih besar dari 0.")
        self.max_retries=max_retries
        self.timeout=timeout
        self.backoff_base=backoff_base
        self.url=self.URL

    def generate(self,prompt):
        payload={
            "model":self.model,
            "messages":[{"role":"user","content":prompt}],
            "response_format":{"type":"json_object"},
        }
        headers={
            "Authorization":f"Bearer {self.api_key}",
            "Content-Type":"application/json",
        }
        last_error=None

        for attempt in range(self.max_retries+1):
            try:
                response=requests.post(
                    self.url,headers=headers,
                    json=payload,timeout=self.timeout
                )

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error=self._build_api_error(response)
                    if attempt>=self.max_retries:
                        break
                    self._sleep_before_retry(response,attempt)
                    continue

                response.raise_for_status()

                try:
                    data=response.json()
                except ValueError as exc:
                    raise RuntimeError(
                        "OpenRouter mengembalikan response yang bukan JSON."
                    ) from exc

                return self._extract_text(data)

            except (requests.Timeout,requests.ConnectionError) as exc:
                last_error=RuntimeError(
                    f"Koneksi ke OpenRouter gagal: {exc}"
                )
                if attempt>=self.max_retries:
                    break
                self._sleep_before_retry(None,attempt)

            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Request ke OpenRouter gagal: {exc}"
                ) from exc

        raise last_error or RuntimeError(
            "Request ke OpenRouter gagal setelah seluruh retry."
        )

    def _sleep_before_retry(self,response,attempt):
        retry_after=self._get_retry_after(response)
        delay=(
            retry_after
            if retry_after is not None
            else self.backoff_base*(2**attempt)
        )
        delay=min(delay,60.0)
        print(
            f"  OpenRouter retry {attempt+1}/"
            f"{self.max_retries} dalam {delay:.1f}s..."
        )
        time.sleep(delay)

    @staticmethod
    def _get_retry_after(response):
        if response is None:
            return None
        value=response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            delay=float(value)
        except (TypeError,ValueError):
            return None
        return delay if delay>=0 else None

    @staticmethod
    def _build_api_error(response):
        status=response.status_code
        try:
            data=response.json()
            message=(
                data.get("error",{}).get("message")
                or data.get("message")
            )
        except (ValueError,AttributeError):
            message=None
        if message:
            return RuntimeError(
                f"OpenRouter API HTTP {status}: {message}"
            )
        return RuntimeError(
            f"OpenRouter API HTTP {status}."
        )

    @staticmethod
    def _extract_text(data):
        choices=data.get("choices",[])
        if not choices:
            raise RuntimeError(
                "OpenRouter tidak mengembalikan choice."
            )

        content=choices[0].get("message",{}).get("content")

        if isinstance(content,str) and content:
            return content

        if isinstance(content,list):
            texts=[]
            for block in content:
                if isinstance(block,dict) and block.get("text"):
                    texts.append(block["text"])
            if texts:
                return "".join(texts)

        raise RuntimeError(
            "Tidak menemukan output text dari OpenRouter."
        )


def create_model_client(
    provider,model,api_key,max_retries=3,
    timeout=120,backoff_base=2.0
):
    provider=provider.strip().lower()

    if provider=="gemini":
        return GeminiClient(
            model=model,api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
            backoff_base=backoff_base,
        )

    if provider=="openrouter":
        return OpenRouterClient(
            model=model,api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
            backoff_base=backoff_base,
        )

    raise ValueError(
        f"Provider AI tidak didukung: {provider!r}"
    )


def extract_json(text):
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
