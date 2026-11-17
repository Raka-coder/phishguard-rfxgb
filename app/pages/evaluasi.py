"""Halaman evaluasi: CV, benchmark test set vs dunia nyata, diagnostik, dan keterbatasan."""

import json
import re
from pathlib import Path

import reflex as rx

from app import style as t
from app.components import card, card_title, muted, page_shell

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "docs" / "metrics.json"
HASIL_PATH = ROOT / "docs" / "hasil_evaluasi.md"
REALWORLD_PATH = ROOT / "docs" / "realworld.json"
MODEL_C_PATH = ROOT / "docs" / "model_c.json"
DENYLIST_PATH = ROOT / "docs" / "denylist.json"
T25_PATH = ROOT / "docs" / "t25.json"
LIMITATIONS_PATH = ROOT / "app" / "limitations.json"

MODEL_GROUPS = (("model_a", "Model A (full)"), ("model_b", "Model B (URL-only)"))
ALGOS = ("lr", "rf", "xgb")
_CONF_RE = re.compile(r"Confusion matrix — Model B.*?TP=(\d+), FN=(\d+), FP=(\d+), TN=(\d+)", re.S)
_METRIC_RE = re.compile(
    r"^\|\s*B\s*\|\s*\d+\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
    re.MULTILINE,
)


# --- Helper murni (mudah dites tanpa Reflex) --------------------------------
def build_cv_rows(metrics: dict) -> list[list[str]]:
    """Baris tabel CV: [grup, algoritma, F1, penanda terbaik]."""
    rows: list[list[str]] = []
    for group, label in MODEL_GROUPS:
        data = metrics.get(group, {}) or {}
        for model in ALGOS:
            info = data.get(model, {}) or {}
            rows.append(
                [
                    label,
                    model.upper(),
                    format_pct(info.get("cv_f1_phishing_mean")),
                    "★" if model == data.get("best") else "",
                ]
            )
    return rows


def build_cv_chart(metrics: dict) -> list[dict]:
    """Satu baris per algoritma: F1 rata-rata CV untuk Model A dan Model B."""
    out = []
    for model in ALGOS:
        row = {"model": model.upper()}
        for group, label in (("model_a", "Model A"), ("model_b", "Model B")):
            info = (metrics.get(group, {}) or {}).get(model, {}) or {}
            row[label] = round(float(info.get("cv_f1_phishing_mean", 0.0)), 4)
        out.append(row)
    return out


def build_fold_chart(metrics: dict) -> list[dict]:
    """F1 per fold untuk Model B (satu baris per fold, satu kolom per algoritma)."""
    group = metrics.get("model_b", {}) or {}
    folds = {m: (group.get(m, {}) or {}).get("cv_folds", []) for m in ALGOS}
    n = max((len(v) for v in folds.values()), default=0)
    out = []
    for i in range(n):
        row = {"fold": f"Fold {i + 1}"}
        for m in ALGOS:
            row[m.upper()] = round(float(folds[m][i]), 4) if i < len(folds[m]) else None
        out.append(row)
    return out


def build_split_chart(split: dict) -> list[dict]:
    return [
        {"name": "Data latih", "value": int(split.get("n_train") or 0), "fill": t.PURPLE},
        {"name": "Data uji", "value": int(split.get("n_test") or 0), "fill": t.ORANGE},
    ]


def parse_confusion(markdown: str) -> dict[str, str] | None:
    """TP/FN/FP/TN Model B dari hasil_evaluasi.md; None bila format tidak cocok."""
    match = _CONF_RE.search(markdown or "")
    if not match:
        return None
    return {k: format_count(v) for k, v in zip(("tp", "fn", "fp", "tn"), match.groups())}


def format_count(value) -> str:
    """Pemisah ribuan gaya Indonesia; non-angka dikembalikan apa adanya."""
    if value in (None, ""):
        return ""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def clean_report(markdown: str) -> str:
    """Sel tabel memakai <br>; renderer markdown menampilkannya sebagai teks, jadi ganti."""
    return markdown.replace("<br>", "; ")


def format_pct(value) -> str:
    """Rasio 0-1 dari artefak menjadi persen; kosong -> 'tidak berlaku'."""
    if value in (None, ""):
        return "tidak berlaku"
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(value)


def format_percent_value(value) -> str:
    """Nilai yang sudah berskala persen di artefak (mis. suspicious_pct)."""
    if value in (None, ""):
        return "tidak berlaku"
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return str(value)


def format_hours(value) -> str:
    """Selang antarsnapshot dalam jam."""
    if value in (None, ""):
        return "tidak berlaku"
    try:
        return f"{float(value):.2f} jam"
    except (TypeError, ValueError):
        return str(value)


def format_delta(value) -> str:
    """Tanda plus/minus untuk selisih antarartefak, dalam persen."""
    if value in (None, ""):
        return "tidak berlaku"
    try:
        return f"{float(value) * 100:+.2f}%"
    except (TypeError, ValueError):
        return str(value)


# --- T22: pembaca metrik dari artefak skrip evaluasi -------------------------
def build_test_metrics(hasil_md: str) -> dict | None:
    """Baris metrik Model B pada test set dari hasil_evaluasi.md; None bila format tidak cocok."""
    match = _METRIC_RE.search(hasil_md or "")
    if not match:
        return None
    conf = _CONF_RE.search(hasil_md or "")
    return {
        "accuracy": float(match.group(1)),
        "precision": float(match.group(2)),
        "recall": float(match.group(3)),
        "f1": float(match.group(4)),
        "fp": int(match.group(5)),
        "fn": int(match.group(6)),
        "tp": int(conf.group(1)) if conf else 0,
        "tn": int(conf.group(4)) if conf else 0,
    }


def build_realworld_metrics(realworld: dict) -> dict:
    """Blok metrik dunia nyata (model_only + with_reputation) dari docs/realworld.json."""
    full = ((realworld or {}).get("variants") or {}).get("full") or {}
    with_rep = full.get("with_reputation") or {}
    group = str(with_rep.get("primary_group") or "not_in_allowlist")
    primary = with_rep.get("primary") or (with_rep.get("by_allowlist") or {}).get(group) or {}
    return {
        "generated_at": str(realworld.get("generated_at") or ""),
        "model_only": full.get("model_only") or {},
        "primary_group": group,
        "primary": primary,
        "all": with_rep.get("all") or {},
    }


def _one_block(block: dict) -> dict:
    """Ambil metrik satu blok, lengkap dengan interval Wilson; siap dipakai di UI."""
    ci_fp = block.get("fp_rate_ci95") or {}
    ci_recall = block.get("recall_ci95") or {}
    return {
        "n": format_count(block.get("n")),
        "tp": format_count(block.get("tp")),
        "fp": format_count(block.get("fp")),
        "fn": format_count(block.get("fn")),
        "tn": format_count(block.get("tn")),
        "precision": format_pct(block.get("precision")),
        "recall": format_pct(block.get("recall")),
        "f1": format_pct(block.get("f1")),
        "accuracy": "tidak berlaku",
        "fp_rate": format_pct(block.get("fp_rate")),
        "fp_rate_ci": f"{format_pct(ci_fp.get('low'))}–{format_pct(ci_fp.get('high'))}",
        "recall_ci": f"{format_pct(ci_recall.get('low'))}–{format_pct(ci_recall.get('high'))}",
    }


def build_benchmark_rows(metrics: dict, realworld: dict, hasil_md: str) -> list[dict]:
    """Kartu benchmark: test set PhiUSIIL dan dua varian uji dunia nyata (Model B)."""
    rows: list[dict] = []
    test = build_test_metrics(hasil_md) or {}
    split = (metrics or {}).get("split") or {}
    rows.append(
        {
            "set": "Test set — PhiUSIIL",
            "n": format_count(split.get("n_test")),
            "tp": format_count(test.get("tp")),
            "fp": format_count(test.get("fp")),
            "fn": format_count(test.get("fn")),
            "tn": format_count(test.get("tn")),
            "precision": format_pct(test.get("precision")),
            "recall": format_pct(test.get("recall")),
            "f1": format_pct(test.get("f1")),
            "accuracy": format_pct(test.get("accuracy")),
            "fp_rate_ci": "tidak berlaku",
            "recall_ci": "tidak berlaku",
        }
    )
    rw = build_realworld_metrics(realworld)
    for label, key in (
        ("Uji dunia nyata — model only", "model_only"),
        (f"Uji dunia nyata — with reputation ({rw['primary_group']})", "primary"),
    ):
        block = rw.get(key) or {}
        if block:
            rows.append({"set": label, **_one_block(block)})
    return rows


def build_roc_shift(model_c: dict, candidate: str = "B_refit") -> dict:
    """ROC-AUC kandidat di test set vs dunia nyata (not_in_allowlist) dari docs/model_c.json."""
    variants = (model_c or {}).get("variants") or {}
    variant = variants.get(candidate) or {}
    test = variant.get("test_grouped") or {}
    rw_variants = (((model_c or {}).get("evaluation") or {}).get("realworld") or {}).get("variants") or {}
    groups = ((rw_variants or {}).get(candidate) or {}).get("groups") or {}
    not_in = groups.get("not_in_allowlist") or groups.get("full") or {}
    test_auc = test.get("roc_auc")
    rw_auc = not_in.get("roc_auc")
    delta = (
        format_delta(float(test_auc) - float(rw_auc))
        if test_auc is not None and rw_auc is not None
        else "tidak berlaku"
    )
    return {
        "candidate": candidate,
        "source": str(variant.get("source") or ""),
        "test_roc_auc": format_pct(test_auc),
        "realworld_roc_auc": format_pct(rw_auc),
        "delta": delta,
    }


def build_candidate_rows(t25: dict, hasil_md: str = "") -> list[dict]:
    """Benar/salah per kandidat; SUSPICIOUS kategori sendiri; split acak vs berkelompok."""
    rows: list[dict] = []
    old = build_test_metrics(hasil_md)
    if old:
        rows.append(
            {
                "split": "acak",
                "candidate": "Model B",
                "n": format_count(old["tp"] + old["fn"] + old["fp"] + old["tn"]),
                "benar": format_count(old["tp"] + old["tn"]),
                "salah": format_count(old["fp"] + old["fn"]),
                "tp": format_count(old["tp"]),
                "fp": format_count(old["fp"]),
                "fn": format_count(old["fn"]),
                "tn": format_count(old["tn"]),
                "precision": format_pct(old["precision"]),
                "recall": format_pct(old["recall"]),
                "f1": format_pct(old["f1"]),
                "suspicious": format_pct(None),
            }
        )
    for name, block in sorted(((t25 or {}).get("test_grouped") or {}).items()):
        if not isinstance(block, dict):
            continue
        tp = int(block.get("tp") or 0)
        fp = int(block.get("fp") or 0)
        fn = int(block.get("fn") or 0)
        tn = int(block.get("tn") or 0)
        suspicious = format_percent_value(block.get("suspicious_pct"))
        if block.get("suspicious_n") is not None:
            suspicious = f"{format_count(block.get('suspicious_n'))} ({suspicious})"
        rows.append(
            {
                "split": "berkelompok",
                "candidate": str(name),
                "n": format_count(block.get("n")),
                "benar": format_count(tp + tn),
                "salah": format_count(fp + fn),
                "tp": format_count(tp),
                "fp": format_count(fp),
                "fn": format_count(fn),
                "tn": format_count(tn),
                "precision": format_pct(block.get("precision")),
                "recall": format_pct(block.get("recall")),
                "f1": format_pct(block.get("f1")),
                "suspicious": suspicious,
            }
        )
    return rows


def build_sensitivity_rows(model_c: dict) -> list[dict]:
    """Sensitivitas URL legit: transform yang diuji dan perubahan skor P(phishing)."""
    rows: list[dict] = []
    sensitivity = ((model_c or {}).get("evaluation") or {}).get("sensitivity") or {}
    for candidate, variant in sorted((sensitivity.get("variants") or {}).items()):
        if not isinstance(variant, dict):
            continue
        for transform, item in sorted((variant.get("variants") or {}).items()):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "candidate": str(candidate),
                    "transform": str(transform),
                    "urls_changed": format_count(item.get("urls_changed")),
                    "mean_delta": format_delta(item.get("mean")),
                    "median_delta": format_delta(item.get("median")),
                    "increased": format_count(item.get("increased")),
                    "decreased": format_count(item.get("decreased")),
                }
            )
    return rows


def build_www_effect(t25: dict) -> dict:
    """Efek normalisasi www. dari docs/t25.json (T25), bukan angka yang diketik manual."""
    effect = (t25 or {}).get("www_normalization_effect") or {}
    return {
        "delta_f1": format_delta(effect.get("delta_f1")),
        "delta_mcc": format_delta(effect.get("delta_mcc")),
        "delta_roc_auc": format_delta(effect.get("delta_roc_auc")),
    }


def build_denylist_rows(denylist: dict) -> list[dict]:
    """Baris ringkasan denylist: snapshot, tumpang tindih, umur, FP, dan vonis sistem penuh."""
    rows: list[dict] = []
    for snap in (denylist or {}).get("snapshots") or []:
        if isinstance(snap, dict):
            name = str(snap.get("name") or "")
            n = format_count(snap.get("n_urls"))
            rows.append(
                {
                    "kind": "snapshot",
                    "name": name,
                    "n": n,
                    "label": f"Snapshot {name}",
                    "value": f"{n} URL",
                }
            )
    for overlap in (denylist or {}).get("overlap") or []:
        if isinstance(overlap, dict):
            a = str(overlap.get("snapshot_a") or "")
            b = str(overlap.get("snapshot_b") or "")
            n_url = format_count(overlap.get("n_url_overlap"))
            n_host = format_count(overlap.get("n_host_overlap"))
            n_domain = format_count(overlap.get("n_domain_overlap"))
            n_new = format_count(overlap.get("n_new_in_b"))
            hours = format_hours(overlap.get("hours_between_snapshots"))
            rows.append(
                {
                    "kind": "overlap",
                    "snapshot_a": a,
                    "snapshot_b": b,
                    "n_url_overlap": n_url,
                    "n_host_overlap": n_host,
                    "n_domain_overlap": n_domain,
                    "n_new_in_b": n_new,
                    "hours": hours,
                    "label": f"Tumpang tindih {a} → {b}",
                    "value": f"URL {n_url}, host {n_host}, domain {n_domain}, baru {n_new} ({hours} jam)",
                }
            )
    for age in (denylist or {}).get("age_curve") or []:
        if isinstance(age, dict):
            hours = format_hours(age.get("hours_between_snapshots"))
            pct = format_percent_value(age.get("pct_still_present"))
            rows.append(
                {
                    "kind": "age",
                    "hours": hours,
                    "pct_still_present": pct,
                    "label": f"Umur {hours} jam",
                    "value": f"masih ada {pct}",
                }
            )
    fp = (denylist or {}).get("false_positives") or {}
    for group in ("legit_dev", "legit_final"):
        block = fp.get(group) or {}
        tested = format_count(block.get("n_tested"))
        n_fp = format_count(block.get("n_fp"))
        rows.append(
            {
                "kind": "fp",
                "group": group,
                "n_tested": tested,
                "n_fp": n_fp,
                "label": f"False positive {group}",
                "value": f"{n_fp} dari {tested}",
            }
        )
    full = (denylist or {}).get("full_system") or {}
    results = full.get("results") or {}
    for mode in full.get("modes_run") or []:
        for group in ("legit_dev", "legit_final"):
            block = (results.get(str(mode)) or {}).get(group) or {}
            tested = format_count(block.get("n_tested"))
            for verdict in ("PHISHING", "SUSPICIOUS", "LEGITIMATE"):
                n = format_count((block.get("verdicts") or {}).get(verdict))
                rows.append(
                    {
                        "kind": "verdict",
                        "mode": str(mode),
                        "group": group,
                        "verdict": verdict,
                        "n_tested": tested,
                        "n": n,
                        "label": f"{mode} · {group} · {verdict}",
                        "value": f"{n} dari {tested}",
                    }
                )
    return rows


# --- T22b: diagnostik dunia nyata dan keterbatasan ---------------------------
def _realworld_split(t25: dict, split: str) -> dict:
    return (((t25 or {}).get("evaluation") or {}).get("realworld") or {}).get(split) or {}


def build_realworld_panel_data(t25: dict) -> dict:
    """Judul dan baris dev/final; semua angka dibaca dari docs/t25.json."""
    dev, final = _realworld_split(t25, "dev"), _realworld_split(t25, "final")
    rows: list[dict] = []
    for split, block in (("dev", dev), ("final", final)):
        n = format_count(block.get("n"))
        for name, c in sorted((block.get("candidates") or {}).items()):
            if not isinstance(c, dict):
                continue
            ci_s, ci_r = c.get("specificity_ci95") or {}, c.get("recall_ci95") or {}
            rows.append(
                {
                    "set": split,
                    "n": n,
                    "candidate": str(name),
                    "specificity_strict": format_pct(c.get("specificity_strict")),
                    "specificity_ci": f"{format_pct(ci_s.get('low'))}–{format_pct(ci_s.get('high'))}",
                    "recall": format_pct(c.get("recall")),
                    "recall_ci": f"{format_pct(ci_r.get('low'))}–{format_pct(ci_r.get('high'))}",
                    "recall_terjaring": format_pct(c.get("recall_terjaring")),
                    "mcc": format_pct(c.get("mcc")),
                    "suspicious": format_percent_value(c.get("suspicious_pct")),
                }
            )
    return {
        "title": f"Dunia nyata: dev ({format_count(dev.get('n'))} URL) dan final ({format_count(final.get('n'))} URL)",
        "rows": rows,
    }


def _mcc(block: dict) -> float | None:
    value = (block or {}).get("mcc")
    return round(float(value), 4) if value is not None else None


def build_mcc_chart(t25: dict) -> list[dict]:
    """MCC kandidat: test set berkelompok vs dunia nyata dev/final."""
    test = (t25 or {}).get("test_grouped") or {}
    dev = (_realworld_split(t25, "dev").get("candidates") or {})
    final = (_realworld_split(t25, "final").get("candidates") or {})
    return [
        {
            "candidate": name,
            "PhiUSIIL": _mcc(test.get(name)),
            "dev": _mcc(dev.get(name)),
            "final": _mcc(final.get(name)),
        }
        for name in sorted(dev)
    ]


def build_verdict_chart(t25: dict) -> list[dict]:
    """Komposisi vonis pada URL legit: FP = PHISHING, SUSPICIOUS, sisanya LEGITIMATE."""
    rows: list[dict] = []
    for split in ("dev", "final"):
        groups = ((_realworld_split(t25, split).get("groups") or {}).get("all") or {})
        for name, c in sorted(groups.items()):
            if not isinstance(c, dict):
                continue
            fp = int(c.get("fp") or 0)
            suspicious = int(c.get("suspicious_legit_n") or 0)
            rows.append(
                {
                    "candidate": f"{split} · {name}",
                    "PHISHING": fp,
                    "SUSPICIOUS": suspicious,
                    "LEGITIMATE": max(0, int(c.get("tn") or 0) - suspicious),
                }
            )
    return rows


def build_age_chart(denylist: dict) -> dict:
    """Kurva umur entri; pasangan snapshot <1 jam diabaikan karena duplikat."""
    rows: list[dict] = []
    skipped = 0
    for item in (denylist or {}).get("age_curve") or []:
        hours = float(item.get("hours_between_snapshots") or 0)
        if hours < 1:
            skipped += 1
            continue
        rows.append(
            {
                "snapshot": str(item.get("later_snapshot") or item.get("snapshot") or ""),
                "hours": round(hours, 3),
                "still": float(item.get("pct_still_present") or 0),
            }
        )
    for item in (denylist or {}).get("overlap") or []:
        if float(item.get("hours_between_snapshots") or 0) < 1:
            skipped += 1
    return {"rows": rows, "skipped": skipped}


def build_denylist_sentence(denylist: dict) -> str:
    """Satu kalimat ringkasan vonis tanpa denylist, dari docs/denylist.json."""
    results = (((denylist or {}).get("full_system") or {}).get("results") or {})
    block = results.get("denylist_disabled") or {}
    parts = []
    for group in ("legit_dev", "legit_final"):
        item = block.get(group) or {}
        verdicts = item.get("verdicts") or {}
        n = int(item.get("n_tested") or 0)
        legitimate = int(verdicts.get("LEGITIMATE") or 0)
        pct = format_percent_value(legitimate / n * 100) if n else "tidak berlaku"
        parts.append(f"{group}: PHISHING {format_count(verdicts.get('PHISHING'))} dari {format_count(n)}, LEGITIMATE {pct}")
    return "Tanpa denylist, sistem hampir tidak pernah yakin bahwa URL itu legit — " + "; ".join(parts) + "."


def load_limitation_items() -> list[str]:
    """Keterbatasan dibaca dari app/limitations.json, bukan diketik di komponen."""
    try:
        data = json.loads(LIMITATIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data if isinstance(data, list) else (data.get("items") or [])
    return [str(item) for item in items if str(item)]


def build_limitations(model_c: dict) -> list[str]:
    """Daftar keterbatasan dari docs/model_c.json."""
    return [str(item) for item in ((model_c or {}).get("limitations") or []) if str(item)]


# --- State ------------------------------------------------------------------
class EvalState(rx.State):
    """Muat artefak saat halaman dikunjungi (bukan saat compile)."""

    artefak_ok: bool = False
    trained_at: str = ""
    n_train: str = ""
    n_test: str = ""
    n_features_b: str = ""
    best_a: str = ""
    best_b: str = ""
    cv_data: list[list[str]] = []
    cv_chart: list[dict] = []
    fold_chart: list[dict] = []
    split_chart: list[dict] = []
    has_conf: bool = False
    conf_tp: str = ""
    conf_fn: str = ""
    conf_fp: str = ""
    conf_tn: str = ""
    hasil_md: str = ""
    tambahan_ok: bool = False
    benchmark_rows: list[dict] = []
    roc_shift: dict = {}
    candidate_rows: list[dict] = []
    sensitivity_rows: list[dict] = []
    www_effect: dict = {}
    denylist_rows: list[dict] = []
    limitations: list[str] = []
    realworld_title: str = ""
    realworld_rows: list[dict] = []
    mcc_chart: list[dict] = []
    verdict_chart: list[dict] = []
    age_chart: list[dict] = []
    age_skipped: int = 0
    denylist_sentence: str = ""

    def _kosongkan_tambahan(self):
        self.tambahan_ok = False
        self.benchmark_rows = []
        self.roc_shift = {}
        self.candidate_rows = []
        self.sensitivity_rows = []
        self.www_effect = {}
        self.denylist_rows = []
        self.limitations = []
        self.realworld_title = ""
        self.realworld_rows = []
        self.mcc_chart = []
        self.verdict_chart = []
        self.age_chart = []
        self.age_skipped = 0
        self.denylist_sentence = ""

    @rx.var
    def trained_date(self) -> str:
        return self.trained_at[:10]

    @rx.event
    async def load_artifacts(self):
        try:
            metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            hasil = HASIL_PATH.read_text(encoding="utf-8") if HASIL_PATH.exists() else ""
        except Exception:
            self.artefak_ok = False
            self.cv_data = []
            self.hasil_md = ""
            self._kosongkan_tambahan()
            return

        self.artefak_ok = True
        self.trained_at = str(metrics.get("trained_at", ""))
        split = metrics.get("split", {}) or {}
        self.n_train = format_count(split.get("n_train", ""))
        self.n_test = format_count(split.get("n_test", ""))
        self.n_features_b = str((metrics.get("model_b", {}) or {}).get("n_features", ""))
        self.best_a = str(metrics.get("model_a", {}).get("best", ""))
        self.best_b = str(metrics.get("model_b", {}).get("best", ""))
        self.cv_data = build_cv_rows(metrics)
        self.cv_chart = build_cv_chart(metrics)
        self.fold_chart = build_fold_chart(metrics)
        self.split_chart = build_split_chart(split)

        conf = parse_confusion(hasil)
        self.has_conf = conf is not None
        if conf:
            self.conf_tp, self.conf_fn, self.conf_fp, self.conf_tn = (conf[k] for k in ("tp", "fn", "fp", "tn"))
        self.hasil_md = clean_report(hasil)

        extra = (REALWORLD_PATH, MODEL_C_PATH, DENYLIST_PATH, T25_PATH)
        if not all(path.exists() for path in extra):
            self._kosongkan_tambahan()
            return
        try:
            realworld = json.loads(REALWORLD_PATH.read_text(encoding="utf-8"))
            model_c = json.loads(MODEL_C_PATH.read_text(encoding="utf-8"))
            denylist = json.loads(DENYLIST_PATH.read_text(encoding="utf-8"))
            t25 = json.loads(T25_PATH.read_text(encoding="utf-8"))
        except Exception:
            self._kosongkan_tambahan()
            return

        self.benchmark_rows = build_benchmark_rows(metrics, realworld, hasil)
        self.roc_shift = build_roc_shift(model_c)
        self.candidate_rows = build_candidate_rows(t25, hasil)
        self.sensitivity_rows = build_sensitivity_rows(model_c)
        self.www_effect = build_www_effect(t25)
        self.denylist_rows = build_denylist_rows(denylist)
        self.limitations = load_limitation_items() or build_limitations(model_c)
        panel = build_realworld_panel_data(t25)
        self.realworld_title = panel["title"]
        self.realworld_rows = panel["rows"]
        self.mcc_chart = build_mcc_chart(t25)
        self.verdict_chart = build_verdict_chart(t25)
        age = build_age_chart(denylist)
        self.age_chart = age["rows"]
        self.age_skipped = age["skipped"]
        self.denylist_sentence = build_denylist_sentence(denylist)
        self.tambahan_ok = True


# --- Komponen ---------------------------------------------------------------
def stat_card(value, label: str) -> rx.Component:
    return card(
        rx.hstack(
            rx.text(
                value,
                style={"font_size": "1.9rem", "font_weight": "700", "line_height": "1", "text_transform": "uppercase"},
            ),
            muted(label),
            align="end",
            spacing="3",
            wrap="wrap",
        ),
        padding="18px 20px",
    )


GRID = {"stroke": "#444444", "stroke_dasharray": "6 6"}
TOOLTIP_STYLE = {
    "background": t.BLACK,
    "border": f"3px solid {t.WHITE}",
    "border_radius": "0",
    "color": t.TEXT,
}


def cv_bar_chart() -> rx.Component:
    return card(
        card_title("chart-bar", "F1 phishing per model"),
        muted(
            "Rata-rata 5-fold CV. Sumbu dipotong di 0,98–1,00 supaya selisihnya terlihat.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "10px"},
        ),
        rx.recharts.bar_chart(
            rx.recharts.cartesian_grid(**GRID),
            rx.recharts.bar(data_key="Model A", fill=t.ORANGE),
            rx.recharts.bar(data_key="Model B", fill=t.PURPLE),
            rx.recharts.x_axis(data_key="model", stroke=t.MUTED),
            rx.recharts.y_axis(domain=[0.98, 1], stroke=t.MUTED, width=52),
            rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
            rx.recharts.legend(),
            data=EvalState.cv_chart,
            width="100%",
            height=260,
        ),
    )


def fold_line_chart() -> rx.Component:
    return card(
        card_title("activity", "Stabilitas per fold (Model B)"),
        muted(
            "F1 phishing di tiap fold. Garis yang datar berarti model konsisten.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "10px"},
        ),
        rx.recharts.line_chart(
            rx.recharts.cartesian_grid(**GRID),
            rx.recharts.line(data_key="LR", stroke=t.YELLOW, type_="monotone", dot=False),
            rx.recharts.line(data_key="RF", stroke=t.ORANGE, type_="monotone", dot=False),
            rx.recharts.line(data_key="XGB", stroke=t.PURPLE_LIGHT, type_="monotone", dot=False),
            rx.recharts.x_axis(data_key="fold", stroke=t.MUTED),
            rx.recharts.y_axis(domain=[0.985, 1], stroke=t.MUTED, width=52),
            rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
            rx.recharts.legend(),
            data=EvalState.fold_chart,
            width="100%",
            height=260,
        ),
    )


def _conf_cell(value, caption: str, good: bool) -> rx.Component:
    """Benar (TP/TN) = putih; salah (FN/FP) = merah."""
    fg = t.BLACK if good else t.WHITE
    return rx.box(
        rx.text(value, style={"font_size": "1.6rem", "font_weight": "700", "line_height": "1.1", "color": fg}),
        muted(caption, size="1", style={"color": fg}),
        style={
            "background": t.WHITE if good else t.P5_RED,
            "border": f"3px solid {t.WHITE if good else t.P5_RED}",
            "border_radius": "0",
            "padding": "14px",
        },
    )


def _conf_axis(text: str) -> rx.Component:
    return rx.flex(muted(text, size="1"), align="center", justify="center", style={"padding": "4px"})


def confusion_card() -> rx.Component:
    return card(
        card_title("layers", "Confusion matrix (Model B)"),
        muted(
            "Hasil pada data uji, ambang 50%. Putih = prediksi benar, merah = salah.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "14px"},
        ),
        rx.cond(
            EvalState.has_conf,
            rx.grid(
                rx.box(),
                _conf_axis("Prediksi phishing"),
                _conf_axis("Prediksi legit"),
                _conf_axis("Aktual phishing"),
                _conf_cell(EvalState.conf_tp, "Terdeteksi (TP)", True),
                _conf_cell(EvalState.conf_fn, "Lolos (FN)", False),
                _conf_axis("Aktual legit"),
                _conf_cell(EvalState.conf_fp, "Salah tandai (FP)", False),
                _conf_cell(EvalState.conf_tn, "Benar legit (TN)", True),
                columns="110px 1fr 1fr",
                spacing="2",
                width="100%",
            ),
            muted("Jalankan `uv run python src/evaluate.py` untuk membuat laporan test set."),
        ),
    )


def split_card() -> rx.Component:
    return card(
        card_title("database", "Pembagian data"),
        muted(
            "Stratified 80/20, seed 42. Data uji tidak dipakai saat training.",
            size="1",
            style={"margin_top": "6px"},
        ),
        rx.box(
            rx.recharts.pie_chart(
                rx.recharts.pie(
                    data=EvalState.split_chart,
                    data_key="value",
                    name_key="name",
                    inner_radius=58,
                    outer_radius=80,
                    stroke="none",
                ),
                rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
                width="100%",
                height=200,
            ),
            rx.flex(
                rx.text("80 / 20", style={"font_size": "1.3rem", "font_weight": "700"}),
                direction="column",
                align="center",
                justify="center",
                style={"position": "absolute", "inset": "0", "pointer_events": "none"},
            ),
            style={"position": "relative", "width": "100%", "margin_top": "6px"},
        ),
        rx.hstack(
            rx.hstack(
                rx.box(style={"width": "8px", "height": "8px", "border_radius": "0", "background": t.PURPLE}),
                muted("Latih", size="1"),
                align="center",
                spacing="1",
            ),
            rx.hstack(
                rx.box(style={"width": "8px", "height": "8px", "border_radius": "0", "background": t.ORANGE}),
                muted("Uji", size="1"),
                align="center",
                spacing="1",
            ),
            justify="center",
            width="100%",
        ),
    )


def _head(text: str, align: str = "left") -> rx.Component:
    return rx.table.column_header_cell(
        text,
        style={"background": t.PURPLE_DEEP, "color": t.TEXT, "text_align": align, "font_weight": "600"},
    )


def cv_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                _head("Model"),
                _head("Algoritma"),
                _head("F1 phishing (rata-rata CV)", "right"),
                _head("Terbaik", "center"),
            )
        ),
        rx.table.body(
            rx.foreach(
                EvalState.cv_data,
                lambda row: rx.table.row(
                    rx.table.cell(row[0]),
                    rx.table.cell(row[1], style={"font_weight": "600"}),
                    rx.table.cell(
                        row[2],
                        style={"text_align": "right", "font_variant_numeric": "tabular-nums"},
                    ),
                    rx.table.cell(
                        rx.cond(
                            row[3] != "",
                            rx.box(
                                "Terbaik",
                                style={
                                    "display": "inline-block",
                                    "background": t.GRADIENT,
                                    "color": t.WHITE,
                                    "font_size": "0.75rem",
                                    "font_weight": "700",
                                    "padding": "2px 10px",
                                    "border_radius": "0",
                                },
                            ),
                            "",
                        ),
                        style={"text_align": "center"},
                    ),
                    style={"background": rx.cond(row[3] != "", "rgba(230,0,18,0.18)", "transparent")},
                ),
            )
        ),
        width="100%",
        variant="ghost",
    )


REPORT_STYLE = {
    "color": t.TEXT,
    "font_size": "0.92rem",
    "line_height": "1.6",
    "overflow_x": "auto",
    "width": "100%",
    "& h1": {"font_size": "1.4rem", "margin": "0 0 0.75rem"},
    "& h2": {
        "font_size": "1.15rem",
        "margin": "1.6rem 0 0.5rem",
        "padding_left": "0.6rem",
        "border_left": f"4px solid {t.PURPLE}",
    },
    "& h3": {"font_size": "1rem", "margin": "1.2rem 0 0.4rem", "color": t.PURPLE_LIGHT},
    "& table": {"width": "100%", "border_collapse": "collapse", "margin": "0.6rem 0", "font_size": "0.85rem"},
    "& th": {
        "background": t.PURPLE_DEEP,
        "color": t.TEXT,
        "text_align": "left",
        "padding": "0.45rem 0.7rem",
        "white_space": "nowrap",
    },
    "& td": {"padding": "0.45rem 0.7rem", "border_bottom": f"1px solid {t.LINE}", "vertical_align": "top"},
    "& code": {
        "background": t.CARD_2,
        "padding": "0.05rem 0.35rem",
        "border_radius": "0",
        "word_break": "break-all",
        "font_size": "0.85em",
    },
    "& ul": {"padding_left": "1.2rem", "margin": "0.4rem 0"},
}


def report_card() -> rx.Component:
    return card(
        rx.accordion.root(
            rx.accordion.item(
                header="Laporan lengkap test set: metrik, confusion matrix, contoh FP dan FN",
                content=rx.box(rx.markdown(EvalState.hasil_md), style=REPORT_STYLE),
                value="laporan",
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            width="100%",
        ),
        padding="6px 12px",
    )


def _mini_stat(label: str, value) -> rx.Component:
    return rx.vstack(
        muted(label, size="1"),
        rx.text(value, style={"font_size": "1.5rem", "font_weight": "700", "line_height": "1.1"}),
        align="start",
        spacing="1",
    )


def _info_line(*parts) -> rx.Component:
    return rx.hstack(
        *(rx.text(part, size="1", style={"color": t.MUTED}) for part in parts),
        wrap="wrap",
        spacing="1",
        width="100%",
    )


def _cell(value, align: str = "right", color: str | None = None) -> rx.Component:
    style = {"text_align": align, "font_variant_numeric": "tabular-nums"}
    if color:
        style["color"] = color
    return rx.table.cell(value, style=style)


def benchmark_panel() -> rx.Component:
    return card(
        card_title("chart-bar", "Benchmark: tiga set yang berbeda"),
        muted(
            "Test set PhiUSIIL bukan dunia nyata. Dua baris berikut memakai set T18; "
            "interval Wilson 95% ditampilkan apa adanya.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "12px"},
        ),
        rx.vstack(
            rx.foreach(
                EvalState.benchmark_rows,
                lambda row: rx.box(
                    rx.text(row["set"], style={"font_weight": "700", "font_size": "1.05rem"}),
                    rx.grid(
                        _mini_stat("Precision", row["precision"]),
                        _mini_stat("Recall", row["recall"]),
                        _mini_stat("F1", row["f1"]),
                        _mini_stat(
                            "Salah (FP / FN)",
                            rx.hstack(rx.text(row["fp"]), rx.text(" / "), rx.text(row["fn"]), spacing="1"),
                        ),
                        columns={"initial": "2", "md": "4"},
                        spacing="3",
                        width="100%",
                    ),
                    _info_line(
                        "n=",
                        row["n"],
                        "· akurasi",
                        row["accuracy"],
                        "· FP-rate",
                        row["fp_rate"],
                        "· CI FP",
                        row["fp_rate_ci"],
                        "· CI recall",
                        row["recall_ci"],
                    ),
                    width="100%",
                    style={
                        "border_bottom": f"1px solid {t.LINE}",
                        "padding": "10px 0",
                    },
                ),
            ),
            spacing="1",
            width="100%",
        ),
    )


def roc_shift_panel() -> rx.Component:
    return card(
        card_title("activity", "Pergeseran distribusi: ROC-AUC"),
        muted(
            "Peringkat skor hampir sempurna di test set turun tajam pada URL dunia nyata "
            "di luar allowlist. Ini pergeseran distribusi, bukan sekadar soal ambang.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "12px"},
        ),
        rx.grid(
            _mini_stat("Test set berkelompok", EvalState.roc_shift["test_roc_auc"]),
            _mini_stat("Dunia nyata (not_in_allowlist)", EvalState.roc_shift["realworld_roc_auc"]),
            _mini_stat("Selisih", EvalState.roc_shift["delta"]),
            columns={"initial": "1", "sm": "3"},
            spacing="3",
            width="100%",
        ),
        _info_line("Kandidat", EvalState.roc_shift["candidate"], "· sumber docs/model_c.json"),
    )


def candidate_panel() -> rx.Component:
    return card(
        card_title("layers", "Kandidat T25: benar, salah, dan SUSPICIOUS"),
        muted(
            "Benar = TP+TN; salah = FP+FN; SUSPICIOUS bukan salah. Split 'acak' berasal dari "
            "hasil_evaluasi.md, 'berkelompok' dari T25.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "12px"},
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        _head("Split"),
                        _head("Kandidat"),
                        _head("n", "right"),
                        _head("Benar", "right"),
                        _head("Salah", "right"),
                        _head("TP", "right"),
                        _head("FP", "right"),
                        _head("FN", "right"),
                        _head("TN", "right"),
                        _head("SUSPICIOUS", "right"),
                        _head("F1", "right"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        EvalState.candidate_rows,
                        lambda row: rx.table.row(
                            _cell(row["split"], "left"),
                            _cell(row["candidate"], "left"),
                            _cell(row["n"]),
                            _cell(row["benar"]),
                            _cell(row["salah"]),
                            _cell(row["tp"]),
                            _cell(row["fp"]),
                            _cell(row["fn"]),
                            _cell(row["tn"]),
                            _cell(row["suspicious"], color=t.YELLOW),
                            _cell(row["f1"]),
                        ),
                    )
                ),
                width="100%",
                variant="ghost",
            ),
            style={"overflow_x": "auto", "width": "100%"},
        ),
    )


def realworld_panel() -> rx.Component:
    return card(
        card_title("globe", EvalState.realworld_title),
        muted(
            "Spesifisitas ketat = URL legit yang benar-benar diterima; MCC dan recall memakai "
            "phishing sebagai kelas positif. SUSPICIOUS dilaporkan sendiri, bukan dimasukkan salah.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "12px"},
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        _head("Set"),
                        _head("Kandidat"),
                        _head("n", "right"),
                        _head("Spesif. ketat (%)", "right"),
                        _head("CI spesif. (%)", "right"),
                        _head("Recall (%)", "right"),
                        _head("CI recall (%)", "right"),
                        _head("Recall terjaring (%)", "right"),
                        _head("MCC", "right"),
                        _head("SUSPICIOUS (%)", "right"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        EvalState.realworld_rows,
                        lambda row: rx.table.row(
                            _cell(row["set"], "left"),
                            _cell(row["candidate"], "left"),
                            _cell(row["n"]),
                            _cell(row["specificity_strict"]),
                            _cell(row["specificity_ci"]),
                            _cell(row["recall"]),
                            _cell(row["recall_ci"]),
                            _cell(row["recall_terjaring"]),
                            _cell(row["mcc"]),
                            _cell(row["suspicious"]),
                        ),
                    )
                ),
                width="100%",
                variant="ghost",
            ),
            style={"overflow_x": "auto", "width": "100%"},
        ),
        muted("Interval kepercayaan Wilson 95%, dibaca apa adanya dari docs/t25.json.", size="1"),
    )


def mcc_shift_panel() -> rx.Component:
    return card(
        card_title("chart-bar", "MCC turun dari PhiUSIIL ke dunia nyata"),
        muted(
            "MCC kandidat yang sama pada test set berkelompok dan pada dua set dunia nyata. "
            "Sumbu dibatasi -0,1 sampai 1 supaya selisihnya terlihat; 0 berarti tidak lebih baik dari tebakan acak.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "10px"},
        ),
        rx.recharts.bar_chart(
            rx.recharts.cartesian_grid(**GRID),
            rx.recharts.bar(data_key="PhiUSIIL", fill=t.ORANGE),
            rx.recharts.bar(data_key="dev", fill=t.PURPLE),
            rx.recharts.bar(data_key="final", fill=t.PURPLE_LIGHT),
            rx.recharts.x_axis(data_key="candidate", stroke=t.MUTED),
            rx.recharts.y_axis(domain=[-0.1, 1], stroke=t.MUTED, width=52),
            rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
            rx.recharts.legend(),
            data=EvalState.mcc_chart,
            width="100%",
            height=280,
        ),
    )


def verdict_panel() -> rx.Component:
    return card(
        card_title("layers", "Sistem jarang yakin bahwa URL itu legit"),
        muted(
            "Komposisi vonis pada URL legit, per kandidat dan per set. Merah = salah dianggap "
            "phishing, kuning = SUSPICIOUS, hijau = benar diterima.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "10px"},
        ),
        rx.recharts.bar_chart(
            rx.recharts.cartesian_grid(**GRID),
            rx.recharts.bar(data_key="PHISHING", stack_id="1", fill=t.RED),
            rx.recharts.bar(data_key="SUSPICIOUS", stack_id="1", fill=t.YELLOW),
            rx.recharts.bar(data_key="LEGITIMATE", stack_id="1", fill=t.GREEN),
            rx.recharts.x_axis(data_key="candidate", stroke=t.MUTED, height=60),
            rx.recharts.y_axis(stroke=t.MUTED, width=52),
            rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
            rx.recharts.legend(),
            data=EvalState.verdict_chart,
            width="100%",
            height=300,
        ),
    )


def tested_panel() -> rx.Component:
    return card(
        card_title("search", "Sudah diuji, bukan penjelasan tunggal"),
        muted(
            "Delta skor P(phishing) pada URL legit dari docs/model_c.json; "
            "efek normalisasi www. dari docs/t25.json.",
            size="1",
            style={"margin_top": "6px", "margin_bottom": "12px"},
        ),
        rx.grid(
            _mini_stat("Δ F1 www.", EvalState.www_effect["delta_f1"]),
            _mini_stat("Δ MCC www.", EvalState.www_effect["delta_mcc"]),
            _mini_stat("Δ ROC-AUC www.", EvalState.www_effect["delta_roc_auc"]),
            columns={"initial": "1", "sm": "3"},
            spacing="3",
            width="100%",
        ),
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        _head("Kandidat"),
                        _head("Transformasi"),
                        _head("URL berubah", "right"),
                        _head("Δ rata-rata", "right"),
                        _head("Δ median", "right"),
                        _head("Naik", "right"),
                        _head("Turun", "right"),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        EvalState.sensitivity_rows,
                        lambda row: rx.table.row(
                            _cell(row["candidate"], "left"),
                            _cell(row["transform"], "left"),
                            _cell(row["urls_changed"]),
                            _cell(row["mean_delta"]),
                            _cell(row["median_delta"]),
                            _cell(row["increased"]),
                            _cell(row["decreased"]),
                        ),
                    )
                ),
                width="100%",
                variant="ghost",
            ),
            style={"overflow_x": "auto", "width": "100%", "margin_top": "14px"},
        ),
    )


def denylist_panel() -> rx.Component:
    return card(
        card_title("shield", "Denylist: umur entri"),
        muted(EvalState.denylist_sentence, size="1", style={"margin_top": "6px", "margin_bottom": "12px"}),
        rx.recharts.line_chart(
            rx.recharts.cartesian_grid(**GRID),
            rx.recharts.line(data_key="still", stroke=t.PURPLE, type_="monotone", dot=True),
            rx.recharts.x_axis(data_key="hours", stroke=t.MUTED, width=70),
            rx.recharts.y_axis(stroke=t.MUTED, width=52),
            rx.recharts.graphing_tooltip(content_style=TOOLTIP_STYLE),
            data=EvalState.age_chart,
            width="100%",
            height=260,
        ),
        muted(
            "Sumbu x = selisih jam antarsnapshot, sumbu y = persentase entri yang masih ada. "
            "Pasangan snapshot dengan selisih <1 jam dilewati karena duplikat, bukan perubahan umur.",
            size="1",
        ),
        rx.hstack(
            muted("Pasangan dilewati:", size="1"),
            rx.text(EvalState.age_skipped, size="1", style={"color": t.MUTED, "font_weight": "700"}),
            spacing="1",
        ),
    )


def limitations_panel() -> rx.Component:
    return card(
        card_title("triangle-alert", "Keterbatasan yang jujur"),
        muted("Dibaca langsung dari app/limitations.json.", size="1", style={"margin_top": "6px", "margin_bottom": "12px"}),
        rx.vstack(
            rx.foreach(
                EvalState.limitations,
                lambda item: rx.hstack(
                    rx.text("•", style={"color": t.P5_RED, "font_weight": "700"}),
                    rx.text(item, size="1"),
                    align="start",
                    spacing="2",
                    width="100%",
                ),
            ),
            spacing="2",
            width="100%",
        ),
    )


def loaded_view() -> rx.Component:
    return rx.vstack(
        rx.callout(
            "Halaman ini membedakan test set PhiUSIIL dan uji dunia nyata, sebelum dan "
            "sesudah lapisan reputasi. Semua angka dibaca dari artefak evaluasi, bukan diketik manual.",
            icon="info",
            color_scheme="blue",
            style={"width": "100%"},
        ),
        rx.grid(
            stat_card("Model B + Model C + aturan", "Model di aplikasi"),
            stat_card(EvalState.n_features_b, "Fitur Model B"),
            stat_card(EvalState.n_train, "Data latih"),
            stat_card(EvalState.n_test, "Data uji"),
            columns={"initial": "1", "sm": "2", "lg": "4"},
            spacing="3",
            width="100%",
        ),
        rx.grid(
            cv_bar_chart(),
            fold_line_chart(),
            columns={"initial": "1", "lg": "2"},
            spacing="4",
            width="100%",
        ),
        rx.grid(
            confusion_card(),
            split_card(),
            columns={"initial": "1", "lg": "2"},
            spacing="4",
            width="100%",
        ),
        card(
            card_title("layers", "Ringkasan validasi silang"),
            muted(
                "5-fold CV pada data latih. Model terbaik dipilih dari rata-rata F1 kelas phishing.",
                size="1",
                style={"margin_top": "6px", "margin_bottom": "12px"},
            ),
            cv_table(),
        ),
        report_card(),
        rx.cond(
            EvalState.tambahan_ok,
            rx.vstack(
                benchmark_panel(),
                realworld_panel(),
                mcc_shift_panel(),
                roc_shift_panel(),
                candidate_panel(),
                verdict_panel(),
                tested_panel(),
                denylist_panel(),
                limitations_panel(),
                spacing="4",
                width="100%",
            ),
            muted(
                "Artefak diagnostik belum ada. Jalankan skrip evaluasi v2 agar "
                "docs/realworld.json, docs/model_c.json, docs/t25.json, dan docs/denylist.json tersedia."
            ),
        ),
        rx.hstack(
            muted("Dilatih pada", size="1"),
            muted(EvalState.trained_date, size="1"),
            spacing="1",
        ),
        spacing="4",
        width="100%",
        align="stretch",
    )


def missing_view() -> rx.Component:
    return rx.callout(
        "Artefak belum ada. Jalankan `uv run python src/train.py` dan "
        "`uv run python src/evaluate.py` dulu.",
        icon="triangle-alert",
        color_scheme="red",
        style={"width": "100%"},
    )


def evaluasi() -> rx.Component:
    return page_shell(
        rx.vstack(
            rx.vstack(
                rx.heading(
                    "Evaluasi model",
                    as_="h1",
                    style={
                        "font_family": t.DISPLAY_FONT,
                        "text_transform": "uppercase",
                        "font_weight": "400",
                        "font_size": "clamp(2rem, 5vw, 3.2rem)",
                        "line_height": "0.95",
                        "color": t.WHITE,
                        "text_shadow": f"6px 6px 0 {t.BLACK}",
                        "transform": "rotate(-3deg)",
                        "transform_origin": "left",
                        "margin": "8px 0 20px",
                    },
                ),
                muted("Seberapa akurat PhishGuard membedakan URL phishing dari URL legit.", size="3"),
                spacing="1",
                align="start",
            ),
            rx.cond(EvalState.artefak_ok, loaded_view(), missing_view()),
            spacing="5",
            width="100%",
            align="stretch",
        ),
        active="evaluasi",
        subtitle="Hasil training dan pengujian",
    )
