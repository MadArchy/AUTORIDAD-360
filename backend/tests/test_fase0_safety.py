from app.services.html_sanitize import sanitize_editorial_html
from app.services.url_safety import validate_provider_base_url


def test_sanitize_strips_script_and_keeps_safe_markup():
    raw = (
        '<article><p>Hola</p><script>alert(1)</script>'
        '<a href="javascript:alert(1)">x</a>'
        '<a href="https://example.com" target="_blank">ok</a></article>'
    )
    cleaned = sanitize_editorial_html(raw)
    assert "<script" not in cleaned.lower()
    assert "javascript:" not in cleaned.lower()
    assert "https://example.com" in cleaned
    assert "noopener" in cleaned
    assert "<p>Hola</p>" in cleaned


def test_ssrf_blocks_private_paid_url():
    try:
        validate_provider_base_url("http://127.0.0.1:8080", is_local=False)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_ssrf_allows_openai_https():
    url = validate_provider_base_url("https://api.openai.com/v1", is_local=False)
    assert url.startswith("https://api.openai.com")


def test_ssrf_allows_local_ollama():
    url = validate_provider_base_url("http://127.0.0.1:11434", is_local=True)
    assert "127.0.0.1" in url
