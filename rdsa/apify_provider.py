"""Read-only Apify adapter for public Threads search results."""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import config


class ApifyError(RuntimeError):
    """An Apify request or actor execution failed."""


class ApifyQuotaError(ApifyError):
    """Apify rejected a request because of quota or a platform limit."""


class ApifyBudgetExceeded(ApifyError):
    """The local monthly spending guard has stopped live execution."""


def _truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def apify_live_enabled():
    return _truthy(os.getenv("APIFY_LIVE_ENABLED", config.APIFY_LIVE_ENABLED))


class MonthlyUsageGuard:
    """Persist a conservative monthly Apify cost estimate."""

    def __init__(self, state_path=None, warn_at_usd=None, stop_at_usd=None, price_per_cu=None):
        self.state_path = Path(state_path or config.APIFY_USAGE_PATH)
        self.warn_at_usd = float(warn_at_usd if warn_at_usd is not None else config.APIFY_WARN_USD)
        self.stop_at_usd = float(stop_at_usd if stop_at_usd is not None else config.APIFY_STOP_USD)
        self.price_per_cu = float(price_per_cu if price_per_cu is not None else os.getenv("APIFY_PRICE_PER_CU", "0.5"))
        self._state = self._load()

    @property
    def total_usd(self):
        return float(self._state.get("estimated_usd", 0.0))

    def _load(self):
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            state = {}
        if state.get("month") != month:
            state = {"month": month, "estimated_usd": 0.0, "runs": 0}
            self._save(state)
        return state

    def _save(self, state=None):
        state = state or self._state
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def check_budget(self):
        if self.total_usd >= self.stop_at_usd:
            return "stop"
        if self.total_usd >= self.warn_at_usd:
            return "warn"
        return "ok"

    def record_run(self, run_obj):
        units = run_obj.get("computeUnits") if isinstance(run_obj, dict) else None
        estimated = float(units) * self.price_per_cu if units is not None else 0.10
        # Prefer the ACTUAL cost the platform reports, if present.
        actual = run_obj.get("usageTotalUsd")
        actual = float(actual) if isinstance(actual, (int, float)) else None
        cost = actual if actual is not None else estimated
        self._state["estimated_usd"] = round(self.total_usd + cost, 4)
        self._state["actual_usd"] = round(float(self._state.get("actual_usd", 0.0)) + (actual or 0.0), 4)
        self._state["runs"] = int(self._state.get("runs", 0)) + 1
        self._save()
        return cost


monthly_usage_guard = MonthlyUsageGuard


class ApifyThreadsProvider:
    BASE_URL = "https://api.apify.com/v2"

    def __init__(self, token=None, actor_id=None, session=None):
        self.token = token if token is not None else os.getenv("APIFY_API_TOKEN", "")
        self.actor_id = actor_id or os.getenv("APIFY_ACTOR_ID", "automation-lab/threads-scraper")
        self.session = session or requests
        self.usage = MonthlyUsageGuard()

    @staticmethod
    def normalize(raw_item):
        if not isinstance(raw_item, dict):
            return None
        post_id = raw_item.get("id", raw_item.get("postId"))
        text = raw_item.get("text")
        if not post_id or not isinstance(text, str) or not text.strip():
            return None
        return {
            "id": str(post_id),
            "text": text,
            "timestamp": raw_item.get("timestamp", raw_item.get("createdAt", raw_item.get("time", ""))) or "",
            "username": raw_item.get("username", raw_item.get("userName", "")) or "",
            "permalink": raw_item.get("permalink") or raw_item.get("url") or raw_item.get("postUrl") or "",
        }

    def _request(self, method, url, timeout, **kwargs):
        last_status = None
        for attempt in range(3):
            try:
                response = getattr(self.session, method)(url, timeout=timeout, **kwargs)
            except requests.Timeout as exc:
                raise ApifyError("Apify request timed out") from exc
            except requests.RequestException as exc:
                raise ApifyError(f"Apify request failed: {exc}") from exc
            status = getattr(response, "status_code", 200)
            if status < 400:
                return response
            last_status = status
            quota_text = ""
            try:
                quota_text = json.dumps(response.json()).lower()
            except (ValueError, TypeError, AttributeError):
                quota_text = str(getattr(response, "text", "")).lower()
            if status == 429 or any(word in quota_text for word in ("quota", "rate limit", "limit exceeded")):
                if attempt < 2:
                    time.sleep(0.05 * (2 ** attempt))
                    continue
                raise ApifyQuotaError("Apify quota or rate limit exceeded")
            if status < 500:
                break
            if attempt < 2:
                time.sleep(0.05 * (2 ** attempt))
        if last_status == 429:
            raise ApifyQuotaError("Apify quota or rate limit exceeded")
        raise ApifyError(f"Apify HTTP error {last_status}")

    @staticmethod
    def _json(response):
        try:
            return response.json()
        except (ValueError, TypeError, AttributeError) as exc:
            raise ApifyError("Apify returned malformed JSON") from exc

    def search(self, queries, max_posts_per_query=5, timeout=60, max_total=20, max_total_charge_usd=0.10):
        if not apify_live_enabled():
            raise ApifyError("Apify live disabled; set APIFY_LIVE_ENABLED=true to enable it")
        if not self.token:
            raise ApifyError("APIFY_API_TOKEN is required when Apify live is enabled")
        if self.usage.check_budget() == "stop":
            raise ApifyBudgetExceeded("Apify monthly usage budget exceeded")
        results = []
        for query in queries:
            if len(results) >= max_total:
                break
            start_url = f"{self.BASE_URL}/acts/{self.actor_id}/runs?token={self.token}"
            response = self._request("post", start_url, timeout, json={"mode": "search", "searchQueries": [query], "maxPosts": max_posts_per_query, "maxTotalChargeUsd": max_total_charge_usd})
            payload = self._json(response)
            run = payload.get("data", payload) if isinstance(payload, dict) else {}
            run_id = run.get("id", run.get("runId")) if isinstance(run, dict) else None
            if not run_id:
                raise ApifyError("Apify run response did not contain a run id")
            deadline = time.monotonic() + timeout
            status_obj = run
            for _ in range(30):
                if time.monotonic() >= deadline:
                    raise ApifyError("Apify actor status polling timed out")
                status_response = self._request("get", f"{self.BASE_URL}/actor-runs/{run_id}?token={self.token}", timeout,)
                status_payload = self._json(status_response)
                status_obj = status_payload.get("data", status_payload) if isinstance(status_payload, dict) else {}
                status = status_obj.get("status") if isinstance(status_obj, dict) else None
                if status == "SUCCEEDED":
                    break
                if status in {"FAILED", "TIMED-OUT", "ABORTED"}:
                    raise ApifyError(f"Apify actor run {status.lower()}")
                time.sleep(0.05)
            else:
                raise ApifyError("Apify actor status polling exceeded poll limit")
            items_response = self._request("get", f"{self.BASE_URL}/actor-runs/{run_id}/dataset/items?token={self.token}", timeout,)
            try:
                items = self._json(items_response)
            except ApifyError:
                return results
            if not isinstance(items, list):
                items = items.get("items", []) if isinstance(items, dict) else []
            self.usage.record_run({**run, **status_obj})
            for item in items[:max_posts_per_query]:
                normalized = self.normalize(item)
                if normalized:
                    results.append(normalized)
                    if len(results) >= max_total:
                        break
        return results[:max_total]
