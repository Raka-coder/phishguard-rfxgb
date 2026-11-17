"""Latih 3 varian eksperimen Model C pada split berkelompok per host (T24).

Varian: `B_refit` (19 fitur Model B), `B_noHTTPS` (tanpa IsHTTPS), `C_host` (10 fitur
host-only). Split dan CV dikelompokkan per host; `TLDLegitimateProb` untuk baris train
memakai nilai out-of-fold. Artefak ditulis ke `models/experimental/` (gitignored) dan
angka ke `docs/model_c.json`; `src/model.pkl` tidak disentuh.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold

from scripts.eval_realworld import metrics
from src.config import (
    CV_FOLDS,
    DATA_PARQUET,
    LABEL_LEGIT,
    LABEL_PHISH,
    SEED,
    TEST_SIZE,
    THRESHOLD,
    TLD_PROBS_PATH,
)
from src.feature_utils import to_frame
from src.features_host import host_of, tld_of_host, to_host_frame
from src.train import build_models

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "models" / "experimental"
JSON_PATH = ROOT / "docs" / "model_c.json"
TLD_PATH = EXPERIMENT_DIR / "tld_probs_host.json"
HYPERPARAMETER_KEYS = (
    "n_estimators",
    "learning_rate",
    "max_depth",
    "tree_method",
    "n_jobs",
    "random_state",
    "eval_metric",
)

VARIANTS = {
    "B_refit": {"source": "url", "drop": []},
    "B_noHTTPS": {"source": "url", "drop": ["IsHTTPS"]},
    "C_host": {"source": "host", "drop": []},
}


def dedupe_by_url(df: pd.DataFrame) -> pd.DataFrame:
    """Buang salinan URL identik, pertahankan kemunculan pertama."""
    return df.drop_duplicates("URL", keep="first").reset_index(drop=True)


def group_split(hosts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """80/20 per host: satu host tidak pernah muncul di kedua sisi."""
    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=SEED)
    train_pos, test_pos = next(splitter.split(np.zeros(len(hosts)), groups=hosts))
    overlap = len(set(hosts[train_pos]) & set(hosts[test_pos]))
    if overlap:
        raise RuntimeError(f"{overlap} host muncul di train dan test")
    return np.sort(train_pos), np.sort(test_pos)


def grouped_folds(
    train_pos: np.ndarray, labels: np.ndarray, hosts: np.ndarray
) -> list[tuple[np.ndarray, np.ndarray]]:
    """5-fold di train, grup host tidak terbelah antar fold."""
    splitter = StratifiedGroupKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    return list(splitter.split(np.zeros(len(train_pos)), labels[train_pos], groups=hosts[train_pos]))


def build_host_tld_probs(hosts, labels) -> tuple[dict[str, float], float]:
    """P(TLD legitimate) dari host dengan Laplace smoothing; default = rasio global."""
    frame = pd.DataFrame({"tld": [tld_of_host(h) for h in hosts], "y": np.asarray(labels)})
    agg = frame.groupby("tld")["y"].agg(["sum", "count"])
    probs = ((agg["sum"] + 1) / (agg["count"] + 2)).round(6).to_dict()
    default = round(float((np.asarray(labels).sum() + 1) / (len(labels) + 2)), 6)
    return probs, default


def tld_values(tlds: np.ndarray, table: dict[str, float], default: float) -> np.ndarray:
    """Nilai TLD prob untuk setiap TLD; TLD tak dikenal memakai default."""
    return np.array([table.get(tld, default) for tld in tlds], dtype=float)


def base_frame(urls: np.ndarray, source: str, table: dict[str, float], default: float) -> pd.DataFrame:
    return to_frame(urls, table, default) if source == "url" else to_host_frame(urls, table, default)


def matrix(
    frame: pd.DataFrame,
    positions: np.ndarray,
    tlds: np.ndarray,
    table: dict[str, float],
    default: float,
    drop: list[str],
) -> np.ndarray:
    """Potongan fitur untuk `positions`, kolom TLD diganti nilai dari `table`."""
    block = frame.iloc[positions].copy()
    block["TLDLegitimateProb"] = tld_values(tlds[positions], table, default)
    if drop:
        block = block.drop(columns=list(drop))
    return block.to_numpy(dtype=np.float32)


def phishing_proba(pipe, frame: pd.DataFrame | np.ndarray) -> np.ndarray:
    values = frame.to_numpy(dtype=np.float32) if isinstance(frame, pd.DataFrame) else frame
    proba = pipe.predict_proba(values)
    return np.asarray(proba[:, list(pipe.classes_).index(LABEL_PHISH)], dtype=float)


def score_block(y_true: np.ndarray, proba: np.ndarray) -> dict[str, object]:
    """Metrik dengan phishing sebagai positif, plus ROC-AUC."""
    predicted = np.where(proba >= THRESHOLD, LABEL_PHISH, LABEL_LEGIT).astype(int)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = round(
        float(roc_auc_score((np.asarray(y_true) == LABEL_PHISH).astype(int), proba)), 4
    )
    return block


def label_counts(labels: np.ndarray) -> dict[str, int]:
    return {
        "legit": int(np.sum(labels == LABEL_LEGIT)),
        "phishing": int(np.sum(labels == LABEL_PHISH)),
    }


def old_tld_comparison(tlds: np.ndarray, test_pos: np.ndarray) -> dict[str, object]:
    """Perbedaan tabel TLD lama (src/tld_probs.json, dari URL penuh) vs baru (host)."""
    if not TLD_PROBS_PATH.exists():
        return {"available": False, "reason": f"{TLD_PROBS_PATH.name} tidak ada"}
    data = json.loads(TLD_PROBS_PATH.read_text(encoding="utf-8"))
    mapping = data["map"]
    test_tlds = tlds[test_pos]
    covered = np.array([tld in mapping for tld in test_tlds])
    return {
        "available": True,
        "path": TLD_PROBS_PATH.name,
        "n_tlds": len(mapping),
        "keys_with_path_fragment": int(sum("/" in key for key in mapping)),
        "default": data["default"],
        "test_rows_covered_pct": round(float(covered.mean() * 100), 2),
        "note": (
            "Dibuat src/train.py:95 dengan rsplit pada URL penuh, sehingga sebagian besar kunci "
            "mengandung fragmen path dan tidak pernah cocok saat inference (TLD dari host)."
        ),
    }


def train_experiment() -> dict[str, object]:
    started = time.perf_counter()
    raw = pd.read_parquet(DATA_PARQUET)
    df = dedupe_by_url(raw)
    urls = df["URL"].astype(str).str.strip().to_numpy()
    labels = df["label"].to_numpy(dtype=np.int8)
    hosts = np.array([host_of(url) for url in urls])
    tlds = np.array([tld_of_host(host) for host in hosts])

    train_pos, test_pos = group_split(hosts)
    folds = grouped_folds(train_pos, labels, hosts)

    train_table, train_default = build_host_tld_probs(hosts[train_pos], labels[train_pos])
    url_frame = to_frame(urls, train_table, train_default)
    host_frame = to_host_frame(urls, train_table, train_default)

    # OOF: nilai TLD untuk baris train hanya dari fold lain, dipakai saat fit akhir.
    fold_data = []
    oof_values = np.empty(len(train_pos), dtype=float)
    for fit_rel, val_rel in folds:
        fit_abs = train_pos[fit_rel]
        table, default = build_host_tld_probs(hosts[fit_abs], labels[fit_abs])
        oof_values[val_rel] = tld_values(tlds[train_pos[val_rel]], table, default)
        fold_data.append((fit_rel, val_rel, table, default))

    variants: dict[str, object] = {}
    for name, spec in VARIANTS.items():
        frame = url_frame if spec["source"] == "url" else host_frame
        drop = list(spec["drop"])

        cv_started = time.perf_counter()
        fold_scores = []
        for fit_rel, val_rel, table, default in fold_data:
            fit_abs, val_abs = train_pos[fit_rel], train_pos[val_rel]
            pipe = build_models()["xgb"]
            pipe.fit(
                matrix(frame, fit_abs, tlds, table, default, drop),
                labels[fit_abs],
            )
            proba = phishing_proba(pipe, matrix(frame, val_abs, tlds, table, default, drop))
            fold_scores.append(score_block(labels[val_abs], proba))
        cv_seconds = time.perf_counter() - cv_started

        fit_started = time.perf_counter()
        x_train = frame.iloc[train_pos].copy()
        x_train["TLDLegitimateProb"] = oof_values
        if drop:
            x_train = x_train.drop(columns=drop)
        pipe = build_models()["xgb"]
        pipe.fit(x_train.to_numpy(dtype=np.float32), labels[train_pos])
        fit_seconds = time.perf_counter() - fit_started

        x_test = frame.iloc[test_pos]
        if drop:
            x_test = x_test.drop(columns=drop)
        test_scores = score_block(labels[test_pos], phishing_proba(pipe, x_test))

        experiment_dir = EXPERIMENT_DIR
        experiment_dir.mkdir(parents=True, exist_ok=True)
        artifact = experiment_dir / f"{name}.pkl"
        joblib.dump(pipe, artifact)

        features = [column for column in frame.columns if column not in drop]
        est = pipe.named_steps["model"]
        variants[name] = {
            "source": spec["source"],
            "drop": drop,
            "features": features,
            "n_features": len(features),
            "hyperparameters": {key: est.get_params()[key] for key in HYPERPARAMETER_KEYS},
            "cv_grouped": {
                "f1_phishing_mean": round(float(np.mean([row["f1"] for row in fold_scores])), 4),
                "mcc_mean": round(float(np.mean([row["mcc"] for row in fold_scores])), 4),
                "roc_auc_mean": round(float(np.mean([row["roc_auc"] for row in fold_scores])), 4),
                "folds": [
                    {key: row[key] for key in ("n", "tp", "fp", "fn", "tn", "precision",
                                                "recall", "f1", "specificity", "mcc", "roc_auc")}
                    for row in fold_scores
                ],
            },
            "test_grouped": test_scores,
            "train_seconds": {"cv": round(cv_seconds, 1), "final_fit": round(fit_seconds, 1)},
            "artifact": artifact.relative_to(ROOT).as_posix(),
        }
        print(
            f"{name}: CV F1={variants[name]['cv_grouped']['f1_phishing_mean']} "
            f"test F1={test_scores['f1']} test ROC-AUC={test_scores['roc_auc']} "
            f"({round(cv_seconds + fit_seconds, 1)} detik)"
        )

    ranking = sorted(
        variants,
        key=lambda item: (
            variants[item]["cv_grouped"]["f1_phishing_mean"],
            variants[item]["cv_grouped"]["mcc_mean"],
        ),
        reverse=True,
    )
    new_covered = np.array([tld in train_table for tld in tlds[test_pos]])
    payload: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "Membandingkan Model B dengan model host-only pada split berkelompok per host.",
        "parameters": {
            "seed": SEED,
            "test_size": TEST_SIZE,
            "threshold": THRESHOLD,
            "positive_class": "phishing (label 0)",
            "cv_folds": CV_FOLDS,
            "split": "GroupShuffleSplit per host, 80/20",
            "cv": "StratifiedGroupKFold per host di train",
            "hyperparameters": variants["B_refit"]["hyperparameters"],
        },
        "data": {
            "source": DATA_PARQUET.name,
            "raw_rows": int(len(raw)),
            "rows_after_dedup": int(len(df)),
            "duplicate_url_rows_removed": int(len(raw) - len(df)),
            "unique_hosts": int(len(set(hosts))),
            "labels": label_counts(labels),
        },
        "split": {
            "train_rows": int(len(train_pos)),
            "test_rows": int(len(test_pos)),
            "test_rows_pct": round(float(len(test_pos) / len(df) * 100), 2),
            "train_hosts": int(len(np.unique(hosts[train_pos]))),
            "test_hosts": int(len(np.unique(hosts[test_pos]))),
            "host_overlap": 0,
            "train_labels": label_counts(labels[train_pos]),
            "test_labels": label_counts(labels[test_pos]),
        },
        "tld_probability": {
            "new": {
                "source": "TLD dari host (src/features_host.py:tld_of_host), split train",
                "formula": "(jumlah legit per TLD + 1) / (jumlah total per TLD + 2)",
                "default_formula": "(jumlah legit train + 1) / (jumlah baris train + 2)",
                "n_tlds": len(train_table),
                "default": train_default,
                "test_rows_covered_pct": round(float(new_covered.mean() * 100), 2),
                "train_values": "out-of-fold dari 5 fold berkelompok",
                "test_values": "tabel dari seluruh train",
            },
            "old": old_tld_comparison(tlds, test_pos),
        },
        "variants": variants,
        "selection": {
            "selected": ranking[0],
            "ranking": ranking,
            "criterion": (
                "F1 phishing rata-rata CV train berkelompok (tie-break MCC); "
                "test berkelompok dan set T18 tidak dipakai memilih"
            ),
        },
        "evaluation": None,
        "limitations": [
            "Model C hanya melihat host: path, query, skema, dan isi halaman tidak dipakai.",
            "Dibuang dari C_host: IsHTTPS/skema, URLLength, seluruh path/query, hitungan "
            "'=', '?', '&', fitur obfuscation URL, dan fitur konten; B_noHTTPS hanya "
            "membuang IsHTTPS.",
            "Fitur host dilebur menjadi satu vonis per host, sehingga phishing di host sah "
            "(mis. layanan user-content) dan legit di host buruk tidak dapat dibedakan.",
            "Split dikelompokkan per host penuh, bukan registrable domain; subdomain berbeda "
            "dari domain yang sama masih bisa muncul di kedua sisi.",
            "GroupShuffleSplit tidak stratified, jadi proporsi label train/test bisa bergeser.",
            "Tabel TLD baru memakai TLD host; tabel lama dihitung dari URL penuh sehingga "
            "banyak kuncinya tidak pernah cocok saat inference.",
            "Set legit T18 kecil, sehingga specificity dan interval kepercayaannya lebar.",
        ],
    }
    payload["train_seconds_total"] = round(time.perf_counter() - started, 1)

    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    TLD_PATH.write_text(
        json.dumps(
            {
                "default": train_default,
                "map": train_table,
                "source": "TLD host dari split train, Laplace smoothing, tabel penuh",
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    payload = train_experiment()
    print(f"Dipilih (CV): {payload['selection']['selected']}")
    print(f"TLD baru: {payload['tld_probability']['new']['n_tlds']} TLD, "
          f"default={payload['tld_probability']['new']['default']}")
    print(f"Ditulis: {JSON_PATH.relative_to(ROOT)} dan {EXPERIMENT_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
