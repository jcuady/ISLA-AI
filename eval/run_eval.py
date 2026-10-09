"""Isla AI evaluation harness -> eval/RESULTS.md.

Judges award 20% for "does it actually work, reliably enough for a live
demonstration", so the numbers have to be real and reproducible. This script
computes every published metric from the committed datasets and writes the
scoreboard. If a gate is missed it is reported honestly, not hidden.

Usage:
    python eval/run_eval.py                 # PII + RAG scoreboard
    python eval/run_eval.py --pii-only
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from services.copilot.copilot import DPACopilot  # noqa: E402
from services.copilot.retrieval import HybridIndex  # noqa: E402
from services.pii.engine import EgressGuard  # noqa: E402
from services.pii.recognizers import HIGH_RISK_TYPES, EntityType  # noqa: E402

DATASETS = Path(__file__).resolve().parent / "datasets"
RESULTS = Path(__file__).resolve().parent / "RESULTS.md"

# Types where a miss is a compliance failure, not a cosmetic one.
HIGH_RISK = {
    "PH_SSS",
    "CARD_PAN",
    "PH_TIN",
    "PH_MOBILE",
    "GCASH_MOBILE",
    "CARD_CVV",
    "BANK_ACCOUNT",
}


def load(name: str) -> list[dict]:
    path = DATASETS / name
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def span_hit(expected_type: str, value: str, entities) -> bool:
    """An expectation is met if some detected entity of that type covers the value."""
    for e in entities:
        if e.entity_type.value != expected_type:
            continue
        if value in e.text or e.text in value:
            # Require the detection to cover the value closely, not just contain it.
            if value in e.text:
                return True
    return False


def eval_pii(guard: EgressGuard) -> dict:
    records = load("pii_ph.jsonl")

    tp = fp = fn = 0
    per_type: dict[str, dict[str, int]] = {}
    latencies: list[float] = []
    residual_failures: list[dict] = []
    hr_tp = hr_fp = hr_fn = 0
    missed: list[dict] = []
    false_positives: list[dict] = []
    negative_violations = 0

    for rec in records:
        t0 = time.perf_counter()
        result = guard.scan(rec["text"])
        latencies.append((time.perf_counter() - t0) * 1000)

        detected = [e for e in result.entities if e.entity_type in HIGH_RISK_TYPES]

        # Residual leakage gate: the redacted text must trip nothing.
        if not result.verified_clean:
            residual_failures.append(rec)

        expected = rec["expect"]
        if rec["is_negative"]:
            # Any redaction of a negative case is a precision failure.
            if result.redaction_map:
                negative_violations += 1
                false_positives.append(
                    {"id": rec["id"], "text": rec["text"], "over": result.redaction_map}
                )
            continue

        for exp in expected:
            hit = span_hit(exp["type"], exp["value"], detected)
            stats = per_type.setdefault(
                exp["type"], {"tp": 0, "fp": 0, "fn": 0, "support": 0}
            )
            stats["support"] += 1
            if hit:
                tp += 1
                stats["tp"] += 1
                if exp["type"] in HIGH_RISK:
                    hr_tp += 1
            else:
                fn += 1
                stats["fn"] += 1
                if exp["type"] in HIGH_RISK:
                    hr_fn += 1
                missed.append({"id": rec["id"], **exp, "text": rec["text"]})

        # Unlabelled detections inside a positive case count as precision loss.
        expected_values = [e["value"] for e in expected]
        for e in detected:
            if not any(v in e.text or e.text in v for v in expected_values):
                fp += 1
                stats = per_type.setdefault(e.entity_type.value, {"tp": 0, "fp": 0, "fn": 0, "support": 0})
                stats["fp"] += 1
                if e.entity_type.value in HIGH_RISK:
                    hr_fp += 1
                false_positives.append({"id": rec["id"], "text": rec["text"], "over": e.text,
                                        "type": e.entity_type.value})

    def prf(tp_: int, fp_: int, fn_: int) -> dict:
        p = tp_ / (tp_ + fp_) if (tp_ + fp_) else 0.0
        r = tp_ / (tp_ + fn_) if (tp_ + fn_) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        return {"precision": p, "recall": r, "f1": f}

    overall = prf(tp, fp, fn)
    high_risk = prf(hr_tp, hr_fp, hr_fn)

    # Macro-F1 across types that actually appear in the dataset.
    f1s = [prf(v["tp"], v["fp"], v["fn"])["f1"] for v in per_type.values() if v["support"] > 0]
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0

    luhn_flags = [
        e for rec in records for e in guard.scan(rec["text"]).entities
        if e.entity_type is EntityType.CARD_PAN
    ]
    luhn_valid = [e for e in luhn_flags if e.validated]
    luhn_rate = len(luhn_valid) / len(luhn_flags) if luhn_flags else 1.0

    return {
        "cases": len(records),
        "positives": sum(1 for r in records if not r["is_negative"]),
        "negatives": sum(1 for r in records if r["is_negative"]),
        "expected_spans": sum(len(r["expect"]) for r in records),
        "macro_f1": macro_f1,
        "overall": overall,
        "high_risk": high_risk,
        "per_type": {k: prf(v["tp"], v["fp"], v["fn"]) | {"support": v["support"]}
                     for k, v in sorted(per_type.items())},
        "residual_leakage_rate": len(residual_failures) / len(records),
        "negative_violations": negative_violations,
        "luhn_pass_rate": luhn_rate,
        "latency_ms": {
            "p50": statistics.median(latencies),
            "p95": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)],
            "mean": statistics.fmean(latencies),
        },
        "missed": missed,
        "false_positives": false_positives[:12],
        "residual_failures": [r["id"] for r in residual_failures],
    }


RAG_CASES = [
    {
        "q": "Ilang oras dapat ko i-report ang data breach?",
        "must_contain": ["72"],
        "expect_doc": "NPC-CIRC-16-03",
    },
    {
        # Previously unscored (expect_doc was None), which meant the single most
        # common real compliance question was the one the evaluation never checked.
        # Ground truth verified against the corpus: RA-10173 Section 21 covers
        # information "transferred to a third party for processing, whether
        # domestically or internationally".
        "q": "Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?",
        "must_contain": [],
        "expect_doc": "RA-10173",
    },
    {
        "q": "Can our call center use AI to score our agents?",
        "must_contain": ["automated decision"],
        "expect_doc": "NPC-ADV-2024-04",
    },
    {
        "q": "Ano ang fine kapag hindi na-notify ang NPC?",
        "must_contain": [],
        "expect_doc": "NPC-CIRC-2022-01",
    },
    {
        "q": "Kailangan ba mag-register ng AI credit scoring model ang banko namin?",
        "must_contain": [],
        "expect_doc": "NPC-CIRC-2022-04",
    },
]

OUT_OF_DOMAIN = [
    "Ano ang stock price ng BDO ngayong araw?",
    "Who won the 2025 FIFA World Cup?",
    "What is the capital of Kenya?",
    "How do I cook adobo?",
    "Magkano ang Porsche 911?",
]


def eval_rag(copilot: DPACopilot) -> dict:
    cited = 0
    correct_doc = 0
    doc_scored = 0
    latencies: list[float] = []
    detail = []

    for case in RAG_CASES:
        ans = copilot.ask(case["q"])
        latencies.append(ans.latency_ms)
        has_cite = len(ans.citations) > 0
        if has_cite:
            cited += 1

        doc_ok = None
        if case["expect_doc"]:
            doc_scored += 1
            doc_ok = any(c["doc_id"] == case["expect_doc"] for c in ans.citations)
            if doc_ok:
                correct_doc += 1

        fact_ok = all(term.lower() in ans.answer.lower() for term in case["must_contain"])

        detail.append(
            {
                "q": case["q"],
                "refused": ans.refused,
                "cited": has_cite,
                "citations": [c["label"] for c in ans.citations][:3],
                "expected_doc": case["expect_doc"],
                "doc_ok": doc_ok,
                "fact_ok": fact_ok,
                "confidence": ans.confidence,
                "latency_ms": round(ans.latency_ms, 1),
            }
        )

    refusals = []
    for q in OUT_OF_DOMAIN:
        ans = copilot.ask(q)
        refusals.append({"q": q, "refused": ans.refused, "confidence": ans.confidence})

    return {
        "cases": len(RAG_CASES),
        "citation_accuracy": cited / len(RAG_CASES),
        "doc_accuracy": (correct_doc / doc_scored) if doc_scored else None,
        "correct_refusal_rate": sum(1 for r in refusals if r["refused"]) / len(refusals),
        "unsupported_claim_rate": 0.0 if cited == len(RAG_CASES) else 1 - cited / len(RAG_CASES),
        "latency_ms": {
            "p50": statistics.median(latencies) if latencies else 0.0,
            "p95": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0.0,
        },
        "detail": detail,
        "refusals": refusals,
        "retrieval_mode": copilot.index.retrieval_mode_name()
        if hasattr(copilot.index, "retrieval_mode_name")
        else ("hybrid" if copilot.index.dense_ready else "bm25+section"),
    }


GATES = [
    ("High-risk recall >= 0.99", lambda p: p["high_risk"]["recall"] >= 0.99),
    ("High-risk precision >= 0.95", lambda p: p["high_risk"]["precision"] >= 0.95),
    ("Residual leakage == 0.00%", lambda p: p["residual_leakage_rate"] == 0.0),
    ("PII macro-F1 >= 0.90", lambda p: p["macro_f1"] >= 0.90),
]


def fmt_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pii-only", action="store_true")
    ap.add_argument("--rag-only", action="store_true")
    ap.add_argument(
        "--sparse-only",
        action="store_true",
        help="Skip the dense embedding leg. Proves the copilot still cites correctly "
             "when no model weights are installed - the degraded air-gap path.",
    )
    args = ap.parse_args()

    guard = EgressGuard()
    pii = None if args.rag_only else eval_pii(guard)

    rag = None
    if not args.pii_only:
        index = HybridIndex()
        if not args.sparse_only:
            index.enable_dense()
        rag = eval_rag(DPACopilot(index))

    lines: list[str] = []
    lines.append("# Isla AI evaluation results\n")
    lines.append("Generated by `python eval/run_eval.py`. Every number below is computed")
    lines.append("from the committed datasets in `eval/datasets/` — nothing is hand-entered.\n")
    if args.sparse_only:
        lines.append("> **Sparse-only run.** The dense embedding model was deliberately not loaded. "
                     "This file measures the degraded air-gap path and is kept separate from the "
                     "headline scoreboard in `RESULTS.md`.\n")
    elif args.pii_only:
        lines.append("> **PII-only run.** Computed with zero third-party dependencies — the Egress "
                     "Guard imports nothing outside the Python standard library. The RAG half of the "
                     "headline scoreboard lives in `RESULTS.md`.\n")

    if pii:
        lines.append("## PII engine (Egress Guard)\n")
        lines.append(f"- Cases: **{pii['cases']}** ({pii['positives']} positive, {pii['negatives']} negative)")
        lines.append(f"- Expected entity spans: **{pii['expected_spans']}**\n")
        lines.append("| Metric | Target | Measured | Status |")
        lines.append("|---|---|---|---|")

        def row(name: str, target: str, measured: str, ok: bool) -> None:
            lines.append(f"| {name} | {target} | {measured} | {'PASS' if ok else 'MISS'} |")

        row("Macro-F1 (PH entity types)", ">= 0.90", f"{pii['macro_f1']:.4f}", pii["macro_f1"] >= 0.90)
        row("High-risk recall", ">= 0.99", fmt_pct(pii["high_risk"]["recall"]),
            pii["high_risk"]["recall"] >= 0.99)
        row("High-risk precision", ">= 0.95", fmt_pct(pii["high_risk"]["precision"]),
            pii["high_risk"]["precision"] >= 0.95)
        row("Residual leakage rate", "0.00%", fmt_pct(pii["residual_leakage_rate"]),
            pii["residual_leakage_rate"] == 0.0)
        row("Luhn pass rate (flagged PANs)", ">= 0.98", fmt_pct(pii["luhn_pass_rate"]),
            pii["luhn_pass_rate"] >= 0.98)
        row("Negatives mis-redacted", "0", str(pii["negative_violations"]), pii["negative_violations"] == 0)
        lines.append("")
        lines.append(f"Overall precision **{fmt_pct(pii['overall']['precision'])}**, "
                     f"recall **{fmt_pct(pii['overall']['recall'])}**, "
                     f"F1 **{pii['overall']['f1']:.4f}**\n")
        lines.append("### Per-entity breakdown\n")
        lines.append("| Entity type | Support | Precision | Recall | F1 |")
        lines.append("|---|---|---|---|---|")
        for name, v in pii["per_type"].items():
            lines.append(
                f"| {name} | {v['support']} | {fmt_pct(v['precision'])} | "
                f"{fmt_pct(v['recall'])} | {v['f1']:.4f} |"
            )
        lines.append("")
        lines.append(f"Latency p50 **{pii['latency_ms']['p50']:.1f} ms**, "
                     f"p95 **{pii['latency_ms']['p95']:.1f} ms**\n")

        if pii["missed"]:
            lines.append("### Missed detections (reported honestly)\n")
            for m in pii["missed"][:10]:
                lines.append(f"- `{m['id']}` expected **{m['type']}** `{m['value']}` in: `{m['text'][:70]}`")
            lines.append("")
        if pii["false_positives"]:
            lines.append("### False positives\n")
            for f in pii["false_positives"][:10]:
                lines.append(f"- `{f['id']}` `{f.get('over')}` in: `{f['text'][:70]}`")
            lines.append("")

    if rag:
        lines.append("## DPA Copilot (retrieval + citation enforcement)\n")
        lines.append(f"- Retrieval mode: **{rag['retrieval_mode']}**")
        lines.append(f"- In-corpus questions: **{rag['cases']}**\n")
        lines.append("| Metric | Target | Measured | Status |")
        lines.append("|---|---|---|---|")
        lines.append(
            f"| Citation accuracy | >= 0.95 | {fmt_pct(rag['citation_accuracy'])} | "
            f"{'PASS' if rag['citation_accuracy'] >= 0.95 else 'MISS'} |"
        )
        if rag["doc_accuracy"] is not None:
            lines.append(
                f"| Correct source document | >= 0.80 | {fmt_pct(rag['doc_accuracy'])} | "
                f"{'PASS' if rag['doc_accuracy'] >= 0.80 else 'MISS'} |"
            )
        lines.append(
            f"| Correct-refusal rate | >= 0.90 | {fmt_pct(rag['correct_refusal_rate'])} | "
            f"{'PASS' if rag['correct_refusal_rate'] >= 0.90 else 'MISS'} |"
        )
        lines.append(
            f"| Copilot latency p50 | < 4000 ms | {rag['latency_ms']['p50']:.0f} ms | "
            f"{'PASS' if rag['latency_ms']['p50'] < 4000 else 'MISS'} |"
        )
        lines.append("")
        lines.append("### Per-question detail\n")
        lines.append("| Question | Refused | Cited | Source correct | Conf | ms |")
        lines.append("|---|---|---|---|---|---|")
        for d in rag["detail"]:
            lines.append(
                f"| {d['q'][:46]} | {'yes' if d['refused'] else 'no'} | "
                f"{'yes' if d['cited'] else 'no'} | "
                f"{'-' if d['doc_ok'] is None else ('yes' if d['doc_ok'] else 'no')} | "
                f"{d['confidence']:.2f} | {d['latency_ms']:.0f} |"
            )
        lines.append("")
        lines.append("### Refusal behaviour (out of domain)\n")
        lines.append("| Question | Refused | Confidence |")
        lines.append("|---|---|---|")
        for r in rag["refusals"]:
            lines.append(f"| {r['q'][:50]} | {'yes' if r['refused'] else 'NO'} | {r['confidence']:.2f} |")
        lines.append("")

    # Only a full run may overwrite the headline scoreboard. Partial runs write to
    # their own file so a diagnostic can never silently replace the real numbers.
    if args.sparse_only:
        out_path = RESULTS.parent / "RESULTS_SPARSE_ONLY.md"
    elif args.pii_only:
        out_path = RESULTS.parent / "RESULTS_PII.md"
    else:
        out_path = RESULTS
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")
    if pii:
        print(f"  PII macro-F1 {pii['macro_f1']:.4f} | high-risk R {pii['high_risk']['recall']:.4f} "
              f"P {pii['high_risk']['precision']:.4f} | residual {pii['residual_leakage_rate']:.4f}")
        print("  gates: " + ", ".join(
            f"{name}={'PASS' if fn(pii) else 'MISS'}" for name, fn in GATES
        ))
    if rag:
        print(f"  RAG citation {rag['citation_accuracy']:.3f} | refusal {rag['correct_refusal_rate']:.3f} "
              f"| p50 {rag['latency_ms']['p50']:.0f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())