"""Diagnosis set uji dunia nyata: AUC, sapuan ambang, kontribusi fitur FP, dan varian URL.

Skrip ini hanya membaca artefak yang sudah ada (model, CSV lokal) dan menambah
bagian `diagnosis` pada `docs/realworld.json` serta menulis
`docs/diagnosis_realworld.md`. Tidak ada URL feed yang ditulis ke keluaran publik.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlunsplit, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

from scripts.eval_realworld import is_valid_url, load_rows, metrics, score_model_only
from src.config import LABEL_LEGIT, LABEL_PHISH, THRESHOLD, URL_FEATURES
from src.feature_utils import to_frame
from src.predict import _load
from src.reputation import is_trusted

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "realworld" / "urls.csv"
DEFAULT_JSON = ROOT / "docs" / "realworld.json"
DEFAULT_DOC = ROOT / "docs" / "diagnosis_realworld.md"
THRESHOLDS = [round(0.10 + i * 0.01, 2) for i in range(90)]
QUANTILES = [0.0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0]
_TOP_FEATURES = 10


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _port(url: str) -> int | None:
    try:
        return urlsplit(url).port
    except ValueError:
        return None


def without_path_query(url: str) -> str:
    """Skema + host (+ port), tanpa path/query/fragment."""
    parts = urlsplit(url)
    netloc = parts.hostname or ""
    port = _port(url)
    if port:
        netloc = f"{netloc}:{port}"
    return f"{parts.scheme.lower()}://{netloc}"


def with_www(url: str) -> str:
    """Tambahkan awalan www. bila belum ada; path/query dipertahankan."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host.startswith("www."):
        return url
    netloc = f"www.{host}"
    port = _port(url)
    if port:
        netloc = f"{netloc}:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def score_distribution(scores: list[float]) -> dict[str, object]:
    """Ringkasan distribusi skor, termasuk kuantil dan persentase diprediksi phishing."""
    values = np.asarray(scores, dtype=float)
    if values.size == 0:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None, "quantiles": {}}
    return {
        "n": int(values.size),
        "mean": round(float(values.mean()), 4),
        "median": round(float(np.median(values)), 4),
        "min": round(float(values.min()), 4),
        "max": round(float(values.max()), 4),
        "predicted_phishing_pct": round(float((values >= THRESHOLD).mean() * 100), 2),
        "quantiles": {f"{q:.2f}": round(float(np.quantile(values, q)), 4) for q in QUANTILES},
    }


def auc_block(y_phishing: list[int], scores: list[float]) -> dict[str, float | None]:
    if len(set(y_phishing)) < 2:
        return {"roc_auc": None, "pr_auc": None}
    return {
        "roc_auc": round(float(roc_auc_score(y_phishing, scores)), 4),
        "pr_auc": round(float(average_precision_score(y_phishing, scores)), 4),
    }


def threshold_sweep(y_true: list[int], scores: list[float]) -> list[dict[str, object]]:
    """Recall, specificity, dan MCC untuk setiap ambang 0.10-0.99."""
    rows = []
    for threshold in THRESHOLDS:
        y_pred = [LABEL_PHISH if score >= threshold else LABEL_LEGIT for score in scores]
        values = metrics(y_true, y_pred)
        rows.append(
            {
                "threshold": threshold,
                "recall": values["recall"],
                "specificity": values["specificity"],
                "mcc": values["mcc"],
                "fp": values["fp"],
                "fn": values["fn"],
                "predicted_phishing_pct": values["predicted_phishing_pct"],
            }
        )
    return rows


def contribution_matrix(urls: list[str]) -> np.ndarray:
    """Kontribusi fitur ke arah phishing (positif = mendorong phishing)."""
    if not urls:
        return np.empty((0, len(URL_FEATURES)), dtype=float)
    pipe, tld, _ = _load()
    frame = to_frame(urls, tld["map"], tld["default"])
    imputed = pipe.named_steps["imputer"].transform(frame.to_numpy(dtype=np.float32))
    model = pipe.named_steps["model"]
    if not hasattr(model, "get_booster"):
        raise RuntimeError("Kontribusi fitur hanya tersedia bila Model B memakai XGBoost.")
    booster = model.get_booster()
    matrix = xgb.DMatrix(imputed)
    contributions = np.asarray(booster.predict(matrix, pred_contribs=True), dtype=float)
    margin = np.asarray(booster.predict(matrix, output_margin=True), dtype=float)
    if not np.allclose(contributions.sum(axis=1), margin, atol=1e-4):
        raise RuntimeError("pred_contribs tidak konsisten dengan margin model")
    # pred_contribs binary XGBoost = kontribusi ke kelas 1 (legit); balik agar positif = phishing.
    return -contributions[:, :-1]


def aggregate_contributions(toward_phishing: np.ndarray) -> list[dict[str, object]]:
    if toward_phishing.size == 0:
        return []
    mean_abs = np.mean(np.abs(toward_phishing), axis=0)
    mean_signed = np.mean(toward_phishing, axis=0)
    order = np.argsort(mean_abs)[::-1][:_TOP_FEATURES]
    return [
        {
            "feature": URL_FEATURES[index],
            "mean_abs_contribution": round(float(mean_abs[index]), 4),
            "mean_contribution_toward_phishing": round(float(mean_signed[index]), 4),
        }
        for index in order
    ]


def legit_variant_experiment(urls: list[str]) -> dict[str, object]:
    """Skor ulang URL legitimate: asli, tanpa path/query, dan dengan awalan www."""
    if not urls:
        return {"n": 0, "variants": {}, "delta_vs_original": {}}
    variants = {
        "original": urls,
        "no_path_query": [without_path_query(url) for url in urls],
        "www_prefix": [with_www(url) for url in urls],
    }
    scores = {name: np.asarray(score_model_only(values), dtype=float) for name, values in variants.items()}
    original = scores["original"]
    payload: dict[str, object] = {
        "n": len(urls),
        "variants": {name: score_distribution(values.tolist()) for name, values in scores.items()},
        "delta_vs_original": {},
    }
    for name, values in scores.items():
        if name == "original":
            continue
        delta = values - original
        payload["delta_vs_original"][name] = {
            "mean": round(float(delta.mean()), 4),
            "median": round(float(np.median(delta)), 4),
            "increased": int((delta > 0).sum()),
            "decreased": int((delta < 0).sum()),
            "unchanged": int((delta == 0).sum()),
        }
    return payload


def build_diagnosis(
    rows: list[dict[str, str]],
    urls: list[str],
    probabilities: list[float],
    in_allowlist: list[bool],
) -> dict[str, object]:
    group = [
        index
        for index, row in enumerate(rows)
        if int(row["label"]) == LABEL_PHISH or not in_allowlist[index]
    ]
    y_true = [int(rows[index]["label"]) for index in group]
    y_phishing = [1 if label == LABEL_PHISH else 0 for label in y_true]
    scores = [probabilities[index] for index in group]

    fp_index = [
        index
        for index, row in enumerate(rows)
        if int(row["label"]) == LABEL_LEGIT
        and not in_allowlist[index]
        and probabilities[index] >= THRESHOLD
    ]
    fp_matrix = contribution_matrix([urls[index] for index in fp_index])

    legit_urls = [urls[index] for index, row in enumerate(rows) if int(row["label"]) == LABEL_LEGIT]
    phishing_scores = [score for score, label in zip(scores, y_true) if label == LABEL_PHISH]
    legit_scores = [score for score, label in zip(scores, y_true) if label == LABEL_LEGIT]

    return {
        "group": {
            "name": "not_in_allowlist + phishing",
            "n": len(group),
            "n_phishing": len(phishing_scores),
            "n_legit": len(legit_scores),
        },
        "auc": auc_block(y_phishing, scores),
        "score_distribution": {
            "phishing": score_distribution(phishing_scores),
            "legit": score_distribution(legit_scores),
        },
        "threshold_sweep": threshold_sweep(y_true, scores),
        "fp_outside_allowlist": {
            "n": len(fp_index),
            "top_features": aggregate_contributions(fp_matrix),
        },
        "legit_variants": legit_variant_experiment(legit_urls),
    }


def render_markdown(payload: dict[str, object]) -> str:
    generated = payload["generated_at"]
    params = payload["parameters"]
    group = payload["group"]
    auc = payload["auc"]
    distribution = payload["score_distribution"]
    fp = payload["fp_outside_allowlist"]
    variants = payload["legit_variants"]

    lines = [
        "# Diagnosis set uji dunia nyata (T18c)",
        "",
        f"Dihasilkan otomatis oleh `scripts/diagnose_realworld.py` pada {generated}. "
        "Semua angka diambil dari skrip; dokumen ini tidak memuat URL.",
        "",
        "## Cakupan",
        "",
        f"- Kelompok diagnosis: **{group['name']}** — {group['n']} URL "
        f"({group['n_phishing']} phishing, {group['n_legit']} legitimate di luar allowlist).",
        f"- Model: Model B; ambang label {params['threshold']}.",
        "- Kelompok ini dipakai karena domain allowlist diputuskan tanpa model.",
        "",
        "## ROC-AUC dan PR-AUC",
        "",
        "| Metrik | Nilai |",
        "|---|---|",
        f"| ROC-AUC | {auc['roc_auc']} |",
        f"| PR-AUC | {auc['pr_auc']} |",
        "",
        "AUC mengukur pemeringkatan skor, bukan kualitas vonis pada ambang tertentu.",
        "",
        "## Distribusi skor per kelas",
        "",
        "| Statistik | Phishing | Legit |",
        "|---|---|---|",
    ]
    for key in ("n", "mean", "median", "min", "max", "predicted_phishing_pct"):
        lines.append(f"| {key} | {distribution['phishing'][key]} | {distribution['legit'][key]} |")
    lines += ["", "| Kuantil | Phishing | Legit |", "|---|---|---|"]
    for quantile, value in distribution["phishing"]["quantiles"].items():
        lines.append(f"| {quantile} | {value} | {distribution['legit']['quantiles'][quantile]} |")

    lines += [
        "",
        "## Sapuan ambang",
        "",
        "> **Peringatan:** ambang di bawah dipilih/dibandingkan pada set kecil ini. "
        "Jangan menganggap ambang terbaik di sini sebagai hasil yang tervalidasi; "
        "risiko overfit tinggi. Ambang produksi harus ditentukan pada data lain.",
        "",
        "| Ambang | Recall | Specificity | MCC | FP | FN | % diprediksi phishing |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in payload["threshold_sweep"]:
        lines.append(
            f"| {row['threshold']:.2f} | {_fmt(row['recall'])} | {_fmt(row['specificity'])} | "
            f"{_fmt(row['mcc'])} | {row['fp']} | {row['fn']} | {row['predicted_phishing_pct']} |"
        )

    lines += [
        "",
        "## Kontribusi fitur pada FP di luar allowlist",
        "",
        f"Jumlah FP model-only di luar allowlist: **{fp['n']}**.",
        "Kontribusi dihitung dengan `pred_contribs` XGBoost, lalu dirata-rata. "
        "Nilai positif berarti mendorong vonis phishing. URL tidak ditampilkan.",
        "",
        "| Fitur | Rata-rata \\|kontribusi\\| | Rata-rata kontribusi ke phishing |",
        "|---|---|---|",
    ]
    for feature in fp["top_features"]:
        lines.append(
            f"| `{feature['feature']}` | {feature['mean_abs_contribution']} | "
            f"{feature['mean_contribution_toward_phishing']} |"
        )
    if not fp["top_features"]:
        lines.append("| — | — | — |")

    lines += [
        "",
        "## Eksperimen varian URL legitimate",
        "",
        f"Jumlah URL legitimate: **{variants['n']}**. Skor adalah P(phishing) dari Model B.",
        "",
        "| Varian | Mean | Median | Min | Max | % diprediksi phishing | Delta mean vs asli | Delta median | Naik | Turun |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, values in variants["variants"].items():
        delta = variants["delta_vs_original"].get(name, {})
        lines.append(
            f"| {name} | {values['mean']} | {values['median']} | {values['min']} | {values['max']} | "
            f"{values.get('predicted_phishing_pct')} | {_fmt(delta.get('mean'))} | {_fmt(delta.get('median'))} | "
            f"{delta.get('increased', '—')} | {delta.get('decreased', '—')} |"
        )

    lines += [
        "",
        "## Keterbatasan",
        "",
        "- Set kecil dan satu snapshot; sapuan ambang rawan overfit.",
        "- Kontribusi fitur menjelaskan model, bukan sebab phishing di dunia nyata.",
        "- Label legitimate masih kurasi manual dan belum diverifikasi per URL.",
        "- Varian `no_path_query` dan `www_prefix` mengubah URL, sehingga bukan lagi URL asli.",
        "- Dokumen ini sengaja tidak memuat URL feed; daftar error lokal ada di `data/realworld/errors.csv`.",
        "",
        "## Cara menjalankan",
        "",
        "```powershell",
        "uv run python scripts/build_realworld_set.py",
        "uv run python scripts/eval_realworld.py",
        "uv run python scripts/diagnose_realworld.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def write_outputs(payload: dict[str, object], json_path: Path, doc_path: Path) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["diagnosis"] = payload
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    doc_path.write_text(render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnosis set uji dunia nyata")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="CSV dari build_realworld_set.py")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="JSON hasil eval_realworld.py")
    parser.add_argument("--doc", default=str(DEFAULT_DOC), help="dokumen diagnosis keluaran")
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    json_path = Path(args.json)
    if not csv_path.exists():
        print(f"File tidak ditemukan: {csv_path}")
        print("Jalankan `uv run python scripts/build_realworld_set.py` dulu.")
        return 2
    if not json_path.exists():
        print(f"File tidak ditemukan: {json_path}")
        print("Jalankan `uv run python scripts/eval_realworld.py` dulu.")
        return 2

    rows = [row for row in load_rows(csv_path) if is_valid_url((row.get("url") or "").strip())]
    if not rows:
        print("Tidak ada URL valid; tidak ada yang didiagnosis.")
        return 2
    urls = [row["url"].strip() for row in rows]

    try:
        probabilities = score_model_only(urls)
        payload = build_diagnosis(
            rows,
            urls,
            probabilities,
            [is_trusted(_host(url)) for url in urls],
        )
    except RuntimeError as exc:
        print(f"Artefak model belum siap: {exc}")
        return 1

    payload["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload["parameters"] = {"threshold": THRESHOLD, "thresholds": [THRESHOLDS[0], THRESHOLDS[-1]]}
    write_outputs(payload, json_path, Path(args.doc))
    print(f"Ditulis: {json_path} (bagian diagnosis)")
    print(f"Ditulis: {args.doc}")
    print(
        f"Grup {payload['group']['n']} URL; ROC-AUC={payload['auc']['roc_auc']} "
        f"PR-AUC={payload['auc']['pr_auc']}; FP di luar allowlist={payload['fp_outside_allowlist']['n']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
