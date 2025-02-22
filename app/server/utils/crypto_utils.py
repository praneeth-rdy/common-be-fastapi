import hashlib
from typing import Optional


def sha256(text: Optional[str]):
    text = hashlib.sha256(text.encode())
    return text.hexdigest()


def sha1(text: Optional[str]):
    text = hashlib.sha1(text.encode())
    return text.hexdigest()


def sha512(text: Optional[str]):
    text = hashlib.sha512(text.encode())
    return text.hexdigest()
