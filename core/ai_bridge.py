
import logging
import os
import time

import requests


logger = logging.getLogger("core.ai")


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
            ("primary", self.api_url, self.api_key),
            ("fallback", self.fallback_url, self.fallback_key),
        ]

        last_error = None

        for provider_name, api_url, api_key in providers:
            if not api_url or not api_key:
                logger.warning(
                    "AI provider skipped: provider=%s configured=False",
                    provider_name,
                )
                continue

            logger.info(
                "AI request started: provider=%s",
                provider_name,
            )

            try:
                result = self._send_with_retries(
                    api_url, api_key, payload,
                    provider_name=provider_name,
                )

                logger.info(
                    "AI request succeeded: provider=%s",
                    provider_name,
                )
                return result

            except AIBridgeError as exc:
                last_error = exc
                logger.error(
                    "AI provider failed: provider=%s error=%s",
                    provider_name,
                    str(exc),
                )

        if last_error:
            logger.error(
                "All configured AI providers failed"
            )
            raise AIBridgeError(
                "All configured AI providers failed."
            ) from last_error

        logger.error("No valid AI provider is configured")
        raise AIBridgeError(
            "No valid AI provider is configured."
        )

    def _send_with_retries(
        self, api_url, api_key, payload, provider_name="unknown"
    ):
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

                if (
                    response.status_code == 429
                    or response.status_code >= 500
                ):
                    if attempt < self.max_retries:
                        logger.warning(
                            "AI request retry: provider=%s "
                            "attempt=%s status=%s",
                            provider_name,
                            attempt + 1,
                            response.status_code,
                        )
                        time.sleep(min(2 ** attempt, 8))
                        continue

                response.raise_for_status()
                return response.json()

            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt >= self.max_retries:
                    logger.exception(
                        "AI connection failed after retries: "
                        "provider=%s attempts=%s",
                        provider_name,
                        attempt + 1,
                    )
                    raise AIBridgeError(
                        "AI service is unavailable after retries."
                    ) from exc

                logger.warning(
                    "AI connection retry: provider=%s "
                    "attempt=%s error_type=%s",
                    provider_name,
                    attempt + 1,
                    type(exc).__name__,
                )
                time.sleep(min(2 ** attempt, 8))

            except requests.HTTPError as exc:
                status_code = exc.response.status_code

                logger.error(
                    "AI HTTP failure: provider=%s status=%s",
                    provider_name,
                    status_code,
                )

                if status_code == 429:
                    raise AIBridgeError(
                        "AI service rate limit exceeded."
                    ) from exc

                raise AIBridgeError(
                    f"AI service returned HTTP {status_code}."
                ) from exc

            except requests.RequestException as exc:
                logger.exception(
                    "AI communication error: provider=%s",
                    provider_name,
                )
                raise AIBridgeError(
                    "Unable to communicate with the AI service."
                ) from exc

            except ValueError as exc:
                logger.exception(
                    "AI returned invalid JSON: provider=%s",
                    provider_name,
                )
                raise AIBridgeError(
                    "AI service returned invalid JSON."
                ) from exc

        raise AIBridgeError("AI service request failed.")
