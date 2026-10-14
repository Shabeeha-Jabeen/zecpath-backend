
import os
import time

import requests


class AIBridgeError(Exception):
    """Raised when an AI service request fails."""


class AIBridgeService:
    """Central bridge for communicating with an external AI API."""

    def __init__(
        self,
        api_url=None,
        api_key=None,
        timeout=20,
        max_retries=3,
        language="en",
        voice="default",
        fallback_url=None,
        fallback_key=None,
    ):
        self.api_url = api_url or os.getenv("AI_API_URL", "")
        self.api_key = api_key or os.getenv("AI_API_KEY", "")
        self.fallback_url = fallback_url or os.getenv(
            "AI_FALLBACK_API_URL", ""
        )
        self.fallback_key = fallback_key or os.getenv(
            "AI_FALLBACK_API_KEY", ""
        )
        self.timeout = timeout
        self.max_retries = max_retries
        self.language = language
        self.voice = voice

    def post_json(self, payload):
        """Send a request with retry and optional provider fallback."""

        payload = {
            **payload,
            "language": self.language,
            "voice": self.voice,
        }

        providers = [
            (self.api_url, self.api_key),
            (self.fallback_url, self.fallback_key),
        ]

        last_error = None

        for api_url, api_key in providers:
            if not api_url or not api_key:
                continue

            try:
                return self._send_with_retries(
                    api_url, api_key, payload
                )
            except AIBridgeError as exc:
                last_error = exc

        if last_error:
            raise AIBridgeError(
                "All configured AI providers failed."
            ) from last_error

        raise AIBridgeError(
            "No valid AI provider is configured."
        )

    def _send_with_retries(self, api_url, api_key, payload):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(min(2 ** attempt, 8))
                        continue

                response.raise_for_status()
                return response.json()

            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt >= self.max_retries:
                    raise AIBridgeError(
                        "AI service is unavailable after retries."
                    ) from exc

                time.sleep(min(2 ** attempt, 8))

            except requests.HTTPError as exc:
                status_code = exc.response.status_code
                if status_code == 429:
                    raise AIBridgeError(
                        "AI service rate limit exceeded."
                    ) from exc

                raise AIBridgeError(
                    f"AI service returned HTTP {status_code}."
                ) from exc

            except requests.RequestException as exc:
                raise AIBridgeError(
                    "Unable to communicate with the AI service."
                ) from exc

            except ValueError as exc:
                raise AIBridgeError(
                    "AI service returned invalid JSON."
                ) from exc

        raise AIBridgeError("AI service request failed.")
