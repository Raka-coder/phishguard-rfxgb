"""Evaluasi isolasi & kumulatif lapisan L0-L4 (T30).

Menjalankan tiap lapisan sendirian lalu bertingkat pada set dunia nyata
(`data/realworld/urls.csv`), lalu menulis semua angka ke `docs/layer_tests.json`.
Tidak ada angka metrik yang ditulis manual; dokumen harus merujuk JSON ini.

Catatan kejujuran:
- L0 tidak punya kebenaran offline. Mode mock menandai URL dengan
  `source == openphish` sehingga angkanya adalah **skenario batas atas**, bukan
  akurasi Google Safe Browsing.
- Model B/C tidak pernah memvonis PHISHING (desain); SUSPICIOUS dilaporkan
  terpisah agar tidak terhitung sebagai deteksi.
- Lapisan peniruan merek (docs/TASKS.md T20) belum ada, jadi tidak diuji.
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.eval_realworld import metrics
from src.config import (
    LABEL_LEGIT,
    LABEL_PHISH,
    THRESHOLD_PHISHING,
    VERDICT_LEGITIMATE,
    VERDICT_PHISHING,
    VERDICT_SUSPICIOUS,
)
from src.denylist import feed_status, is_denied, load_feed, normalize_url, reset_cache
from src.feature_utils import to_frame
from src.features_host import to_host_frame
from src.predict import _band, _decide, _load, _load_model_c
from src.reputation import is_shortener, is_trusted

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "realworld" / "urls.csv"
DEFAULT_OUT = ROOT / "docs" / "layer_tests.json"
_ALLOWED_SCHEMES = {"http", "https"}
_GUARD_MAX_OVERLAP_PCT = 5.0


def _relative(path: Path | None) -> str | None:
    """Path relatif ke root dengan garis miring depan agar sama di Windows/Linux."""
    if path is None:
        return None
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    return str(shown).replace("\\", "/")


# Urutan lapisan di produksi: L0 GSB -> L1 denylist -> L2 allowlist -> L3 model -> L4 shortener.
STAGES = [
    ("L1", ["L1"]),
    ("L1+L2", ["L1", "L2"]),
    ("L1+L2+L3", ["L1", "L2", "L3"]),
    ("L1+L2+L3+L4", ["L1", "L2", "L3", "L4"]),
    ("L0+L1+L2+L3+L4 (mock)", ["L0", "L1", "L2", "L3", "L4"]),
]


def is_valid_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme.lower() in _ALLOWED_SCHEMES and bool(parts.hostname)


def load_realworld(path: Path) -> tuple[list[dict], int]:
    """Baca url/label/source; kembalikan (baris valid, jumlah baris tidak valid)."""
    with path.open(encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))
    rows, skipped = [], 0
    for row in raw:
        url, label = (row.get("url") or "").strip(), (row.get("label") or "").strip()
        if label not in {"0", "1"} or not is_valid_url(url):
            skipped += 1
            continue
        rows.append({"url": url, "label": int(label), "source": (row.get("source") or "").strip()})
    return rows, skipped


def model_probabilities(urls: list[str]) -> tuple[list[float], list[float | None], bool]:
    """P(phishing) Model B dan C untuk sekumpulan URL (batch); C None bila artefak hilang."""
    pipe, tld, _ = _load()
    frame = to_frame(urls, tld["map"], tld["default"])
    proba = pipe.predict_proba(frame.to_numpy(dtype="float32"))
    column = list(pipe.classes_).index(LABEL_PHISH)
    prob_b = [float(row[column]) for row in proba]

    loaded = _load_model_c()
    if loaded is None:
        return prob_b, [None] * len(urls), False
    pipe_c, tld_c = loaded
    frame_c = to_host_frame(urls, tld_c.get("map") or {}, float(tld_c.get("default", 0.5)), strip_www=True)
    proba_c = pipe_c.predict_proba(frame_c.to_numpy(dtype="float32"))
    column_c = list(pipe_c.classes_).index(LABEL_PHISH)
    return prob_b, [float(row[column_c]) for row in proba_c], True


def overlap_guard(test_urls: list[str], feed_keys: set[str]) -> dict:
    """Guard anti-melingkar: feed denylist tidak boleh memuat set uji."""
    test_keys = {key for key in (normalize_url(u) for u in test_urls) if key}
    overlap = len(test_keys & feed_keys)
    pct = round(overlap / len(test_keys) * 100, 2) if test_keys else 0.0
    return {
        "test_unique_urls": len(test_keys),
        "feed_entries": len(feed_keys),
        "overlap_urls": overlap,
        "overlap_pct_of_test": pct,
        "max_overlap_pct": _GUARD_MAX_OVERLAP_PCT,
        "ok": pct <= _GUARD_MAX_OVERLAP_PCT,
        "note": "Feed harus snapshot berbeda dari set uji; bila tidak, evaluasi L1 melingkar.",
    }


def stage_verdict(
    url: str,
    stages: list[str],
    prob_b: float,
    prob_c: float | None,
    gsb_match: bool,
    feed_ok: bool,
) -> str:
    """Vonis pada tingkatan lapisan tertentu; urutan sama dengan predict_url()."""
    host = (urlsplit(url).hostname or "").lower()
    if "L0" in stages and gsb_match:
        return VERDICT_PHISHING
    if "L1" in stages and feed_ok and is_denied(url):
        return VERDICT_PHISHING
    if "L2" in stages and is_trusted(host):
        return VERDICT_LEGITIMATE
    if "L3" in stages:
        return _decide(prob_b, prob_c, "L4" in stages and is_shortener(host))[0]
    return VERDICT_LEGITIMATE


def band_counts(prob_b: list[float], prob_c: list[float | None] | None = None) -> dict:
    """Sebaran zona skor: tinggi >=0.65, sedang 0.40-0.65, rendah <0.40."""

    def _counts(values: list[float | None]) -> dict[str, int]:
        counts = {"tinggi": 0, "sedang": 0, "rendah": 0, "tidak_dinilai": 0}
        for value in values:
            counts["tidak_dinilai" if value is None else _band(value)] += 1
        return counts

    model_c = _counts(prob_c) if prob_c and any(v is not None for v in prob_c) else None
    return {"model_b": _counts(prob_b), "model_c": model_c}


def isolation_block(name: str, kind: str, signal: str, rows: list[dict], flags: list[bool], elapsed_ms: float) -> dict:
    """Profil satu lapisan sendirian: flag pada phishing vs legit + waktu rata-rata."""
    phish = [flag for row, flag in zip(rows, flags) if row["label"] == LABEL_PHISH]
    legit = [flag for row, flag in zip(rows, flags) if row["label"] == LABEL_LEGIT]

    def _rate(values: list[bool]) -> dict:
        return {
            "n": len(values),
            "flagged": sum(values),
            "rate": round(sum(values) / len(values), 4) if values else None,
        }

    return {
        "layer": name,
        "kind": kind,  # deny = flag berarti risiko; trust = flag berarti diterima sebagai legit
        "signal": signal,
        "phish": _rate(phish),
        "legit": _rate(legit),
        "mean_ms": round(elapsed_ms / len(rows), 3) if rows else None,
    }


def cumulative_block(label: str, stages: list[str], rows: list[dict], verdicts: list[str], elapsed_ms: float) -> dict:
    y_true = [row["label"] for row in rows]
    y_pred = [LABEL_PHISH if verdict == VERDICT_PHISHING else LABEL_LEGIT for verdict in verdicts]
    return {
        "stage": label,
        "stages": stages,
        "metrics": metrics(y_true, y_pred),
        "suspicious": {
            "phish": sum(1 for row, v in zip(rows, verdicts) if v == VERDICT_SUSPICIOUS and row["label"] == LABEL_PHISH),
            "legit": sum(1 for row, v in zip(rows, verdicts) if v == VERDICT_SUSPICIOUS and row["label"] == LABEL_LEGIT),
        },
        "mean_ms": round(elapsed_ms / len(rows), 3) if rows else None,
    }


def run(csv_path: Path, max_age_hours: int) -> dict:
    os.environ["PHISHGUARD_FEED_MAX_AGE_HOURS"] = str(max_age_hours)
    reset_cache()

    rows, skipped = load_realworld(csv_path)
    urls = [row["url"] for row in rows]
    prob_b, prob_c, model_c_available = model_probabilities(urls)

    status, feed_path, feed_detail = feed_status()
    feed_keys = load_feed() if status == "ok" else set()
    guard = overlap_guard(urls, feed_keys)
    if status == "ok" and not guard["ok"]:
        raise SystemExit(
            f"Guard gagal: {guard['overlap_urls']} URL set uji ada di feed "
            f"({guard['overlap_pct_of_test']}%); gunakan snapshot feed lain."
        )

    # Skenario L0: mock label-aware, batas atas mekanika short-circuit (bukan akurasi GSB).
    gsb_matches = {row["url"] for row in rows if row["source"] == "openphish"}

    isolation = []
    started = time.perf_counter()
    flags = [url in gsb_matches for url in urls]
    isolation.append(
        isolation_block(
            "L0_google_sb",
            "deny",
            "mock: source == openphish (skenario batas atas, bukan akurasi GSB)",
            rows,
            flags,
            (time.perf_counter() - started) * 1000,
        )
    )

    started = time.perf_counter()
    flags = [is_denied(url) for url in urls] if status == "ok" else [False] * len(urls)
    isolation.append(
        isolation_block(
            "L1_denylist",
            "deny",
            "URL ada di snapshot feed lokal" if status == "ok" else "feed tidak aktif",
            rows,
            flags,
            (time.perf_counter() - started) * 1000,
        )
    )

    started = time.perf_counter()
    flags = [is_trusted((urlsplit(url).hostname or "").lower()) for url in urls]
    isolation.append(
        isolation_block("L2_allowlist", "trust", "domain ada di allowlist tepercaya", rows, flags, (time.perf_counter() - started) * 1000)
    )

    started = time.perf_counter()
    flags = [_decide(pb, pc, False)[0] == VERDICT_SUSPICIOUS for pb, pc in zip(prob_b, prob_c)]
    isolation.append(
        isolation_block(
            "L3_model_band",
            "deny",
            f"vonis model SUSPICIOUS (ambang risiko {THRESHOLD_PHISHING})",
            rows,
            flags,
            (time.perf_counter() - started) * 1000,
        )
    )

    started = time.perf_counter()
    flags = [is_shortener((urlsplit(url).hostname or "").lower()) for url in urls]
    isolation.append(
        isolation_block("L4_shortener", "deny", "host adalah layanan pemendek URL", rows, flags, (time.perf_counter() - started) * 1000)
    )

    cumulative = []
    for label, stages in STAGES:
        started = time.perf_counter()
        verdicts = [
            stage_verdict(url, stages, pb, pc, url in gsb_matches, status == "ok")
            for url, pb, pc in zip(urls, prob_b, prob_c)
        ]
        cumulative.append(cumulative_block(label, stages, rows, verdicts, (time.perf_counter() - started) * 1000))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/test_layers.py",
        "dataset": {
            "path": _relative(csv_path),
            "n_total": len(rows),
            "n_phish": sum(1 for row in rows if row["label"] == LABEL_PHISH),
            "n_legit": sum(1 for row in rows if row["label"] == LABEL_LEGIT),
            "n_invalid_skipped": skipped,
        },
        "feed": {
            "path": _relative(feed_path),
            "status": status,
            "detail": feed_detail,
            "max_age_hours_used": max_age_hours,
        },
        "guard": guard,
        "model_c_available": model_c_available,
        "band_distribution": band_counts(prob_b, prob_c),
        "definitions": {
            "positive": "phishing (label 0)",
            "suspicious": "dihitung non-phishing, dilaporkan terpisah",
            "isolation_kind_deny": "flag = lapisan menaikkan risiko; ideal: tinggi pada phishing, nol pada legit",
            "isolation_kind_trust": "flag = lapisan menerima sebagai legit; ideal: tinggi pada legit, nol pada phishing",
            "cumulative": "hanya lapisan pada `stages` yang aktif; sisanya LEGITIMATE",
        },
        "isolation": isolation,
        "cumulative": cumulative,
        "notes": [
            "L0 dievaluasi dengan mock label-aware (source == openphish) sebagai skenario batas atas, bukan akurasi Google Safe Browsing.",
            "Model B/C tidak pernah memvonis PHISHING; SUSPICIOUS dihitung non-phishing dan dilaporkan terpisah.",
            "Lapisan peniruan merek (docs/TASKS.md T20) belum diimplementasikan, jadi tidak ada baris ujinya.",
            "Jumlah set dunia nyata mengikuti data/realworld/urls.csv, bukan angka di docs/command.md.",
        ],
    }


def print_summary(data: dict) -> None:
    print(f"Dataset: {data['dataset']['n_phish']} phishing + {data['dataset']['n_legit']} legit")
    print(f"Feed   : {data['feed']['status']} ({data['feed']['path']}), guard ok={data['guard']['ok']}")
    print()
    print(f"{'lapisan':<18}{'phish':>10}{'legit':>10}{'rata2 ms':>12}")
    for block in data["isolation"]:
        phish = f"{block['phish']['flagged']}/{block['phish']['n']}"
        legit = f"{block['legit']['flagged']}/{block['legit']['n']}"
        print(f"{block['layer']:<18}{phish:>10}{legit:>10}{block['mean_ms']:>12}")
    print()
    print(f"{'tingkatan':<26}{'recall':>9}{'fp_rate':>9}{'SUSP phish':>12}{'SUSP legit':>12}")
    for block in data["cumulative"]:
        m = block["metrics"]
        recall = "-" if m["recall"] is None else f"{m['recall']:.4f}"
        fp_rate = "-" if m["fp_rate"] is None else f"{m['fp_rate']:.4f}"
        print(f"{block['stage']:<26}{recall:>9}{fp_rate:>9}{block['suspicious']['phish']:>12}{block['suspicious']['legit']:>12}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluasi isolasi & kumulatif lapisan L0-L4.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-age-hours", type=int, default=168, help="batas umur feed untuk evaluasi (default 168)")
    args = parser.parse_args(argv)

    if not args.csv.exists():
        print(f"Set dunia nyata tidak ada: {args.csv}")
        return 1

    data = run(args.csv, args.max_age_hours)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_summary(data)
    print(f"\nJSON: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
