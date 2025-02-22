import secrets
import string

from fastapi import HTTPException, status

from app.server.static import localization
from app.server.utils import crypto_utils


def generate_random_password(length):
    # Combine all alphanumeric characters (letters and digits)
    characters = string.ascii_letters + string.digits

    return ''.join(secrets.choice(characters) for _ in range(length))


def check_password(password: str, password_hash: str) -> bool:
    """
    Checks if a given password is valid by comparing it with a password hash.

    Args:
        password: The password to be checked.
        password_hash: The hash of the correct password.
    Returns:
        bool: True if the password is valid, False otherwise.
    """
    password_received = crypto_utils.sha256(password)
    if password_received != password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_PASSWORD_INVALID)

    return True
