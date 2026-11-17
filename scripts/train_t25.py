"""T25: latih C_host dengan normalisasi www. dan hitung CV/test berkelompok.

Kandidat: B_refit (dimuat), C_host (dilatih ulang, host tanpa www.), dan aturan
kesepakatan B+C (tanpa model baru). Artefak ke models/experimental/; src/model.pkl
tidak disentuh. Angka latih ditulis ke docs/t25.json (bagian train).
"""

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from scripts.eval_realworld import metrics
from src.config import (
    DATA_PARQUET,
    LABEL_LEGIT,
    LABEL_PHISH,
    SEED,
    TEST_SIZE,
    THRESHOLD,
)
from src.feature_utils import to_frame
from src.features_host import host_of, to_host_frame
from src.train import build_models

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "models" / "experimental"
JSON_PATH = ROOT / "docs" / "t25.json"
B_REFIT_PATH = EXPERIMENT_DIR / "B_refit.pkl"
C_HOST_OLD_PATH = EXPERIMENT_DIR / "C_host.pkl"
C_HOST_NEW_PATH = EXPERIMENT_DIR / "C_host.pkl"
C_HOST_PREV_PATH = EXPERIMENT_DIR / "C_host_prev.pkl"
TLD_OLD_PATH = EXPERIMENT_DIR / "tld_probs_host.json"
TLD_NEW_PATH = EXPERIMENT_DIR / "tld_probs_host.json"
TLD_PREV_PATH = EXPERIMENT_DIR / "tld_probs_host_prev.json"


def dedupe_by_url(df):
    return df.drop_duplicates("URL", keep="first").reset_index(drop=True)


def group_split(hosts):
    from sklearn.model_selection import GroupShuffleSplit

    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=SEED)
    train_pos, test_pos = next(splitter.split(np.zeros(len(hosts)), groups=hosts))
    if len(set(hosts[train_pos]) & set(hosts[test_pos])):
        raise RuntimeError("host tumpang tindih pada split")
    return np.sort(train_pos), np.sort(test_pos)


def grouped_folds(train_pos, labels, hosts):
    from sklearn.model_selection import StratifiedGroupKFold

    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    return list(splitter.split(np.zeros(len(train_pos)), labels[train_pos], groups=hosts[train_pos]))


def build_host_tld_probs(hosts, labels):
    frame = pd.DataFrame({"tld": [h.rsplit(".", 1)[-1] if "." in h else "" for h in hosts], "y": np.asarray(labels)})
    agg = frame.groupby("tld")["y"].agg(["sum", "count"])
    probs = ((agg["sum"] + 1) / (agg["count"] + 2)).round(6).to_dict()
    default = round(float((np.asarray(labels).sum() + 1) / (len(labels) + 2)), 6)
    return probs, default


def tld_values(tlds, table, default):
    return np.array([table.get(tld, default) for tld in tlds], dtype=float)


def matrix(frame, positions, tlds, table, default, drop):
    block = frame.iloc[positions].copy()
    block["TLDLegitimateProb"] = tld_values(tlds[positions], table, default)
    if drop:
        block = block.drop(columns=list(drop))
    return block.to_numpy(dtype=np.float32)


def phishing_proba(pipe, frame):
    values = frame.to_numpy(dtype=np.float32) if hasattr(frame, "to_numpy") else frame
    proba = pipe.predict_proba(values)
    return np.asarray(proba[:, list(pipe.classes_).index(LABEL_PHISH)], dtype=float)


def score_block(y_true, proba):
    predicted = np.where(proba >= THRESHOLD, LABEL_PHISH, LABEL_LEGIT).astype(int)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = round(float(roc_auc_score((np.asarray(y_true) == LABEL_PHISH).astype(int), proba)), 4)
    return block


def consensus_proba(p_b, p_c):
    """Label konsensus: PHISHING jika keduanya phishing, LEGITIMATE jika keduanya legit, selain itu SUSPICIOUS."""
    label_b = np.where(p_b >= THRESHOLD, LABEL_PHISH, LABEL_LEGIT)
    label_c = np.where(p_c >= THRESHOLD, LABEL_PHISH, LABEL_LEGIT)
    verdict = np.array(["SUSPICIOUS"] * len(p_b), dtype=object)
    verdict[(label_b == LABEL_PHISH) & (label_c == LABEL_PHISH)] = "PHISHING"
    verdict[(label_b == LABEL_LEGIT) & (label_c == LABEL_LEGIT)] = "LEGITIMATE"
    # untuk metrik biner, SUSPICIOUS dihitung non-phishing
    predicted = np.where(verdict == "PHISHING", LABEL_PHISH, LABEL_LEGIT).astype(int)
    suspicious_pct = round(float(np.mean(verdict == "SUSPICIOUS") * 100), 2)
    return verdict, predicted, suspicious_pct


def consensus_block(y_true, p_b, p_c):
    verdict, predicted, suspicious_pct = consensus_proba(p_b, p_c)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = None
    block["suspicious_pct"] = suspicious_pct
    block["suspicious_n"] = int(np.sum(verdict == "SUSPICIOUS"))
    return block


def t24a_aggregate():
    """Agregat T24a bila file tersedia; jika tidak, laporkan belum tersedia."""
    files = {
        "review": ROOT / "data" / "realworld" / "legit_review.csv",
        "dev": ROOT / "data" / "realworld" / "legit_dev.csv",
        "final": ROOT / "data" / "realworld" / "legit_final.csv",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        return {"available": False, "missing": missing, "note": "Jalankan T24a dulu untuk menghasilkan file ini."}
    import csv as _csv

    def summarize(path):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = [dict(row) for row in _csv.DictReader(handle)]
        hosts = { (r.get("url") or "").split("/")[2] if "://" in (r.get("url") or "") else "" for r in rows }
        contributors = { (r.get("person_label") or "").strip() for r in rows if (r.get("person_label") or "").strip() }
        return {
            "rows": len(rows),
            "root": sum((r.get("host_type") or "") == "root" for r in rows),
            "berpath": sum((r.get("host_type") or "") == "berpath" for r in rows),
            "outside_allowlist": sum((r.get("in_allowlist") or "") == "0" for r in rows),
            "hosts": len(hosts - {""}),
            "contributors": len(contributors),
        }

    return {
        "available": True,
        "review": summarize(files["review"]),
        "dev": summarize(files["dev"]),
        "final": summarize(files["final"]),
    }


def main():
    started = time.perf_counter()
    raw = pd.read_parquet(DATA_PARQUET)
    df = dedupe_by_url(raw)
    urls = df["URL"].astype(str).str.strip().to_numpy()
    labels = df["label"].to_numpy(dtype=np.int8)
    hosts_old = np.array([host_of(u) for u in urls])
    hosts_new = np.array([host_of(u, strip_www=True) for u in urls])
    tlds_old = np.array([h.rsplit(".", 1)[-1] if "." in h else "" for h in hosts_old])
    tlds_new = np.array([h.rsplit(".", 1)[-1] if "." in h else "" for h in hosts_new])

    train_pos, test_pos = group_split(hosts_old)
    # host grouping must be identical after www normalization? Compare
    host_overlap_new = len(set(hosts_new[train_pos]) & set(hosts_new[test_pos]))
    folds = grouped_folds(train_pos, labels, hosts_old)

    # Save old artifact before overwrite
    if C_HOST_OLD_PATH.exists():
        shutil.copyfile(C_HOST_OLD_PATH, C_HOST_PREV_PATH)
    if TLD_OLD_PATH.exists():
        shutil.copyfile(TLD_OLD_PATH, TLD_PREV_PATH)

    # Tables
    table_old, default_old = build_host_tld_probs(hosts_old[train_pos], labels[train_pos])
    table_new, default_new = build_host_tld_probs(hosts_new[train_pos], labels[train_pos])

    url_frame = to_frame(urls, table_old, default_old)
    host_frame_old = to_host_frame(urls, table_old, default_old, strip_www=False)
    host_frame_new = to_host_frame(urls, table_new, default_new, strip_www=True)

    # CV
    cv_started = time.perf_counter()
    b_folds = []
    c_old_folds = []
    c_new_folds = []
    consensus_folds = []
    for fit_rel, val_rel in folds:
        fit_abs, val_abs = train_pos[fit_rel], train_pos[val_rel]
        # B_refit
        pipe_b = build_models()["xgb"]
        pipe_b.fit(matrix(url_frame, fit_abs, tlds_old, table_old, default_old, []), labels[fit_abs])
        proba_b = phishing_proba(pipe_b, matrix(url_frame, val_abs, tlds_old, table_old, default_old, []))
        # C old
        pipe_co = build_models()["xgb"]
        pipe_co.fit(matrix(host_frame_old, fit_abs, tlds_old, table_old, default_old, []), labels[fit_abs])
        proba_co = phishing_proba(pipe_co, matrix(host_frame_old, val_abs, tlds_old, table_old, default_old, []))
        # C new
        pipe_cn = build_models()["xgb"]
        pipe_cn.fit(matrix(host_frame_new, fit_abs, tlds_new, table_new, default_new, []), labels[fit_abs])
        proba_cn = phishing_proba(pipe_cn, matrix(host_frame_new, val_abs, tlds_new, table_new, default_new, []))
        # consensus
        _, pred_cons, susp_pct = consensus_proba(proba_b, proba_cn)
        cons_block = metrics(np.asarray(labels[val_abs], dtype=int).tolist(), pred_cons.tolist())
        cons_block["roc_auc"] = None
        cons_block["suspicious_pct"] = susp_pct
        cons_block["suspicious_n"] = int(np.sum(pred_cons == -1))  # placeholder replaced below
        # fix suspicious count properly
        verdict, _, _ = consensus_proba(proba_b, proba_cn)
        cons_block["suspicious_n"] = int(np.sum(verdict == "SUSPICIOUS"))

        b_folds.append(score_block(labels[val_abs], proba_b))
        c_old_folds.append(score_block(labels[val_abs], proba_co))
        c_new_folds.append(score_block(labels[val_abs], proba_cn))
        consensus_folds.append(cons_block)
    cv_seconds = time.perf_counter() - cv_started

    def mean_metric(folds, key):
        return round(float(np.mean([f[key] for f in folds])), 4)

    # Final C_new
    fit_started = time.perf_counter()
    x_train = host_frame_new.iloc[train_pos].copy()
    x_train["TLDLegitimateProb"] = tld_values(tlds_new[train_pos], table_new, default_new)
    pipe_c_new = build_models()["xgb"]
    pipe_c_new.fit(x_train.to_numpy(dtype=np.float32), labels[train_pos])
    fit_seconds = time.perf_counter() - fit_started
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe_c_new, C_HOST_NEW_PATH)
    TLD_NEW_PATH.write_text(json.dumps({"default": default_new, "map": table_new, "source": "host TLD tanpa www, split train"}, indent=1), encoding="utf-8")

    # B_refit loaded
    pipe_b_final = joblib.load(B_REFIT_PATH)

    # Test blocks
    def test_block(pipe, frame, tlds, table, default, drop):
        x = frame.iloc[test_pos]
        if drop:
            x = x.drop(columns=list(drop))
        proba = phishing_proba(pipe, x)
        return score_block(labels[test_pos], proba), proba

    b_test_block, p_b_test = test_block(pipe_b_final, url_frame, tlds_old, table_old, default_old, [])
    # old C_host
    if C_HOST_PREV_PATH.exists():
        pipe_c_old = joblib.load(C_HOST_PREV_PATH)
        old_tld = json.loads(TLD_PREV_PATH.read_text(encoding="utf-8")) if TLD_PREV_PATH.exists() else {"map": table_old, "default": default_old}
        c_old_test_block, p_c_old_test = test_block(pipe_c_old, host_frame_old, tlds_old, old_tld["map"], old_tld["default"], [])
    else:
        c_old_test_block, p_c_old_test = None, None
    c_new_test_block, p_c_new_test = test_block(pipe_c_new, host_frame_new, tlds_new, table_new, default_new, [])
    # consensus test
    verdict_test, pred_cons_test, susp_pct_test = consensus_proba(p_b_test, p_c_new_test)
    cons_test_block = metrics(np.asarray(labels[test_pos], dtype=int).tolist(), pred_cons_test.tolist())
    cons_test_block["roc_auc"] = None
    cons_test_block["suspicious_pct"] = susp_pct_test
    cons_test_block["suspicious_n"] = int(np.sum(verdict_test == "SUSPICIOUS"))

    # Effect of www normalization on C_host
    effect = {
        "old_c_host": c_old_test_block,
        "new_c_host": c_new_test_block,
        "delta_f1": round(float(c_new_test_block["f1"] - (c_old_test_block["f1"] if c_old_test_block else 0)), 4) if c_old_test_block else None,
        "delta_mcc": round(float(c_new_test_block["mcc"] - (c_old_test_block["mcc"] if c_old_test_block else 0)), 4) if c_old_test_block else None,
        "delta_roc_auc": round(float(c_new_test_block["roc_auc"] - (c_old_test_block["roc_auc"] if c_old_test_block else 0)), 4) if c_old_test_block else None,
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "T25: pemilihan B_refit vs C_host (normalisasi www.) vs aturan kesepakatan B+C.",
        "protocol": "docs/protokol_t25.md",
        "parameters": {
            "seed": SEED,
            "test_size": TEST_SIZE,
            "threshold": THRESHOLD,
            "positive_class": "phishing (label 0)",
            "cv_folds": 5,
            "www_normalization": "host tanpa awalan www. sebelum ekstraksi fitur C_host",
        },
        "data": {
            "raw_rows": int(len(raw)),
            "rows_after_dedup": int(len(df)),
            "duplicate_url_rows_removed": int(len(raw) - len(df)),
            "unique_hosts_old": int(len(set(hosts_old))),
            "unique_hosts_new": int(len(set(hosts_new))),
            "labels": {"legit": int(np.sum(labels == LABEL_LEGIT)), "phishing": int(np.sum(labels == LABEL_PHISH))},
            "host_overlap_after_split_old": 0,
            "host_overlap_after_split_new": int(host_overlap_new),
        },
        "split": {
            "train_rows": int(len(train_pos)),
            "test_rows": int(len(test_pos)),
            "train_hosts_old": int(len(np.unique(hosts_old[train_pos]))),
            "test_hosts_old": int(len(np.unique(hosts_old[test_pos]))),
            "train_hosts_new": int(len(np.unique(hosts_new[train_pos]))),
            "test_hosts_new": int(len(np.unique(hosts_new[test_pos]))),
        },
        "tld_probability": {
            "old": {"n_tlds": len(table_old), "default": default_old, "source": "host TLD dengan www (T24)"},
            "new": {"n_tlds": len(table_new), "default": default_new, "source": "host TLD tanpa www (T25)"},
        },
        "cv_grouped": {
            "B_refit": {
                "f1_phishing_mean": mean_metric(b_folds, "f1"),
                "mcc_mean": mean_metric(b_folds, "mcc"),
                "roc_auc_mean": mean_metric(b_folds, "roc_auc"),
                "folds": b_folds,
            },
            "C_host_old": {
                "f1_phishing_mean": mean_metric(c_old_folds, "f1"),
                "mcc_mean": mean_metric(c_old_folds, "mcc"),
                "roc_auc_mean": mean_metric(c_old_folds, "roc_auc"),
                "folds": c_old_folds,
            },
            "C_host": {
                "f1_phishing_mean": mean_metric(c_new_folds, "f1"),
                "mcc_mean": mean_metric(c_new_folds, "mcc"),
                "roc_auc_mean": mean_metric(c_new_folds, "roc_auc"),
                "folds": c_new_folds,
            },
            "consensus": {
                "mcc_mean": mean_metric(consensus_folds, "mcc"),
                "suspicious_pct_mean": mean_metric(consensus_folds, "suspicious_pct"),
                "folds": consensus_folds,
            },
        },
        "test_grouped": {
            "B_refit": b_test_block,
            "C_host_old": c_old_test_block,
            "C_host": c_new_test_block,
            "consensus": cons_test_block,
        },
        "www_normalization_effect": effect,
        "artifacts": {
            "B_refit": B_REFIT_PATH.relative_to(ROOT).as_posix(),
            "C_host": C_HOST_NEW_PATH.relative_to(ROOT).as_posix(),
            "C_host_previous": C_HOST_PREV_PATH.relative_to(ROOT).as_posix() if C_HOST_PREV_PATH.exists() else None,
            "tld_host": TLD_NEW_PATH.relative_to(ROOT).as_posix(),
        },
        "t24a_aggregate": t24a_aggregate(),
        "train_seconds_total": round(time.perf_counter() - started, 1),
        "evaluation": None,
    }

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"B_refit test F1={b_test_block['f1']} AUC={b_test_block['roc_auc']}")
    print(f"C_host (www norm) test F1={c_new_test_block['f1']} AUC={c_new_test_block['roc_auc']}")
    if c_old_test_block:
        print(f"C_host (T24) test F1={c_old_test_block['f1']} AUC={c_old_test_block['roc_auc']}")
    print(f"Consensus test suspicious={susp_pct_test}% MCC={cons_test_block['mcc']}")
    print(f"Ditulis: {JSON_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
