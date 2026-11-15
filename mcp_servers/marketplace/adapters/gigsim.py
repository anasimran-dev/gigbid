"""GigSim adapter. Talks HTTP when GIGSIM_BASE_URL is set, otherwise uses the in-process simulator
(tests, evals, local dev without Docker). Retries 429 and 5xx with exponential backoff."""
import json
import os
import time
import urllib.error
import urllib.request

from agent.config import cfg
from agent.marketplace_port import MarketplaceUnavailable


class GigSimAdapter:
    def __init__(self):
        self.base = os.getenv("GIGSIM_BASE_URL", "")
        self.token = os.getenv("GIGSIM_API_TOKEN", "dev-token")
        m = cfg()["marketplace"]
        self.retries, self.backoff, self.timeout = m["retries"], m["backoff_seconds"], m["timeout_seconds"]

    def _once(self, method: str, user: str, kwargs: dict):
        if not self.base:
            from gigsim.core import default_sim
            return getattr(default_sim(), method)(user, **kwargs)
        req = urllib.request.Request(f"{self.base}/v1/{method}", json.dumps(kwargs).encode(),
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}", "X-User": user})
        with urllib.request.urlopen(req, timeout=self.timeout) as res:
            return json.loads(res.read())["result"]

    def _do(self, method: str, user: str, **kwargs):
        last = None
        for attempt in range(self.retries + 1):
            try:
                return self._once(method, user, kwargs)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise KeyError(e.read().decode()) from e
                last = e  # 429 / 5xx: retry
            except KeyError:
                raise
            except Exception as e:  # RateLimited, ServerError, connection refused, timeout
                last = e
            time.sleep(self.backoff * (2 ** attempt))
        raise MarketplaceUnavailable(f"GigSim {method} failed after {self.retries + 1} attempts: {last}")

    def search_jobs(self, user, query, limit=20):
        return self._do("search_jobs", user, query=query, limit=limit)

    def get_job(self, user, job_id):
        return self._do("get_job", user, job_id=job_id)

    def get_client_history(self, user, client_id):
        return self._do("get_client_history", user, client_id=client_id)

    def get_connects_balance(self, user):
        return self._do("get_connects_balance", user)

    def get_market_stats(self, user, category, skills):
        return self._do("get_market_stats", user, category=category, skills=skills)

    def list_messages(self, user, thread_id=None):
        return self._do("list_messages", user, thread_id=thread_id)

    def list_events(self, user):
        return self._do("list_events", user)

    def create_proposal_draft(self, user, job_id, cover_letter, bid_usd, screening_answers, idempotency_key):
        return self._do("create_proposal_draft", user, job_id=job_id, cover_letter=cover_letter, bid_usd=bid_usd,
                        screening_answers=screening_answers, idempotency_key=idempotency_key)

    def submit_proposal(self, user, draft_id, idempotency_key):
        return self._do("submit_proposal", user, draft_id=draft_id, idempotency_key=idempotency_key)

    def send_message(self, user, thread_id, text, idempotency_key):
        return self._do("send_message", user, thread_id=thread_id, text=text, idempotency_key=idempotency_key)
