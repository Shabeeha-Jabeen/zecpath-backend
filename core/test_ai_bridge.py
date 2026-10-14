
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from core.ai_bridge import AIBridgeService, AIBridgeError


class AIBridgeServiceTests(SimpleTestCase):

    def test_missing_api_url(self):
        service = AIBridgeService(api_url="", api_key="test-key")

        with self.assertRaises(AIBridgeError):
            service.post_json({"message": "Hello"})

    def test_missing_api_key(self):
        service = AIBridgeService(
            api_url="https://example.com/api",
            api_key="",
        )

        with self.assertRaises(AIBridgeError):
            service.post_json({"message": "Hello"})

    @patch("core.ai_bridge.requests.post")
    def test_successful_api_response(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"reply": "Hello!"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        service = AIBridgeService(
            api_url="https://example.com/api",
            api_key="test-key",
        )

        result = service.post_json({"message": "Hello"})

        self.assertEqual(result, {"reply": "Hello!"})
        mock_post.assert_called_once()

    def test_language_and_voice_are_added_to_payload(self):
        service = AIBridgeService(
            api_url="https://primary.example.com/api",
            api_key="test-key",
            language="ml",
            voice="voice-1",
        )

        with patch.object(
            service,
            "_send_with_retries",
            return_value={"reply": "Namaskaram"},
        ) as mock_send:
            result = service.post_json({"message": "Hello"})

        sent_payload = mock_send.call_args.args[2]

        self.assertEqual(sent_payload["language"], "ml")
        self.assertEqual(sent_payload["voice"], "voice-1")
        self.assertEqual(result["reply"], "Namaskaram")

    def test_fallback_provider_is_used_after_primary_failure(self):
        service = AIBridgeService(
            api_url="https://primary.example.com/api",
            api_key="primary-key",
            fallback_url="https://fallback.example.com/api",
            fallback_key="fallback-key",
        )

        with patch.object(
            service,
            "_send_with_retries",
            side_effect=[
                AIBridgeError("Primary provider failed"),
                {"reply": "Fallback response"},
            ],
        ) as mock_send:
            result = service.post_json({"message": "Hello"})

        self.assertEqual(result["reply"], "Fallback response")
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(
            mock_send.call_args_list[1].args[0],
            "https://fallback.example.com/api",
        )
