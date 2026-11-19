"""Kategorisasi 122 False Negative Model B pada test set (T31.2).

Daftar URL FN tidak disimpan utuh (dataset CC BY-NC-SA). Skrip mereproduksi FN secara
deterministik dari split dan artefak model, mencocokkan jumlahnya dengan
`docs/hasil_evaluasi.md`, lalu menulis kategori + 5 contoh per kategori ke
`results/data/fn_categories.json`.

Taksonomi final hanya memakai kategori yang terukur dari string URL: pendek_bersih,
shortener, typosquatting, dan lainnya. Kategori berbasis umur domain (domain_tua)
tidak dimasukkan karena tidak ada data WHOIS/RDAP di pipeline; hal itu dicatat
sebagai batas pengukuran, bukan diisi perkiraan.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import pandas as pd

from src.config import (
    DATA_PARQUET,
    EXPECTED_N_TEST,
    LABEL_PHISH,
    METRICS_PATH,
    MODEL_B_PATH,
    TLD_PROBS_PATH,
    make_split,
)
from src.evaluate import phishing_proba, score
from src.feature_utils import to_frame
from src.reputation import is_shortener

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "data" / "fn_categories.json"
HASIL_PATH = ROOT / "docs" / "hasil_evaluasi.md"
_CONF_RE = re.compile(r"TP=(\d+),\s*FN=(\d+),\s*FP=(\d+),\s*TN=(\d+)")
MAX_EXAMPLES = 5

# Merek yang dipakai untuk pencocokan string sederhana; bukan detektor peniruan merek.
ID_BRANDS = {
    "tokopedia", "gojek", "goto", "traveloka", "blibli", "shopee", "lazada",
    "bukalapak", "dana", "ovo", "grab", "bca", "bri", "mandiri", "bni", "btn",
    "bsi", "cimb", "permata", "pertamina", "pln", "telkomsel", "indosat", "jne", "pos",
}


def levenshtein(a: str, b: str) -> int:
    """Jarak edit dua string (implementasi DP sederhana)."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (char_a != char_b),
                )
            )
        previous = current
    return previous[-1]


def load_brands() -> set[str]:
    """Label merek dari allowlist + merek lokal; hanya yang panjangnya >=4."""
    trusted = json.loads((ROOT / "src" / "trusted_domains.json").read_text(encoding="utf-8"))["domains"]
    brands = {domain.split(".")[0] for domain in trusted}
    brands |= ID_BRANDS
    return {brand for brand in brands if len(brand) >= 4}


def typosquat_brand(url: str, brands: set[str]) -> str | None:
    """Kembalikan merek yang ditiru, atau None. Aturan string, bukan model."""
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    label = host.split(".")[0]
    for brand in brands:
        if brand in host and label != brand:
            return brand
        limit = 1 if len(brand) <= 5 else 2
        if levenshtein(label, brand) <= limit:
            return brand
    return None


def categorize(url: str, brands: set[str]) -> tuple[str, str | None]:
    """Prioritas: shortener -> typosquatting -> pendek_bersih -> lainnya."""
    host = (urlsplit(url).hostname or "").lower()
    if is_shortener(host):
        return "shortener", None
    brand = typosquat_brand(url, brands)
    if brand:
        return "typosquatting", brand
    if len(url) <= 30 and url.isascii() and not any(char in url for char in "?@%"):
        return "pendek_bersih", None
    return "lainnya", None


def expected_counts() -> tuple[int, int]:
    """Baca TP/FN/FP/TN Model B pertama dari docs/hasil_evaluasi.md."""
    match = _CONF_RE.search(HASIL_PATH.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"Format confusion matrix tidak ditemukan di {HASIL_PATH}")
    _, fn, fp, _ = (int(value) for value in match.groups())
    return fn, fp


def collect_fn() -> tuple[pd.DataFrame, dict, dict]:
    """Reproduksi FN Model B; kembalikan frame FN, ringkasan skor, dan metadata split."""
    df = pd.read_parquet(DATA_PARQUET)
    _, test_idx = make_split(df)
    test = df.iloc[test_idx].reset_index(drop=True)
    if len(test) != EXPECTED_N_TEST:
        raise SystemExit(f"Ukuran test tak terduga: {len(test)}")

    pipe = joblib.load(MODEL_B_PATH)
    tld = json.loads(TLD_PROBS_PATH.read_text(encoding="utf-8"))
    features = to_frame(test["URL"].astype(str), tld["map"], tld["default"]).to_numpy(dtype="float32")
    proba = phishing_proba(pipe, features)
    metrics = score(test["label"].to_numpy(), proba)

    fn = test[(test["label"].to_numpy() == LABEL_PHISH) & (metrics["pred"] == 1)].copy()
    fn["probability"] = proba[fn.index]
    return fn, metrics, {"n_test": len(test), "n_train": len(df) - len(test)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kategorisasi FN Model B pada test set.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    expected_fn, expected_fp = expected_counts()
    fn, metrics, split = collect_fn()
    if metrics["fn"] != expected_fn or metrics["fp"] != expected_fp:
        raise SystemExit(
            f"FN/FP tidak cocok dengan docs/hasil_evaluasi.md: "
            f"dihitung {metrics['fn']}/{metrics['fp']}, dokumen {expected_fn}/{expected_fp}"
        )

    brands = load_brands()
    categories = {
        "shortener": {"label": "Shortener", "examples": []},
        "typosquatting": {"label": "Typosquatting/peniruan merek (string)", "examples": []},
        "pendek_bersih": {"label": "URL pendek dan bersih", "examples": []},
        "lainnya": {"label": "Lainnya", "examples": []},
    }
    counts = Counter()
    brand_hits = Counter()

    for row in fn.itertuples():
        category, brand = categorize(row.URL, brands)
        counts[category] += 1
        if brand:
            brand_hits[brand] += 1
        if len(categories[category]["examples"]) < MAX_EXAMPLES:
            categories[category]["examples"].append(
                {"url": row.URL, "probability": round(float(row.probability), 4)}
            )

    output_categories = []
    for key in ("pendek_bersih", "shortener", "typosquatting", "lainnya"):
        item = {
            "id": key,
            "label": categories[key]["label"],
            "n": counts.get(key, 0),
            "examples": categories[key]["examples"],
            "status": "OK",
        }
        output_categories.append(item)

    assigned = sum(counts.values())
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/categorize_fn.py",
        "source": {
            "metrics_path": str(METRICS_PATH.relative_to(ROOT)).replace("\\", "/"),
            "confusion_matrix": str(HASIL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "model_b_path": str(MODEL_B_PATH.relative_to(ROOT)).replace("\\", "/"),
            "data": str(DATA_PARQUET.relative_to(ROOT)).replace("\\", "/"),
            "split": split,
            "expected_fn": expected_fn,
            "expected_fp": expected_fp,
            "recomputed_fn": metrics["fn"],
            "recomputed_fp": metrics["fp"],
            "verified": True,
        },
        "rules": {
            "priority": ["shortener", "typosquatting", "pendek_bersih", "lainnya"],
            "pendek_bersih": "panjang URL <=30, ASCII, tanpa ? @ %",
            "shortener": "host ada di src/reputation.py URL_SHORTENERS",
            "typosquatting": "host memuat label merek atau jarak Levenshtein <=1 (merek 4-5 huruf) / <=2 (>=6 huruf)",
        },
        "total_fn": expected_fn,
        "assigned_total": assigned,
        "unassigned": expected_fn - assigned,
        "categories": output_categories,
        "brand_hits": dict(brand_hits),
        "notes": [
            "Daftar 122 URL FN tidak disimpan utuh karena dataset CC BY-NC-SA; hanya 5 contoh per kategori.",
            "Taksonomi final hanya memakai kategori yang terukur dari string URL. Kategori berbasis umur domain (domain_tua) tidak dimasukkan karena tidak ada data WHOIS/RDAP di pipeline; hal itu dicatat sebagai batas pengukuran, bukan diisi perkiraan.",
            "Kategori adalah heuristik string untuk laporan, bukan lapisan keputusan baru.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"FN terverifikasi: {metrics['fn']} (dokumen: {expected_fn}), FP: {metrics['fp']}")
    for item in output_categories:
        shown = "MISSING" if item["n"] is None else item["n"]
        print(f"  {item['id']:<15} {shown}")
    print(f"JSON: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
