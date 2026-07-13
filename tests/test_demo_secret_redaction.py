from app_review_demo import redact_token


def test_redaction_never_emits_raw_token():
    token = "very-secret-threads-token"
    rendered = f"Authentication status: connected; token={redact_token(token)}"
    assert token not in rendered
    assert "[redacted]" in rendered

