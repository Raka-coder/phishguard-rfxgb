"""Kesetaraan fitur Model B: bandingkan ekstraktor repo dengan kolom dataset PhiUSIIL.

Sampel diambil hanya dari split **train** (`config.make_split`, seed tetap) supaya
test tetap tersegel. Angka yang dilaporkan: persentase cocok persis, selisih
absolut rata-rata/maksimum, dan korelasi Pearson per fitur, dipisah per label.
Semua dihitung di sini; tidak ada angka manual.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.config import (
    DATA_PARQUET,
    LABEL_LEGIT,
    LABEL_PHISH,
    TLD_PROBS_PATH,
    URL_FEATURES,
    make_split,
)
from src.feature_utils import extract_features

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REALWORLD_CSV = ROOT / "data" / "realworld" / "urls.csv"
DEFAULT_SAMPLE = 5000
DEFAULT_SEED = 42
_WORST = 5


def _is_plain_homepage(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.path in ("", "/") and not parts.query and not parts.fragment


def _tld_of(url: str) -> str:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""
    return host.rsplit(".", 1)[-1] if "." in host else ""


def _feature_stats(dataset: pd.DataFrame, computed: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Persentase cocok persis, MAE, maks |selisih|, dan korelasi per fitur."""
    stats: dict[str, dict[str, object]] = {}
    for feature in URL_FEATURES:
        actual = dataset[feature].to_numpy(dtype=float)
        expected = computed[feature].to_numpy(dtype=float)
        diff = np.abs(actual - expected)
        correlation = None
        if actual.size > 1 and actual.std() > 0 and expected.std() > 0:
            correlation = round(float(np.corrcoef(actual, expected)[0, 1]), 4)
        stats[feature] = {
            "exact_match_pct": round(float(np.mean(actual == expected) * 100), 2),
            "mean_abs_diff": round(float(diff.mean()), 6),
            "max_abs_diff": round(float(diff.max()), 6),
            "correlation": correlation,
        }
    return stats


def _worst(stats: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(stats.items(), key=lambda item: item[1]["mean_abs_diff"], reverse=True)
    return [{"feature": feature, **values} for feature, values in ordered[:_WORST]]


def parity_report(
    df: pd.DataFrame,
    indices: np.ndarray,
    tld_probs: dict[str, float],
    tld_default: float,
    *,
    seed: int,
    sample_size: int,
) -> dict[str, object]:
    """Parity 19 fitur pada baris `indices` (harus dari split train)."""
    subset = df.iloc[indices]
    urls = subset["URL"].astype(str).str.strip()
    computed = pd.DataFrame(
        [extract_features(url, tld_probs, tld_default) for url in urls],
        columns=URL_FEATURES,
    )
    dataset = subset[URL_FEATURES].astype(float).reset_index(drop=True)
    labels = subset["label"].to_numpy()

    by_label = {
        "legit": _feature_stats(dataset[labels == LABEL_LEGIT], computed[labels == LABEL_LEGIT]),
        "phishing": _feature_stats(dataset[labels == LABEL_PHISH], computed[labels == LABEL_PHISH]),
    }
    known_tlds = np.array([_tld_of(url) in tld_probs for url in urls])
    return {
        "sample": {
            "source": "split train dari config.make_split (test tidak disentuh)",
            "seed": seed,
            "requested_size": sample_size,
            "size": int(len(subset)),
            "n_legit": int(np.sum(labels == LABEL_LEGIT)),
            "n_phishing": int(np.sum(labels == LABEL_PHISH)),
        },
        "tld_probability": {
            "source": "src/tld_probs.json",
            "formula": "(jumlah legit per TLD + 1) / (jumlah total per TLD + 2)",
            "default_formula": "(jumlah legit train + 1) / (jumlah baris train + 2)",
            "n_tlds": int(len(tld_probs)),
            "default": tld_default,
            "sample_default_fallback_pct": round(float((~known_tlds).mean() * 100), 2),
        },
        "by_label": {
            name: {"n": int(np.sum(labels == (LABEL_LEGIT if name == "legit" else LABEL_PHISH))), "features": values}
            for name, values in by_label.items()
        },
        "worst_features": {name: _worst(values) for name, values in by_label.items()},
        "computed_feature_names": list(URL_FEATURES),
    }


def homepage_reference(
    df: pd.DataFrame,
    train_indices: np.ndarray,
    tld_probs: dict[str, float],
    tld_default: float,
) -> dict[str, object]:
    """Median 19 fitur untuk baris legitimate bertipe homepage polos di data latih."""
    subset = df.iloc[train_indices]
    mask = (subset["label"].to_numpy() == LABEL_LEGIT) & subset["URL"].astype(str).map(_is_plain_homepage)
    urls = subset.loc[mask, "URL"].astype(str).str.strip()
    computed = pd.DataFrame(
        [extract_features(url, tld_probs, tld_default) for url in urls],
        columns=URL_FEATURES,
    )
    if computed.empty:
        return {"n_train_legit_homepages": 0, "median": {}}
    return {
        "n_train_legit_homepages": int(len(computed)),
        "median": {feature: round(float(computed[feature].median()), 6) for feature in URL_FEATURES},
    }


def homepage_comparison(
    homepage_urls: list[str],
    reference: dict[str, object],
    tld_probs: dict[str, float],
    tld_default: float,
) -> dict[str, object]:
    """Median fitur 3 homepage T18 (anonim) vs median homepage legit di data latih."""
    if not homepage_urls or not reference.get("n_train_legit_homepages"):
        return {"available": False, "reason": "butuh URL homepage dan baris homepage legit di train"}
    computed = pd.DataFrame(
        [extract_features(url, tld_probs, tld_default) for url in homepage_urls],
        columns=URL_FEATURES,
    )
    train_median = reference["median"]
    rows = [
        {
            "feature": feature,
            "t18_median": round(float(computed[feature].median()), 6),
            "t18_min": round(float(computed[feature].min()), 6),
            "t18_max": round(float(computed[feature].max()), 6),
            "train_median": train_median[feature],
            "delta": round(float(computed[feature].median()) - float(train_median[feature]), 6),
        }
        for feature in URL_FEATURES
    ]
    return {
        "available": True,
        "n_urls": len(homepage_urls),
        "n_train_legit_homepages": reference["n_train_legit_homepages"],
        "rows": rows,
    }


def homepages_from_csv(csv_path: Path, limit: int = 3) -> list[str]:
    """Tiga URL legitimate pertama bertipe homepage polos dari set T18 (lokal)."""
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    urls = []
    for row in rows:
        url = (row.get("url") or "").strip()
        if (row.get("label") or "").strip() == str(LABEL_LEGIT) and _is_plain_homepage(url):
            urls.append(url)
        if len(urls) == limit:
            break
    return urls


def _load_tld_probs(path: Path = TLD_PROBS_PATH) -> tuple[dict[str, float], float]:
    if not path.exists():
        raise FileNotFoundError(f"{path} tidak ada; jalankan `uv run python src/train.py` dulu.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["map"], float(data["default"])


def training_diagnostics(
    homepage_urls: list[str] | None = None,
    *,
    sample_size: int = DEFAULT_SAMPLE,
    seed: int = DEFAULT_SEED,
    parquet_path: Path = DATA_PARQUET,
    tld_path: Path = TLD_PROBS_PATH,
) -> dict[str, object]:
    """Parity fitur + referensi homepage dari split train; dipakai skrip diagnosis."""
    df = pd.read_parquet(parquet_path)
    train_indices, _ = make_split(df)
    urls = df["URL"].astype(str).str.strip()
    candidates = train_indices[urls.iloc[train_indices].to_numpy() != ""]
    size = min(sample_size, len(candidates))
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(candidates, size=size, replace=False))
    tld_probs, tld_default = _load_tld_probs(tld_path)

    report = parity_report(df, indices, tld_probs, tld_default, seed=seed, sample_size=sample_size)
    report["available"] = True
    reference = homepage_reference(df, train_indices, tld_probs, tld_default)
    if homepage_urls is None:
        homepage_urls = homepages_from_csv(DEFAULT_REALWORLD_CSV)
    report["homepage_comparison"] = homepage_comparison(homepage_urls, reference, tld_probs, tld_default)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parity fitur Model B terhadap kolom dataset PhiUSIIL")
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE, help="jumlah baris train yang diuji")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="seed sampling")
    parser.add_argument("--json", default="", help="opsional: tulis hasil lengkap ke path JSON")
    parser.add_argument("--realworld-csv", default=str(DEFAULT_REALWORLD_CSV), help="CSV set T18 untuk homepage")
    args = parser.parse_args(argv)

    homepage_urls = homepages_from_csv(Path(args.realworld_csv))
    try:
        report = training_diagnostics(homepage_urls, sample_size=args.sample, seed=args.seed)
    except FileNotFoundError as exc:
        print(exc)
        return 2

    print(f"Sampel train: {report['sample']['size']} baris "
          f"(legit {report['sample']['n_legit']}, phishing {report['sample']['n_phishing']})")
    tld = report["tld_probability"]
    print(f"TLDLegitimateProb: {tld['n_tlds']} TLD dari {tld['source']}, default={tld['default']}, "
          f"fallback={tld['sample_default_fallback_pct']}%")
    for label in ("legit", "phishing"):
        block = report["by_label"][label]
        exact = np.mean([values["exact_match_pct"] for values in block["features"].values()])
        print(f"  {label:8s} n={block['n']:5d} rata-rata cocok persis={exact:.2f}%")
        for item in report["worst_features"][label]:
            print(f"    {item['feature']:28s} cocok={item['exact_match_pct']:6.2f}% "
                  f"MAE={item['mean_abs_diff']:.4f} maks={item['max_abs_diff']:.4f} "
                  f"r={item['correlation']}")
    homepage = report["homepage_comparison"]
    if homepage.get("available"):
        print(f"Homepage: {homepage['n_urls']} URL T18 vs {homepage['n_train_legit_homepages']} homepage legit train")
    else:
        print(f"Homepage: tidak tersedia ({homepage.get('reason', '—')})")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Ditulis: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
