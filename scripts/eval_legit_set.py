"""Evaluasi set legit Barat & Lokal lewat pipeline penuh (T31.1).

Membaca `data/realworld/legit_barat_lokal.txt` (satu URL per baris, `#` = komentar),
memanggil `predict_url` untuk setiap URL, lalu menulis ringkasan dan hasil per URL ke
`results/data/legit_barat_lokal_results.json`.

Evaluasi ini sengaja offline: Layer 0 Google Safe Browsing dimatikan agar hasil tidak
bergantung pada kuota/jawaban jaringan. Snapshot feed denylist dipakai dengan batas
umur 168 jam karena snapshot evaluasi disimpan secara historis; status feed dicatat di
JSON. Tidak ada URL yang dibuka atau di-resolve.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Harus diset sebelum `src.config` diimpor: load_dotenv(override=False) tidak menimpa env shell.
os.environ["PHISHGUARD_USE_GOOGLE"] = "false"
os.environ["PHISHGUARD_FEED_MAX_AGE_HOURS"] = "168"

from src.config import FEED_MAX_AGE_HOURS, VERDICT_LEGITIMATE
from src.denylist import feed_status, reset_cache
from src.predict import _band, _model_c_probability, predict_url

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TXT = ROOT / "data" / "realworld" / "legit_barat_lokal.txt"
DEFAULT_OUT = ROOT / "results" / "data" / "legit_barat_lokal_results.json"


def load_urls(path: Path) -> list[str]:
    """Baca URL, abaikan baris kosong dan komentar."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def band_counts(records: list[dict]) -> dict[str, dict[str, int]]:
    """Sebaran zona skor Model B dan C: tinggi >=0.65, sedang 0.40-0.65, rendah <0.40."""
    out = {}
    for key, name in (("probability", "model_b"), ("probability_c", "model_c")):
        counts = {"tinggi": 0, "sedang": 0, "rendah": 0, "tidak_dinilai": 0}
        for record in records:
            probability = record.get(key)
            counts["tidak_dinilai" if probability is None else _band(probability)] += 1
        out[name] = counts
    return out


def evaluate(path: Path) -> dict:
    urls = load_urls(path)
    reset_cache()
    status, feed_path, feed_detail = feed_status()
    results, errors = [], []

    for url in urls:
        try:
            result = predict_url(url)
        except ValueError as exc:
            errors.append({"url": url, "error": str(exc)})
            continue
        results.append(
            {
                "url": result["url"],
                "verdict": result["verdict"],
                "risk_level": result["risk_level"],
                "decision_source": result["decision_source"],
                "probability": result["probability"],
                "probability_c": _model_c_probability(url) if result["probability"] is not None else None,
                "reason": result["reason"],
                "trail": [
                    {"layer": item["layer"], "result": item["result"]}
                    for item in result["trail"]
                ],
            }
        )

    by_verdict = Counter(item["verdict"] for item in results)
    by_decision = Counter(item["decision_source"] for item in results)
    by_risk = Counter(item["risk_level"] for item in results)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/eval_legit_set.py",
        "input": str(path.relative_to(ROOT)).replace("\\", "/"),
        "config": {
            "use_google": False,
            "feed_max_age_hours": FEED_MAX_AGE_HOURS,
        },
        "definitions": {
            "verdict": "PHISHING / SUSPICIOUS (TIDAK TERVERIFIKASI) / LEGITIMATE",
            "band_edges": {
                "rendah": "< 0.40",
                "sedang": "0.40 <= P < 0.65",
                "tinggi": ">= 0.65",
            },
            "probability_null": "allowlist atau short-circuit lain; model tidak memberi skor",
        },
        "feed": {
            "status": status,
            "path": str(feed_path.relative_to(ROOT)).replace("\\", "/") if feed_path and feed_path.is_relative_to(ROOT) else (str(feed_path) if feed_path else None),
            "detail": feed_detail,
        },
        "summary": {
            "n_input": len(urls),
            "n_evaluated": len(results),
            "n_error": len(errors),
            "by_verdict": dict(by_verdict),
            "by_risk_level": dict(by_risk),
            "by_decision_source": dict(by_decision),
            "band_counts": band_counts(results),
            "model_c_available": any(item["probability_c"] is not None for item in results),
            "non_legitimate": [
                {
                    "url": item["url"],
                    "verdict": item["verdict"],
                    "risk_level": item["risk_level"],
                    "decision_source": item["decision_source"],
                    "probability": item["probability"],
                }
                for item in results
                if item["verdict"] != VERDICT_LEGITIMATE
            ],
        },
        "results": results,
        "errors": errors,
    }


def realworld_band_distribution() -> dict:
    """Sebaran band Model B/C pada set real-world, memakai fungsi yang sama dengan T30."""
    from scripts.test_layers import band_counts as layer_band_counts
    from scripts.test_layers import load_realworld, model_probabilities

    path = ROOT / "data" / "realworld" / "urls.csv"
    if not path.exists():
        return {"status": "MISSING", "reason": f"{path} tidak ada"}
    rows, skipped = load_realworld(path)
    prob_b, prob_c, model_c_available = model_probabilities([row["url"] for row in rows])
    return {
        "status": "OK",
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "n": len(rows),
        "n_skipped_invalid": skipped,
        "model_c_available": model_c_available,
        "bands": layer_band_counts(prob_b, prob_c),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluasi set legit Barat & Lokal (offline).")
    parser.add_argument("--txt", type=Path, default=DEFAULT_TXT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--band-out",
        type=Path,
        default=ROOT / "results" / "data" / "band_distribution.json",
        help="JSON distribusi band untuk set real-world dan set legit",
    )
    args = parser.parse_args(argv)

    if not args.txt.exists():
        print(f"Berkas input tidak ada: {args.txt}")
        return 1

    data = evaluate(args.txt)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bands = {
        "generated_at": data["generated_at"],
        "script": "scripts/eval_legit_set.py",
        "definitions": data["definitions"],
        "sources": {
            "legit_barat_lokal": {
                "path": data["input"],
                "n": data["summary"]["n_evaluated"],
                "bands": data["summary"]["band_counts"],
                "model_c_available": data["summary"]["model_c_available"],
                "note": "Hanya URL yang dinilai model; allowlist tidak punya probability.",
            },
            "realworld": realworld_band_distribution(),
        },
    }
    args.band_out.parent.mkdir(parents=True, exist_ok=True)
    args.band_out.write_text(json.dumps(bands, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = data["summary"]
    print(f"Input      : {summary['n_input']} URL ({data['input']})")
    print(f"Dievaluasi : {summary['n_evaluated']} URL, error {summary['n_error']}")
    print(f"Verdict    : {summary['by_verdict']}")
    print(f"Sumber     : {summary['by_decision_source']}")
    print(f"Band       : {summary['band_counts']}")
    print(f"JSON       : {args.out}")
    print(f"Band JSON  : {args.band_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
