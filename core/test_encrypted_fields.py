
from django.test import SimpleTestCase

from core.encrypted_fields import EncryptedTextField


class EncryptedTextFieldTests(SimpleTestCase):

    def setUp(self):
        self.field = EncryptedTextField()

    def test_new_value_is_encrypted(self):
        original = "Sensitive interview answer"

        stored = self.field.get_prep_value(original)

        self.assertNotEqual(stored, original)
        self.assertTrue(stored.startswith("enc:v1:"))

    
    def test_encrypted_value_can_be_decrypted(self):
        original = "Python Django interview answer"

        stored = self.field.get_prep_value(original)

        restored = self.field.from_db_value(
            stored, None, None
        )

        self.assertEqual(restored, original)


    def test_existing_plaintext_remains_readable(self):
        original = "Existing interview transcript"

        restored = self.field.from_db_value(original, None, None)

        self.assertEqual(restored, original)

    def test_empty_value_is_preserved(self):
        self.assertEqual(self.field.get_prep_value(""), "")
        self.assertEqual(
            self.field.from_db_value("", None, None), ""
        )

    def test_none_value_is_preserved(self):
        self.assertIsNone(self.field.get_prep_value(None))
        self.assertIsNone(
            self.field.from_db_value(None, None, None)
        )
