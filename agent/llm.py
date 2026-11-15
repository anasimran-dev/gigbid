"""Model access. Every node asks for a structured (Pydantic) answer and gets None when
no model is available, so each node falls back to its rule-based logic.

  result = structured("analyst", JobSpec, job=wrapped_text) or heuristic(...)

Models are OpenAI-compatible endpoints (Groq, OpenRouter, Together, Ollama, vLLM), chosen per
node in agent/config.yaml. Prompts are files in agent/prompts/<node>.md, never inline.
"""
import json
import os
import threading
import time
import urllib.request

from pydantic import BaseModel

from agent import tracing
from agent.config import ROOT, cfg

DEFAULT_URLS = {"OPEN_LLM_BASE_URL": "https://api.groq.com/openai/v1", "OLLAMA_OPENAI_URL": "http://localhost:11434/v1"}


def _profile() -> dict:
    return cfg()["profiles"][cfg()["profile"]]


def enabled() -> bool:
    p = _profile()
    if p["provider"] == "none":
        return False
    return bool(os.getenv(p["api_key_env"])) or p["api_key_env"] == "OLLAMA_API_KEY"


def load_prompt(name: str, **variables) -> str:
    text = (ROOT / "agent" / "prompts" / f"{name}.md").read_text(encoding="utf-8")
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def _chat(model: str, system: str, user: str, timeout: int = 60) -> tuple[str, int, int]:
    p = _profile()
    base = os.getenv(p["base_url_env"], DEFAULT_URLS.get(p["base_url_env"], ""))
    body = {"model": model, "temperature": 0.2, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{base}/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json",
                                  "Authorization": f"Bearer {os.getenv(p['api_key_env'], 'ollama')}"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        out = json.loads(res.read())
    usage = out.get("usage", {})
    return out["choices"][0]["message"]["content"], usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def structured(node: str, schema: type[BaseModel], prompt: str | None = None, **variables) -> BaseModel | None:
    """Call the node's model with its prompt file; validate the JSON against `schema`.
    Two tries on the node's model, then one on the fallback model, then None (rule-based path)."""
    if not enabled():
        return None
    p = _profile()
    model = p[cfg()["node_models"].get(node, "small")]
    system = ("Reply with one JSON object that matches this JSON schema. No prose.\n"
              + json.dumps(schema.model_json_schema()))
    user = load_prompt(prompt or node, **variables)
    for attempt, m in enumerate([model, model, p["fallback"]]):
        start = time.time()
        try:
            text, t_in, t_out = _chat(m, system, user)
            result = schema.model_validate_json(text)
            tracing.event("llm", m, node=node, tokens_in=t_in, tokens_out=t_out,
                          usd=tracing.cost_usd(m, t_in, t_out), seconds=round(time.time() - start, 3))
            _used().append((t_in + t_out, tracing.cost_usd(m, t_in, t_out)))
            return result
        except Exception as e:  # timeout, 429, 5xx, invalid JSON, schema mismatch
            tracing.event("llm_error", m, node=node, error=str(e)[:200], attempt=attempt)
            time.sleep(0.5 * (attempt + 1))
    return None


_local = threading.local()  # parallel nodes run in separate threads, so usage is tracked per thread


def _used() -> list:
    if not hasattr(_local, "usage"):
        _local.usage = []
    return _local.usage


def take_usage() -> tuple[int, float]:
    """Tokens and USD used by this thread since the last call (the node wrapper adds them to state)."""
    tokens, usd = sum(t for t, _ in _used()), sum(u for _, u in _used())
    _used().clear()
    return tokens, usd
