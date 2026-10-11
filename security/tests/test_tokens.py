"""Predictable reset tokens: tokens must be random, not derived from the user."""

import re

from vault.tokens import reset_token


def test_token_shape():
    token = reset_token("bob")
    assert len(token) >= 32 and re.fullmatch(r"[A-Za-z0-9_-]+", token)


def test_exploit_tokens_are_not_predictable():
    tokens = {reset_token("bob") for _ in range(20)}
    assert len(tokens) == 20  # never the same twice, so an attacker cannot recompute one
    assert reset_token("alice") != reset_token("alice")
