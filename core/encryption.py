
import os

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured


def get_fernet():
    """Return a Fernet instance using the key stored in .env."""
    key = os.getenv("DATA_ENCRYPTION_KEY")

    if not key:
        raise ImproperlyConfigured(
            "DATA_ENCRYPTION_KEY is missing from the environment."
        )

    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "DATA_ENCRYPTION_KEY is invalid."
        ) from exc


def encrypt_text(value):
    """Encrypt a string. Preserve None and empty strings."""
    if value is None or value == "":
        return value

    if not isinstance(value, str):
        raise TypeError("encrypt_text expects a string.")

    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value):
    """Decrypt text previously encrypted with this key."""
    if value is None or value == "":
        return value

    if not isinstance(value, str):
        raise TypeError("decrypt_text expects a string.")

    try:
        return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "Unable to decrypt value. Check the encryption key and stored data."
        ) from exc
