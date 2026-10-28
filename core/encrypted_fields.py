
from django.db import models

from .encryption import decrypt_text, encrypt_text


class EncryptedTextField(models.TextField):
    """Encrypt text at rest and decrypt it when loaded from the database."""

    prefix = "enc:v1:"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)

        if value is None or value == "":
            return value

        if not isinstance(value, str):
            raise TypeError("EncryptedTextField accepts text values only.")

        # Avoid encrypting a value that is already stored in encrypted format.
        if value.startswith(self.prefix):
            return value

        return self.prefix + encrypt_text(value)

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value

        if value.startswith(self.prefix):
            encrypted_value = value[len(self.prefix):]
            return decrypt_text(encrypted_value)

        # Allow existing plaintext records to remain readable.
        return value
