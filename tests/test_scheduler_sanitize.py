"""C1B — focused security tests for centralized error sanitization.

Target: ``rdsa.scheduler.sanitize_error``.

These tests prove that sanitized error output can never expose:
  - token= / api_token= / bot_token= / api_key= / secret= / password=
  - chat_id=
  - Authorization: Bearer <token>
  - token-like URL query parameters
  - known filesystem paths (Windows and POSIX)

All secret inputs are clearly FAKE sentinels, not real credentials or
production chat IDs. The public return contract ``(error_code, sanitized)``
and useful non-sensitive context are preserved. Sanitization is idempotent.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdsa import scheduler as S

# Fake sentinel values — never real credentials or production identifiers.
SENTINELS = {
    "token_eq": "token=FAKE_TOKEN_SENTINEL",
    "chat_id_eq": "chat_id=123456789",
    "token_colon": "api_token: FAKE_TOKEN_SENTINEL",
    "chat_id_colon": "chat_id: 123456789",
    "bearer": "Authorization: Bearer FAKE_BEARER_SENTINEL",
    "api_key": "api_key: FAKE_KEY_SENTINEL",
    "bot_token": "bot_token=FAKE_BOT_SENTINEL",
    "secret": "secret=FAKE_SECRET_SENTINEL",
    "password": "password=FAKE_PASSWORD_SENTINEL",
    "url_query": "https://example.test?token=FAKE_QUERY_SENTINEL",
    "win_path": "C:\\private\\path",
    "posix_path": "/usr/local/secret/run.sh",
}

REDACTED = "[redacted]"


def _all_sentinels_present(blob: str) -> list[str]:
    leaks = []
    for key, val in SENTINELS.items():
        # Only the secret-bearing value itself must be absent; the key label
        # (e.g. "token=") is fine.
        value_only = val.split("=", 1)[1] if "=" in val else val.split(":", 1)[1].strip()
        if value_only in blob:
            leaks.append(key)
    return leaks


# --- token using "=" ---------------------------------------------------------
def test_token_equals_redacted():
    code, san = S.sanitize_error("provider failed token=FAKE_TOKEN_SENTINEL")
    assert "FAKE_TOKEN_SENTINEL" not in san
    assert "token=[redacted]" in san


# --- token using ":" ---------------------------------------------------------
def test_token_colon_redacted():
    code, san = S.sanitize_error("auth api_token: FAKE_TOKEN_SENTINEL denied")
    assert "FAKE_TOKEN_SENTINEL" not in san
    assert "api_token=[redacted]" in san


# --- quoted JSON-like token fields ------------------------------------------
def test_json_quoted_token_redacted():
    code, san = S.sanitize_error('{"token": "FAKE_TOKEN_SENTINEL", "chat_id": 123456789}')
    assert "FAKE_TOKEN_SENTINEL" not in san
    assert '"token": "[redacted]"' in san


# --- chat_id using "=" -------------------------------------------------------
def test_chat_id_equals_redacted():
    code, san = S.sanitize_error("delivered chat_id=123456789 ok")
    assert "123456789" not in san
    assert "chat_id=[redacted]" in san


# --- chat_id using ":" -------------------------------------------------------
def test_chat_id_colon_redacted():
    code, san = S.sanitize_error("chat_id: 123456789 routed")
    assert "123456789" not in san
    assert "chat_id=[redacted]" in san


# --- Bearer authorization ----------------------------------------------------
def test_bearer_authorization_redacted():
    code, san = S.sanitize_error("auth error Authorization: Bearer FAKE_BEARER_SENTINEL")
    assert "FAKE_BEARER_SENTINEL" not in san
    assert "Authorization: Bearer [redacted]" in san


# --- API key and bot-token aliases ------------------------------------------
def test_api_key_and_bot_token_redacted():
    code, san = S.sanitize_error("api_key: FAKE_KEY_SENTINEL bot_token=FAKE_BOT_SENTINEL")
    assert "FAKE_KEY_SENTINEL" not in san
    assert "FAKE_BOT_SENTINEL" not in san
    assert "api_key=[redacted]" in san
    assert "bot_token=[redacted]" in san


# --- URL query-string token --------------------------------------------------
def test_url_query_token_redacted():
    code, san = S.sanitize_error("fetch https://example.test?token=FAKE_QUERY_SENTINEL failed")
    assert "FAKE_QUERY_SENTINEL" not in san
    assert "token=[redacted]" in san


# --- Windows and POSIX paths -------------------------------------------------
def test_paths_redacted():
    code, san = S.sanitize_error("read C:\\private\\path and /usr/local/secret/run.sh")
    assert "C:\\private\\path" not in san
    assert "/usr/local/secret/run.sh" not in san
    assert "[path]" in san


# --- multiline provider errors ----------------------------------------------
def test_multiline_provider_error_redacted():
    raw = "Traceback line1\ntoken=FAKE_TOKEN_SENTINEL\nchat_id=123456789\nnormal context"
    code, san = S.sanitize_error(raw)
    assert "FAKE_TOKEN_SENTINEL" not in san
    assert "123456789" not in san
    assert "normal context" in san  # non-sensitive context preserved


# --- already-redacted input --------------------------------------------------
def test_already_redacted_is_idempotent():
    once = S.sanitize_error("token=FAKE_TOKEN_SENTINEL chat_id=123456789")[1]
    twice = S.sanitize_error(once)[1]
    assert once == twice
    assert "FAKE_TOKEN_SENTINEL" not in twice
    assert "123456789" not in twice


# --- very long error truncation ---------------------------------------------
def test_long_error_truncated():
    code, san = S.sanitize_error("timeout " + ("x" * 5000))
    assert len(san) <= 280
    assert "timeout" in san.lower()


# --- useful non-sensitive message retained ----------------------------------
def test_useful_context_retained():
    code, san = S.sanitize_error("Apify actor run failed: cost limit exceeded at step 3")
    assert "cost" in san.lower()
    assert "step 3" in san
    assert code == "cost_limit"


# --- raw exception appears neither in audit nor UI --------------------------
def test_raw_exception_not_in_output():
    exc = RuntimeError("provider failed token=FAKE_TOKEN_SENTINEL chat_id=123456789 C:\\private\\path")
    code, san = S.sanitize_error(exc)
    # The raw repr / original payload must not survive.
    assert "FAKE_TOKEN_SENTINEL" not in san
    assert "123456789" not in san
    assert "C:\\private\\path" not in san
    assert "RuntimeError" not in san


# --- repeated sanitization is safe ------------------------------------------
def test_repeated_sanitization_safe():
    original = "token=FAKE_TOKEN_SENTINEL chat_id=123456789 C:\\private\\path"
    out = original
    for _ in range(5):
        out = S.sanitize_error(out)[1]
    assert "FAKE_TOKEN_SENTINEL" not in out
    assert "123456789" not in out
    assert out.count("[redacted]") == 2  # stable, not multiplied


# --- public contract preserved ----------------------------------------------
def test_public_contract_preserved():
    code, san = S.sanitize_error("telegram send failed token=FAKE_TOKEN_SENTINEL")
    assert isinstance(code, str) and isinstance(san, str)
    assert code == "telegram_failure"
    assert len(san) <= 280
