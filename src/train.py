"""Latih Model A (50 fitur) & Model B (19 fitur URL), pilih terbaik via 5-fold CV pada train."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # agar `import src.*` jalan sebagai skrip

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.config import (
    CV_FOLDS,
    DATA_PARQUET,
    FULL_FEATURES,
    LABEL_PHISH,
    LR_MAX_ITER,
    METRICS_PATH,
    MODEL_A_PATH,
    MODEL_B_PATH,
    N_ESTIMATORS_RF,
    N_ESTIMATORS_XGB,
    SEED,
    STATS_PATH,
    TEST_SIZE,
    THRESHOLD,
    TLD_PROBS_PATH,
    URL_FEATURES,
)
from src.feature_utils import to_frame

MODEL_NAMES = {"model_a": "Model A (full)", "model_b": "Model B (URL-only)"}
PHISHING_F1 = make_scorer(f1_score, pos_label=LABEL_PHISH)


def build_models() -> dict[str, Pipeline]:
    """Satu pipeline per algoritme: imputer median di-fit hanya pada train."""
    imputer = lambda: SimpleImputer(strategy="median")  # noqa: E731
    return {
        "lr": Pipeline(
            [
                ("imputer", imputer()),
                ("scaler", StandardScaler()),  # LR tidak konvergen baik pada hitungan mentah
                ("model", LogisticRegression(max_iter=LR_MAX_ITER, random_state=SEED)),
            ]
        ),
        "rf": Pipeline(
            [
                ("imputer", imputer()),
                ("model", RandomForestClassifier(n_estimators=N_ESTIMATORS_RF, n_jobs=-1, random_state=SEED)),
            ]
        ),
        "xgb": Pipeline(
            [
                ("imputer", imputer()),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=N_ESTIMATORS_XGB,
                        learning_rate=0.1,
                        max_depth=6,
                        tree_method="hist",
                        n_jobs=-1,
                        random_state=SEED,
                        eval_metric="logloss",
                    ),
                ),
            ]
        ),
    }


def model_params(pipe: Pipeline) -> dict:
    est = pipe.named_steps["model"]
    return {k: v for k, v in est.get_params().items() if not k.startswith("_")}


def build_tld_probs(urls: pd.Series, labels: np.ndarray) -> tuple[dict[str, float], float]:
    """P(TLD legitimate) dari train saja, dengan Laplace smoothing; default = rasio global train."""
    tlds = urls.map(lambda u: u.rsplit(".", 1)[-1].lower() if "." in (u or "") else "")
    frame = pd.DataFrame({"tld": tlds.to_numpy(), "y": labels})
    agg = frame.groupby("tld")["y"].agg(["sum", "count"])
    probs = ((agg["sum"] + 1) / (agg["count"] + 2)).round(6).to_dict()
    default = round(float((labels.sum() + 1) / (len(labels) + 2)), 6)
    return probs, default


def feature_importances(pipe: Pipeline) -> list[float]:
    est = pipe.named_steps["model"]
    if hasattr(est, "feature_importances_"):
        return [float(v) for v in est.feature_importances_]
    return [float(abs(v)) for v in est.coef_[0]]  # LR: |koefisien| sebagai pengganti importance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="uji cepat memakai N baris (0 = semua)")
    args = parser.parse_args()

    started = time.perf_counter()
    df = pd.read_parquet(DATA_PARQUET)
    if args.sample:
        df = df.sample(n=args.sample, random_state=SEED).reset_index(drop=True)

    # Verifikasi dtype: kolom numerik harus sama persis dengan FULL_FEATURES (T2/DESCRIBE).
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != "label"]
    if set(numeric) != set(FULL_FEATURES):
        print(f"FULL_FEATURES tidak cocok dengan kolom numerik Parquet.\n  parquet: {sorted(set(numeric) - set(FULL_FEATURES))}\n  config : {sorted(set(FULL_FEATURES) - set(numeric))}")
        return 1
    print(f"Data: {len(df)} baris, {len(numeric)} fitur Model A. Label: {df['label'].value_counts().to_dict()}")

    y = df["label"].to_numpy(dtype=np.int8)
    train_idx, _ = train_test_split(
        np.arange(len(df)), test_size=TEST_SIZE, stratify=y, random_state=SEED
    )

    urls = df["URL"].astype(str)
    tld_probs, tld_default = build_tld_probs(urls.iloc[train_idx], y[train_idx])
    TLD_PROBS_PATH.write_text(json.dumps({"default": tld_default, "map": tld_probs}, indent=1))
    print(f"TLD probs: {len(tld_probs)} TLD dari train, default={tld_default} -> {TLD_PROBS_PATH.name}")

    X_a = df[FULL_FEATURES].astype(np.float32).to_numpy()
    X_b = to_frame(urls, tld_probs, tld_default).to_numpy(dtype=np.float32)

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    metrics: dict = {
        "split": {
            "seed": SEED,
            "test_size": TEST_SIZE,
            "stratified": True,
            "n_train": int(len(train_idx)),
            "n_test": int(len(df) - len(train_idx)),
            "cv_folds": CV_FOLDS,
            "sampled_rows": args.sample or None,
        },
        "label": {"phishing": LABEL_PHISH, "legitimate": 1, "threshold": THRESHOLD},
        "selection": "rata-rata F1 kelas phishing (label 0) pada 5-fold CV di train",
    }
    stats: dict = {"label": {"phishing": LABEL_PHISH, "legitimate": 1}, "threshold": THRESHOLD}

    for key, X, columns, out_path in (
        ("model_a", X_a, FULL_FEATURES, MODEL_A_PATH),
        ("model_b", X_b, URL_FEATURES, MODEL_B_PATH),
    ):
        print(f"\n=== {MODEL_NAMES[key]}: {len(columns)} fitur ===")
        X_train, y_train = X[train_idx], y[train_idx]
        scores: dict[str, dict] = {}
        for name, pipe in build_models().items():
            t0 = time.perf_counter()
            cv_scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring=PHISHING_F1, n_jobs=1)
            scores[name] = {
                "cv_f1_phishing_mean": round(float(cv_scores.mean()), 6),
                "cv_f1_phishing_std": round(float(cv_scores.std()), 6),
                "cv_folds": [round(float(s), 6) for s in cv_scores],
                "params": model_params(pipe),
                "fit_seconds": round(time.perf_counter() - t0, 1),
            }
            print(f"  {name:4s} F1(phishing) CV = {cv_scores.mean():.4f} ± {cv_scores.std():.4f} ({scores[name]['fit_seconds']}s)")

        best_name = max(scores, key=lambda n: scores[n]["cv_f1_phishing_mean"])
        best = build_models()[best_name]
        best.fit(X_train, y_train)
        dump(best, out_path)
        print(f"  terbaik: {best_name} -> {out_path.name}")

        metrics[key] = {**scores, "best": best_name, "n_features": len(columns)}
        stats[key] = {
            "features": list(columns),
            "importances": feature_importances(best),
            "class_means": {
                "phishing": {c: float(np.mean(X_train[y_train == LABEL_PHISH, i])) for i, c in enumerate(columns)},
                "legit": {c: float(np.mean(X_train[y_train == 1, i])) for i, c in enumerate(columns)},
            },
            "best": best_name,
        }

    metrics["trained_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metrics["label_order"] = {"P(phishing)": "predict_proba[:, 0]"}
    METRICS_PATH.write_text(json.dumps(metrics, indent=1))
    STATS_PATH.write_text(json.dumps(stats, indent=1))

    print(f"\nSelesai dalam {time.perf_counter() - started:.1f}s")
    print(f"Metrik: {METRICS_PATH.relative_to(DATA_PARQUET.parents[1])}, stats: {STATS_PATH.name}")
    for key in ("model_a", "model_b"):
        m = metrics[key]
        print(f"{key}: best={m['best']} F1(phishing) CV={m[m['best']]['cv_f1_phishing_mean']:.4f} (target >= {'0.97' if key == 'model_a' else '0.95'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
