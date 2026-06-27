import base64
import hashlib
import hmac
import os
from secrets import token_hex


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")


def hash_password(password: str) -> str:
    salt = token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt, digest = stored_hash.split("$", 1)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return hmac.compare_digest(candidate, digest)


def sign_user_id(user_id: int) -> str:
    payload = str(user_id).encode()
    encoded = base64.urlsafe_b64encode(payload).decode()
    signature = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def read_signed_user_id(cookie_value: str | None) -> int | None:
    if not cookie_value or "." not in cookie_value:
        return None
    encoded, signature = cookie_value.split(".", 1)
    expected = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        return int(base64.urlsafe_b64decode(encoded.encode()).decode())
    except ValueError:
        return None

