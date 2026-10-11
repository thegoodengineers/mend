"""SQL injection and insecure deserialization: the feature works, and the exploit does not."""

import pickle

import pytest

from vault.db import connect, find_user
from vault.session import load_session

USERS = [("alice", "admin"), ("bob", "user"), ("o'brien", "user")]


def test_find_user_by_exact_name():
    conn = connect(USERS)
    assert find_user(conn, "bob") == [("bob", "user")]
    assert find_user(conn, "o'brien") == [("o'brien", "user")]
    assert find_user(conn, "nobody") == []


def test_exploit_sql_injection_returns_nothing():
    conn = connect(USERS)
    assert find_user(conn, "x' OR '1'='1") == []
    assert find_user(conn, "x' UNION SELECT name, role FROM users --") == []


def test_session_round_trip():
    assert load_session(b'{"user": "bob", "cart": [1, 2]}') == {"user": "bob", "cart": [1, 2]}


def test_exploit_pickled_session_is_rejected():
    with pytest.raises(ValueError):
        load_session(pickle.dumps({"user": "alice", "role": "admin"}))
    with pytest.raises(ValueError):
        load_session(b"[1, 2, 3]")
