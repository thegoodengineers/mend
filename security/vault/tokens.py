import secrets


def reset_token(user: str) -> str:
    """A password-reset token: random and unguessable, different every time, at least 32 URL-safe characters."""
    return secrets.token_urlsafe(32)
