"""Tests Fase 5 — cifrado y enrutamiento."""

from app.services.crypto_keys import decrypt_secret, encrypt_secret, key_hint
from app.services.model_router import estimate_cost, routing_mode


def test_encrypt_roundtrip():
    plain = "sk-test-abcdef1234567890"
    token = encrypt_secret(plain)
    assert token != plain
    assert "sk-test" not in token
    assert decrypt_secret(token) == plain


def test_key_hint_masks():
    assert key_hint("sk-abcdefghij") == "••••ghij"
    assert key_hint("ab") == "••••"


def test_routing_simple_local():
    assert routing_mode("classify") == "local_first"
    assert routing_mode("verify") == "local_first"


def test_routing_complex_paid():
    assert routing_mode("generate_content") == "local_first"
    assert routing_mode("translate") == "local_first"
    assert routing_mode("complex_analysis") == "paid_only"


def test_local_cost_zero():
    assert estimate_cost("ollama", 1000, 1000) == 0.0
    assert estimate_cost("openai", 1000, 0) > 0
