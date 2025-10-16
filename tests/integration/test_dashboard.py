import os
import sys
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from .utils import ensure_results_dir, load_json_artifacts, write_markdown_report, format_table, timestamp_id  # noqa: E402


@pytest.mark.local_ollama
def test_build_dashboard_report():
    """Aggregate JSON artifacts and build a single comparison dashboard Markdown."""
    ensure_results_dir()
    items = load_json_artifacts("*.json")

    # Partition by type
    connectivity = [x for x in items if x.get("type") == "connectivity"]
    embeds = [x for x in items if x.get("type") == "embeddings_throughput"]
    chats = [x for x in items if x.get("type") == "chat_latency"]
    accs = [x for x in items if x.get("type") == "accuracy"]

    sections = []
    # Aggregates for snapshot
    best_chat = None
    best_embed_overall = None
    total_embed_tokens = 0
    total_chat_prompt_tokens = 0
    total_chat_completion_tokens = 0
    latest_acc = None

    # Connectivity summary
    if connectivity:
        rows = []
        for c in connectivity:
            phase_ms = sum(float(p.get("elapsed_ms", 0)) for p in c.get("phases", []))
            rows.append({
                "timestamp": c.get("timestamp"),
                "base_url": c.get("base_url"),
                "total_elapsed_ms": round(phase_ms, 2),
            })
        sections.append("## Connectivity Summary\n\n" + format_table(rows, ["timestamp", "base_url", "total_elapsed_ms"]))
    else:
        sections.append("## Connectivity Summary\n\nNo connectivity artifacts found.\n")

    # Embeddings throughput comparison
    if embeds:
        rows = []
        # Best by items/sec per dataset_size
        best_by_size = {}
        for e in embeds:
            ds = int(e.get("dataset_size", 0))
            m = e.get("metrics", {})
            row = {
                "timestamp": e.get("timestamp"),
                "dataset_size": ds,
                "model": e.get("model", ""),
                "items_per_sec": m.get("items_per_sec", 0),
                "latency_p95_ms": m.get("latency_p95_ms", 0),
                "errors": m.get("errors", 0),
            }
            # Track totals for snapshot
            try:
                total_embed_tokens += int(m.get("approx_input_tokens_total", 0) or 0)
            except Exception:
                pass
            rows.append(row)
            curr = best_by_size.get(ds)
            if curr is None or float(row["items_per_sec"]) > float(curr["items_per_sec"]):
                best_by_size[ds] = row
            if (best_embed_overall is None) or float(row["items_per_sec"]) > float(best_embed_overall["items_per_sec"]):
                best_embed_overall = row
        sections.append("## Embeddings Throughput\n\n" + format_table(rows, ["timestamp", "dataset_size", "model", "items_per_sec", "latency_p95_ms", "errors"]))

        # Best performers
        best_rows = list(best_by_size.values())
        sections.append("## Best Embedding Performance by Dataset Size\n\n" + format_table(best_rows, ["dataset_size", "model", "items_per_sec", "latency_p95_ms"]))
    else:
        sections.append("## Embeddings Throughput\n\nNo embedding artifacts found.\n")

    # Chat latency comparison across all discovered models
    if chats:
        flat = []
        for c in chats:
            ts = c.get("timestamp")
            for r in c.get("results", []):
                flat.append({
                    "timestamp": ts,
                    "model": r.get("model", ""),
                    "elapsed_ms": r.get("elapsed_ms", 0),
                    "success": r.get("success", False),
                })
        sections.append("## Chat Latency (All Models)\n\n" + format_table(flat, ["timestamp", "model", "elapsed_ms", "success"]))

        # Best successful model (minimum elapsed_ms)
        best = None
        for r in flat:
            if not r.get("success"):
                continue
            if best is None or float(r["elapsed_ms"]) < float(best["elapsed_ms"]):
                best = r
        if best:
            best_chat = best
            sections.append(
                "## Best Chat Model\n\n"
                f"- **[model]** {best['model']}\n"
                f"- **[elapsed_ms]** {best['elapsed_ms']}\n"
                f"- **[timestamp]** {best['timestamp']}\n"
            )
    else:
        sections.append("## Chat Latency (All Models)\n\nNo chat latency artifacts found.\n")

    # Accuracy comparison
    if accs:
        arows = []
        for a in accs:
            m = a.get("metrics", {})
            arows.append({
                "timestamp": a.get("timestamp"),
                "run_label": a.get("run_label", ""),
                "study": a.get("study", ""),
                "top1": m.get("top1", 0),
                "top3": m.get("top3", 0),
                "top5": m.get("top5", 0),
                "mrr@5": m.get("mrr@5", 0),
                "ndcg@5": m.get("ndcg@5", 0),
                "valid": m.get("valid", 0),
                "total": m.get("total", 0),
            })
        sections.append("## Accuracy (Mapping to Target Codebook)\n\n" + format_table(arows, ["timestamp", "run_label", "study", "top1", "top3", "top5", "mrr@5", "ndcg@5", "valid", "total"]))
        # Latest accuracy for snapshot
        try:
            latest_acc = max(arows, key=lambda x: str(x.get("timestamp", ""))) if arows else None
        except Exception:
            latest_acc = arows[-1] if arows else None
    else:
        sections.append("## Accuracy (Mapping to Target Codebook)\n\nNo accuracy artifacts found.\n")

    # Token summary
    token_sections = []
    if embeds:
        erows = []
        for e in embeds:
            m = e.get("metrics", {})
            erows.append({
                "timestamp": e.get("timestamp"),
                "run_label": e.get("run_label", ""),
                "dataset_size": e.get("dataset_size", 0),
                "text_length_tier": m.get("text_length_tier", ""),
                "approx_input_tokens_total": m.get("approx_input_tokens_total", 0),
            })
        token_sections.append("### Embeddings Token Estimate\n\n" + format_table(erows, ["timestamp", "run_label", "dataset_size", "text_length_tier", "approx_input_tokens_total"]))
    if chats:
        crows = []
        for c in chats:
            ts = c.get("timestamp")
            rl = c.get("run_label", "")
            base = c.get("base_url", "")
            pt = 0
            ct = 0
            cnt = 0
            for r in c.get("results", []):
                cnt += 1
                try:
                    pt += int(r.get("prompt_eval_count") or 0)
                    ct += int(r.get("eval_count") or 0)
                except Exception:
                    pass
            total_chat_prompt_tokens += pt
            total_chat_completion_tokens += ct
            crows.append({
                "timestamp": ts,
                "run_label": rl,
                "base_url": base,
                "models": cnt,
                "prompt_tokens": pt,
                "completion_tokens": ct,
            })
        token_sections.append("### Chat Token Usage\n\n" + format_table(crows, ["timestamp", "run_label", "base_url", "models", "prompt_tokens", "completion_tokens"]))
    if token_sections:
        sections.append("## Token Summary\n\n" + "\n".join(token_sections))

    # Guidance section with Snapshot
    snap_lines = ["## Guidance\n\n",]
    # Snapshot bullets (non-technical)
    if best_chat:
        snap_lines.append(f"- **[Fastest chat]** {best_chat['model']} at {best_chat['elapsed_ms']} ms.\n")
    else:
        snap_lines.append("- **[Fastest chat]** N/A.\n")
    if best_embed_overall:
        snap_lines.append(
            f"- **[Best embeddings]** Size {best_embed_overall['dataset_size']} at {best_embed_overall['items_per_sec']} items/sec (p95 {best_embed_overall['latency_p95_ms']} ms).\n"
        )
    else:
        snap_lines.append("- **[Best embeddings]** N/A.\n")
    if latest_acc:
        snap_lines.append(
            f"- **[Accuracy]** {latest_acc.get('study','')} — Top‑1 {latest_acc.get('top1',0)}, Top‑3 {latest_acc.get('top3',0)}, Top‑5 {latest_acc.get('top5',0)}.\n"
        )
    else:
        snap_lines.append("- **[Accuracy]** N/A.\n")
    snap_lines.append(
        f"- **[Tokens]** Embeddings ≈ {total_embed_tokens} • Chat in {total_chat_prompt_tokens} / out {total_chat_completion_tokens}.\n"
    )
    # Original guidance bullets
    snap_lines.append("\n- **[Best model]** Higher items/sec with low p95 latency is preferred.\n")
    snap_lines.append("- **[Stability]** Ensure errors = 0.\n")
    snap_lines.append("- **[Scaling]** Compare 100 vs 1000 dataset sizes to see throughput trend.\n")
    guidance = "".join(snap_lines)
    sections.append(guidance)

    rid = timestamp_id()
    write_markdown_report(
        filename=f"dashboard_{rid}.md",
        title="Local Integration Dashboard",
        sections=sections,
    )
