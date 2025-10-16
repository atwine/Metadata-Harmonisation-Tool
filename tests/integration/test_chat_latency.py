import os
import sys
import time
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from .utils import ensure_results_dir, write_markdown_report, write_json_report, format_table, timestamp_id, ms  # noqa: E402


def _list_models(base_url: str) -> list[str]:
    """List local models via Ollama client.list().
    Returns a de-duplicated sorted list of model names.
    """
    import ollama
    client = ollama.Client(host=base_url)
    resp = client.list()
    items: list[str] = []
    if hasattr(resp, "models"):
        for m in getattr(resp, "models", []):
            name = getattr(m, "model", None) or getattr(m, "name", None)
            if name:
                items.append(str(name))
    elif isinstance(resp, dict):
        for m in resp.get("models", []):
            if isinstance(m, dict):
                n = m.get("model") or m.get("name")
                if n:
                    items.append(str(n))
    return sorted(set(items))


def _is_chat_capable(base_url: str, model: str) -> bool:
    """Return True if Ollama reports 'completion' capability for the model.
    Uses /api/show via client.show(). Falls back to excluding names containing 'embed'.
    - API refs: List Local Models (GET /api/tags), Show Model Information (POST /api/show)
      [src] https://raw.githubusercontent.com/ollama/ollama/main/docs/api.md
    """
    try:
        import ollama
        client = ollama.Client(host=base_url)
        info = client.show(model=model)
        caps = []
        if isinstance(info, dict):
            caps = info.get("capabilities") or []
        else:
            try:
                caps = getattr(info, "capabilities", []) or []
            except Exception:
                caps = []
        if isinstance(caps, list) and any(str(c).lower() == "completion" for c in caps):
            return True
    except Exception:
        # If show() fails or capabilities not present, fall back to name heuristic
        pass
    return ("embed" not in model.lower())


@pytest.mark.local_ollama
def test_chat_latency_model_sweep():
    # Environment
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Discover available chat models or honor explicit whitelist
    env_models = os.getenv("CHAT_MODELS", "").strip()
    if env_models:
        chat_models = [m.strip() for m in env_models.split(",") if m.strip()]
    else:
        names = _list_models(base_url)
        chat_models = [n for n in names if _is_chat_capable(base_url, n)]
        if not chat_models:
            chat_models = [n for n in names if "embed" not in n.lower()]
    if not chat_models:
        pytest.skip("No chat-capable models found.")

    import ollama
    client = ollama.Client(host=base_url)

    rows = []
    for model in chat_models:
        s0 = time.perf_counter()
        try:
            # Primary: chat API
            resp = client.chat(
                model=model,
                messages=[{"role": "user", "content": "Reply exactly with: pong"}],
                options={"temperature": 0, "num_predict": 8},
                stream=False,
            )
            # Robust content/tokens extraction (dict or object response)
            content = ""
            prompt_tokens = None
            completion_tokens = None
            if isinstance(resp, dict):
                content = (resp.get("message", {}) or {}).get("content", "") or resp.get("response", "") or ""
                prompt_tokens = resp.get("prompt_eval_count")
                completion_tokens = resp.get("eval_count")
            else:
                try:
                    msg = getattr(resp, "message", None)
                    if msg is not None:
                        content = getattr(msg, "content", "") or ""
                    if not content:
                        content = getattr(resp, "response", "") or ""
                    prompt_tokens = getattr(resp, "prompt_eval_count", None)
                    completion_tokens = getattr(resp, "eval_count", None)
                except Exception:
                    content = ""
                    prompt_tokens = None
                    completion_tokens = None
            ok = isinstance(content, str) and ("pong" in content.lower())
            err = ""

            # Fallback: generate API if needed
            if (not ok) or (not content):
                try:
                    gen = client.generate(
                        model=model,
                        prompt="Reply exactly with: pong",
                        options={"temperature": 0, "num_predict": 8},
                        stream=False,
                    )
                    gcontent = ""
                    if isinstance(gen, dict):
                        gcontent = gen.get("response", "") or (gen.get("message", {}) or {}).get("content", "")
                        if prompt_tokens is None:
                            prompt_tokens = gen.get("prompt_eval_count")
                        if completion_tokens is None:
                            completion_tokens = gen.get("eval_count")
                    else:
                        try:
                            gcontent = getattr(gen, "response", "") or (
                                getattr(gen, "message", None) and getattr(getattr(gen, "message", None), "content", "")
                            ) or ""
                            if prompt_tokens is None:
                                prompt_tokens = getattr(gen, "prompt_eval_count", None)
                            if completion_tokens is None:
                                completion_tokens = getattr(gen, "eval_count", None)
                        except Exception:
                            gcontent = ""
                    if not content:
                        content = gcontent
                    ok = isinstance(content, str) and ("pong" in content.lower())
                except Exception as ge:
                    if not err:
                        err = str(ge)
        except Exception as e:
            content = ""
            ok = False
            prompt_tokens = None
            completion_tokens = None
            err = str(e)
        s1 = time.perf_counter()
        rows.append({
            "model": model,
            "elapsed_ms": ms(s1 - s0),
            "success": ok,
            "content_len": len(content),
            "error": (err or "")[:200],
            "prompt_eval_count": prompt_tokens,
            "eval_count": completion_tokens,
        })

    # Markdown summary
    rid = timestamp_id()
    ensure_results_dir()
    section = "## Chat Latency by Model\n\n" + format_table(rows, ["model", "elapsed_ms", "success", "content_len", "error"])
    summary = (
        "## Summary\n\n"
        f"- **[run_label]** {os.getenv('RUN_LABEL', '')}\n"
        f"- **[models_tested]** {len(rows)}\n"
        "- **[note]** Lower time is better; 'success' means the model replied with 'pong'.\n"
    )
    write_markdown_report(
        filename=f"chat_latency_{rid}.md",
        title="Chat Latency Model Sweep",
        sections=[section, summary],
    )

    # JSON artifact for dashboard
    write_json_report(
        filename=f"chat_latency_{rid}.json",
        data={
            "type": "chat_latency",
            "timestamp": rid,
            "results": rows,
            "base_url": base_url,
            "run_label": os.getenv("RUN_LABEL", ""),
        },
    )
