import os
import sys
import platform
import time
from datetime import datetime
from typing import List, Dict, Any
import json
import glob

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def ensure_results_dir() -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    return RESULTS_DIR


def timestamp() -> str:
    # Example: 2025-10-03 18:50:00 local time
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_id() -> str:
    # Example: 20251003_185000 for filenames
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def env_info() -> Dict[str, Any]:
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "run_label": os.getenv("RUN_LABEL", ""),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", ""),
        "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", ""),
        "chat_model": os.getenv("OLLAMA_CHAT_MODEL", ""),
        "ai_request_timeout": os.getenv("AI_REQUEST_TIMEOUT", ""),
    }


def p95(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = int(0.95 * (len(s) - 1))
    return float(s[k])


def write_markdown_report(filename: str, title: str, sections: List[str]) -> str:
    ensure_results_dir()
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Generated: {timestamp()}\n\n")
        # Variable definitions block
        f.write("## Variable Definitions\n\n")
        f.write("- **[latency_avg_ms]** Average latency in milliseconds per item.\n")
        f.write("- **[latency_p95_ms]** 95th percentile latency in milliseconds per item.\n")
        f.write("- **[items_per_sec]** Processed items per second (throughput).\n")
        f.write("- **[dataset_size]** Number of items processed.\n")
        f.write("- **[retries]** Count of retry attempts triggered by the wrapper.\n")
        f.write("- **[errors]** Number of failed items.\n")
        f.write("- **[timeout_s]** Request timeout used in seconds.\n\n")

        # Environment block
        info = env_info()
        f.write("## Environment\n\n")
        for k, v in info.items():
            f.write(f"- **[{k}]** {v}\n")
        f.write("\n")

        for s in sections:
            f.write(s)
            if not s.endswith("\n"):
                f.write("\n")
            f.write("\n")
    return path


def write_json_report(filename: str, data: Dict[str, Any]) -> str:
    """Write a JSON summary artifact alongside Markdown for easy aggregation."""
    ensure_results_dir()
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_json_artifacts(pattern: str = "*.json") -> List[Dict[str, Any]]:
    """Load JSON summaries from the results directory (for dashboard)."""
    ensure_results_dir()
    items: List[Dict[str, Any]] = []
    for p in glob.glob(os.path.join(RESULTS_DIR, pattern)):
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict):
                    obj["__file"] = os.path.basename(p)
                    items.append(obj)
        except Exception:
            continue
    return items


def format_table(rows: List[Dict[str, Any]], headers: List[str]) -> str:
    # Simple Markdown table from a list of dicts
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(str(r.get(h, "")) for h in headers) + " |")
    return "\n" + "\n".join(out) + "\n"


def ms(x: float) -> float:
    return round(x * 1000.0, 2)


def per_sec(n_items: int, seconds: float) -> float:
    if seconds <= 0:
        return 0.0
    return round(n_items / seconds, 2)
