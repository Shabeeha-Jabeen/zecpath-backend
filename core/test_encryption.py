
from unittest import TestCase
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

from core.encryption import encrypt_text, decrypt_text


class EncryptionHelperTests(TestCase):
    def test_encrypt_and_decrypt_text(self):
        original = "Sensitive candidate data"

        encrypted = encrypt_text(original)

        self.assertNotEqual(encrypted, original)
        self.assertEqual(decrypt_text(encrypted), original)

    def test_encrypt_empty_string(self):
        self.assertEqual(encrypt_text(""), "")

    def test_decrypt_empty_string(self):
        self.assertEqual(decrypt_text(""), "")

    def test_none_values_are_preserved(self):
        self.assertIsNone(encrypt_text(None))
        self.assertIsNone(decrypt_text(None))

    def test_each_encryption_uses_randomized_output(self):
        original = "Candidate data"

        encrypted_one = encrypt_text(original)
        encrypted_two = encrypt_text(original)

        self.assertNotEqual(encrypted_one, encrypted_two)
        self.assertEqual(decrypt_text(encrypted_one), original)
        self.assertEqual(decrypt_text(encrypted_two), original)

    def test_missing_encryption_key_raises_error(self):
        with patch.dict("os.environ", {}, clear=False):
            with patch("core.encryption.os.getenv", return_value=None):
                with self.assertRaises(ImproperlyConfigured):
                    encrypt_text("Sensitive data")

    def test_invalid_encryption_key_raises_error(self):
        with patch(
            "core.encryption.os.getenv",
            return_value="invalid-key",
        ):
            with self.assertRaises(ImproperlyConfigured):
                encrypt_text("Sensitive data")

    def test_invalid_encrypted_value_raises_error(self):
        with self.assertRaises(ValueError):
            decrypt_text("not-valid-encrypted-data")

    def test_non_string_values_are_rejected(self):
        with self.assertRaises(TypeError):
            encrypt_text(123)

        with self.assertRaises(TypeError):
            decrypt_text(123)
