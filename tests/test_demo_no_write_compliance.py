from pathlib import Path


def test_demo_has_no_threads_content_write_calls():
    text = Path("app_review_demo.py").read_text(encoding="utf-8").lower()
    assert "graph.threads.net" not in text or all(call not in text for call in (".post(", ".put(", ".delete("))

