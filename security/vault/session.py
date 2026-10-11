import json


def load_session(blob: bytes) -> dict:
    """Decode a session cookie. Only JSON objects are accepted; anything else raises ValueError.
    (Never unpickle data from a client: pickle can run code.)"""
    try:
        data = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("session is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("session must be a JSON object")
    return data
