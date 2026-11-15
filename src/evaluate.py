"""Evaluasi Model A & B pada test set + contoh FP/FN nyata -> docs/hasil_evaluasi.md."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # agar `import src.*` jalan sebagai skrip

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from src.config import (
    DATA_PARQUET,
    DOCS_DIR,
    EXPECTED_N_TEST,
    EXPECTED_N_TRAIN,
    FULL_FEATURES,
    LABEL_LEGIT,
    LABEL_PHISH,
    METRICS_PATH,
    MODEL_A_PATH,
    MODEL_B_PATH,
    STATS_PATH,
    THRESHOLD,
    TLD_PROBS_PATH,
    URL_FEATURES,
    make_split,
)
from src.feature_utils import to_frame

RESULT_PATH = DOCS_DIR / "hasil_evaluasi.md"
MAX_ROWS_PER_TABLE = 10
MIN_EXAMPLES = 5


def load_artifact(path: Path):
    if not path.exists():
        raise SystemExit(f"Artefak belum ada: {path}. Jalankan `uv run python src/train.py` dulu.")
    return joblib.load(path)


def phishing_proba(pipe, features: np.ndarray) -> np.ndarray:
    """P(phishing) = predict_proba[:, 0] (label 0 = phishing)."""
    return pipe.predict_proba(features)[:, 0]


def score(y_true: np.ndarray, proba: np.ndarray) -> dict:
    pred = np.where(proba >= THRESHOLD, LABEL_PHISH, LABEL_LEGIT)
    matrix = confusion_matrix(y_true, pred, labels=[LABEL_PHISH, LABEL_LEGIT])
    tp, fn = int(matrix[0][0]), int(matrix[0][1])  # aktual phishing: terdeteksi / terlewat
    fp, tn = int(matrix[1][0]), int(matrix[1][1])  # aktual legit: dituduh phishing / benar
    return {
        "pred": pred,
        "matrix": matrix,
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, pos_label=LABEL_PHISH, zero_division=0),
        "recall": recall_score(y_true, pred, pos_label=LABEL_PHISH, zero_division=0),
        "f1": f1_score(y_true, pred, pos_label=LABEL_PHISH, zero_division=0),
    }


def top_deviations(row: dict, means: dict[str, float], k: int = 3) -> str:
    """Fitur yang paling menyimpang dari rata-rata kelas aslinya, untuk menjelaskan contoh.

    Penyebut +1.0 mencegah fitur dengan rata-rata mendekati 0 mendominasi secara semu.
    """
    dev = {f: abs(v - means[f]) / (abs(means[f]) + 1.0) for f, v in row.items()}
    top = sorted(dev.items(), key=lambda kv: kv[1], reverse=True)[:k]
    return "<br>".join(f"{f}={row[f]:.3g} (rata2 kelas={means[f]:.3g})" for f, _ in top)


def examples(
    urls: pd.Series,
    y_true: np.ndarray,
    proba: np.ndarray,
    pred: np.ndarray,
    kind: str,
    means: dict[str, float],
    tld: dict,
) -> tuple[pd.DataFrame, int, int]:
    """Ambil contoh FP (legit dituduh phishing) atau FN (phishing lolos), unik per URL."""
    mask = (y_true == LABEL_LEGIT) & (pred == LABEL_PHISH) if kind == "fp" else (y_true == LABEL_PHISH) & (
        pred == LABEL_LEGIT
    )
    frame = pd.DataFrame({"URL": urls.to_numpy(), "y_true": y_true, "proba": proba})[mask]
    total = len(frame)
    unique = int(frame["URL"].nunique())
    # FP: paling yakin salah (P tinggi); FN: paling yakin lolos (P rendah)
    frame = frame.sort_values("proba", ascending=(kind == "fn")).drop_duplicates("URL")
    frame = frame.head(MAX_ROWS_PER_TABLE).copy()
    frame["deviasi"] = [
        top_deviations(to_frame(url, tld["map"], tld["default"]).iloc[0].to_dict(), means)
        for url in frame["URL"]
    ]
    return frame, total, unique


def md_confusion(label: str, s: dict) -> str:
    return (
        f"### Confusion matrix — {label}\n\n"
        "| aktual \\ prediksi | phishing (0) | legit (1) |\n|---|---|---|\n"
        f"| **phishing (0)** | TP={s['tp']} | FN={s['fn']} |\n"
        f"| **legit (1)** | FP={s['fp']} | TN={s['tn']} |\n\n"
        f"TP={s['tp']}, FN={s['fn']}, FP={s['fp']}, TN={s['tn']} "
        f"(threshold={THRESHOLD}, P(phishing) = predict_proba[:, 0])\n"
    )


def md_examples(title: str, frame: pd.DataFrame, total: int, unique: int, kind: str) -> str:
    if frame.empty:
        return f"## {title}\n\nTidak ada {kind.upper()} pada test set.\n"
    rows = "\n".join(
        f"| `{r.URL}` | {r.proba:.4f} | {'legit' if kind == 'fp' else 'phishing'} | {r.deviasi} |"
        for r in frame.itertuples()
    )
    return (
        f"## {title}\n\n"
        f"Total **{total}** baris ({unique} URL unik); {len(frame)} contoh teratas ditampilkan.\n\n"
        "| URL | P(phishing) | label benar | top-3 fitur menyimpang (vs rata-rata kelas) |\n|---|---|---|---|\n"
        f"{rows}\n"
    )


def evaluate_url_list(urls: list[str]) -> list[dict]:
    """Prediksi Model B untuk daftar URL mentah (tanpa dataset); dipakai T11."""
    pipe = load_artifact(MODEL_B_PATH)
    tld = json.loads(TLD_PROBS_PATH.read_text(encoding="utf-8"))
    frame = to_frame(urls, tld["map"], tld["default"])
    proba = phishing_proba(pipe, frame.to_numpy(dtype=np.float32))
    return [
        {
            "url": url,
            "label": int(LABEL_PHISH if p >= THRESHOLD else LABEL_LEGIT),
            "label_name": "PHISHING" if p >= THRESHOLD else "LEGITIMATE",
            "probability": round(float(p), 4),
        }
        for url, p in zip(urls, proba)
    ]


def main() -> int:
    pipe_a = load_artifact(MODEL_A_PATH)
    pipe_b = load_artifact(MODEL_B_PATH)
    tld = json.loads(TLD_PROBS_PATH.read_text(encoding="utf-8"))
    stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    df = pd.read_parquet(DATA_PARQUET)
    train_idx, test_idx = make_split(df)
    if (len(train_idx), len(test_idx)) != (EXPECTED_N_TRAIN, EXPECTED_N_TEST):
        raise SystemExit(f"Split tak terduga: {len(train_idx)}/{len(test_idx)}")

    test = df.iloc[test_idx]
    y_true = test["label"].to_numpy(dtype=np.int8)
    urls = test["URL"].astype(str)

    X_a = test[FULL_FEATURES].astype(np.float32).to_numpy()
    X_b = to_frame(urls, tld["map"], tld["default"]).to_numpy(dtype=np.float32)

    proba_a = phishing_proba(pipe_a, X_a)
    proba_b = phishing_proba(pipe_b, X_b)
    results = {"model_a": score(y_true, proba_a), "model_b": score(y_true, proba_b)}
    print(f"Test set: {len(test)} baris (train {len(train_idx)})")
    for key, s in results.items():
        print(f"{key}: F1(phishing)={s['f1']:.4f} recall={s['recall']:.4f} FP={s['fp']} FN={s['fn']}")

    fp_frame, fp_total, fp_unique = examples(
        urls, y_true, proba_b, results["model_b"]["pred"], "fp", stats["model_b"]["class_means"]["legit"], tld
    )
    fn_frame, fn_total, fn_unique = examples(
        urls, y_true, proba_b, results["model_b"]["pred"], "fn", stats["model_b"]["class_means"]["phishing"], tld
    )
    for label, total in (("FP", fp_total), ("FN", fn_total)):
        if total < MIN_EXAMPLES:
            print(f"PERINGATAN: hanya {total} contoh {label} (< {MIN_EXAMPLES}) — laporan kurang dari target")

    ordered = [("b", "Model B (URL-only)"), ("a", "Model A (full)")]
    top_b = sorted(
        zip(stats["model_b"]["importances"], stats["model_b"]["features"]), reverse=True
    )[:3]
    top_a = sorted(zip(stats["model_a"]["importances"], stats["model_a"]["features"]), reverse=True)[:3]

    table = "\n".join(
        f"| {'A' if k == 'a' else 'B'} | {len(FULL_FEATURES if k == 'a' else URL_FEATURES)} | "
        f"{results['model_' + k]['accuracy']:.4f} | {results['model_' + k]['precision']:.4f} | "
        f"{results['model_' + k]['recall']:.4f} | {results['model_' + k]['f1']:.4f} | "
        f"{results['model_' + k]['fp']} | {results['model_' + k]['fn']} |"
        for k, _ in ordered
    )

    md = f"""# Hasil Evaluasi PhishGuard

- Tanggal evaluasi: {datetime.now(timezone.utc).isoformat(timespec="seconds")}
- Model A terbaik: `{metrics['model_a']['best']}` ({metrics['model_a']['n_features']} fitur) ·
  Model B terbaik: `{metrics['model_b']['best']}` ({metrics['model_b']['n_features']} fitur)
- Angka training/CV bersumber dari `docs/metrics.json` (`trained_at` = {metrics['trained_at']})
- Test set: {len(test)} baris, stratified 80/20 (seed {metrics['split']['seed']},
  train {len(train_idx)}). Test set tidak dipakai saat training.
- Definisi: **FP** = aktual legit (1) diprediksi phishing (0); **FN** = aktual phishing (0) diprediksi legit (1).
  Semua metrik phishing memakai `pos_label=0`.

## Tabel metrik (test set)

| Model | fitur | accuracy | precision (phishing) | recall (phishing) | F1 (phishing) | FP | FN |
|---|---|---|---|---|---|---|---|
{table}

{md_confusion("Model B (URL-only, produksi)", results["model_b"])}
{md_confusion("Model A (full, laporan)", results["model_a"])}
{md_examples("Contoh False Positive — Model B", fp_frame, fp_total, fp_unique, "fp")}
{md_examples("Contoh False Negative — Model B", fn_frame, fn_total, fn_unique, "fn")}
## Keterbatasan yang teramati (draf analisis, finalisasi oleh owner)

- Fitur paling berpengaruh Model B: {", ".join(f"`{n}` ({v:.3f})" for v, n in top_b)}.
  Dominasi `IsHTTPS` berarti model banyak belajar "phishing cenderung tanpa HTTPS" — pola era dataset,
  sementara phishing 2026 umumnya memakai HTTPS.
- Model A: {", ".join(f"`{n}` ({v:.3f})" for v, n in top_a)} — fitur konten halaman inilah yang membuat
  angkanya ~1.00 dan tidak tersedia saat inference live (leakage yang didokumentasikan, bukan disembunyikan).
- False positive Model B: {fp_total} baris ({fp_unique} URL unik) — pola yang terlihat: URL legit pendek,
  HTTPS, tanpa digit/simbol, sering berupa domain bank/populer dengan path `/login`.
- False negative Model B: {fn_total} baris ({fn_unique} URL unik) — pola: URL phishing pendek dan "bersih"
  (`https://…`, tanpa query, sedikit simbol), mirip URL legit di dataset.
- Kesimpulan draf: performa test tinggi karena distribusi dataset; risiko utama di data live adalah
  ketergantungan pada HTTPS dan keterbatasan fitur leksikal murni (lihat T11 untuk uji URL live).
"""

    RESULT_PATH.write_text(md, encoding="utf-8")
    print(f"\nDitulis: {RESULT_PATH}")
    print(f"FP Model B: {fp_total} baris ({fp_unique} URL unik), FN: {fn_total} ({fn_unique} unik)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
