"""Buat grafik laporan Bab 3-5 dari JSON sumber (T32).

Setiap grafik membaca satu JSON/artefak yang sudah ada; tidak ada angka yang ditulis
keras di skrip ini. Bila sumber hilang, skrip berhenti dengan pesan jelas (tanpa
fallback), supaya laporan tidak pernah memuat angka karangan.

Jalankan dari akar repo:
    uv run python scripts/make_figures.py
"""

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = ROOT / "results" / "data"
OUT = ROOT / "results" / "figures"

DPI = 200
# Warna konsisten dengan vonis aplikasi: merah phishing, kuning tidak terverifikasi,
# hijau legitimate. Abu-abu untuk yang tidak dinilai.
C = {
    "phishing": "#c0392b",
    "suspicious": "#e6a700",
    "legitimate": "#2e7d32",
    "neutral": "#7f8c8d",
    "muted": "#bdc3c7",
    "blue": "#2c6e9b",
}

SOURCES = {
    "metrics": DOCS / "metrics.json",
    "stats": DOCS / "stats.json",
    "realworld": DOCS / "realworld.json",
    "model_c": DOCS / "model_c.json",
    "layer_tests": DOCS / "layer_tests.json",
    "denylist": DOCS / "denylist.json",
    "hasil_evaluasi": DOCS / "hasil_evaluasi.md",
    "legit_set": DATA / "legit_barat_lokal_results.json",
    "fn_categories": DATA / "fn_categories.json",
    "band_distribution": DATA / "band_distribution.json",
}

plt.rcParams.update(
    {
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
    }
)


def num(value: float, digits: int = 2) -> str:
    """Angka desimal dengan koma (gaya Indonesia)."""
    return f"{value:.{digits}f}".replace(".", ",")


def pct(value: float, digits: int = 1) -> str:
    return num(value * 100, digits) + "%"


def load_json(path: Path):
    if not path.exists():
        raise SystemExit(f"Sumber hilang: {path.relative_to(ROOT)}. Jalankan skrip penghasilnya dulu.")
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Sumber hilang: {path.relative_to(ROOT)}.")
    return path.read_text(encoding="utf-8")


def save(fig, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / name
    fig.savefig(target, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}")
    return target


def _first_int_pair(text: str) -> tuple[int, int, int, int]:
    match = re.search(r"TP=(\d+),\s*FN=(\d+),\s*FP=(\d+),\s*TN=(\d+)", text)
    if not match:
        raise SystemExit("Confusion matrix Model B tidak ditemukan di docs/hasil_evaluasi.md.")
    return tuple(int(value) for value in match.groups())


def _test_table(text: str) -> dict[str, dict]:
    """Baris tabel metrik test set untuk Model A dan B dari markdown evaluasi."""
    rows = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("| A |") or stripped.startswith("| B |")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 8:
            raise SystemExit(f"Baris tabel metrik tak terduga: {stripped}")
        rows[cells[0]] = {
            "features": int(cells[1]),
            "accuracy": float(cells[2]),
            "precision": float(cells[3]),
            "recall": float(cells[4]),
            "f1": float(cells[5]),
            "fp": int(cells[6]),
            "fn": int(cells[7]),
        }
    if set(rows) != {"A", "B"}:
        raise SystemExit("Tabel metrik Model A/B tidak lengkap di docs/hasil_evaluasi.md.")
    return rows


def confusion_matrix() -> None:
    tp, fn, fp, tn = _first_int_pair(read_text(SOURCES["hasil_evaluasi"]))
    table = np.array([[tp, fn], [fp, tn]])
    row_pct = table / table.sum(axis=1, keepdims=True) * 100

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.imshow(row_pct, cmap="Reds", vmin=0, vmax=100)
    ax.grid(False)
    labels = ["phishing (0)", "legit (1)"]
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                f"{table[i, j]:,}\n({num(row_pct[i, j])}% baris)".replace(",", "."),
                ha="center",
                va="center",
                fontsize=12,
                color="black" if row_pct[i, j] < 60 else "white",
            )
    ax.set_xticks([0, 1], labels, fontsize=9, rotation=15)
    ax.set_yticks([0, 1], labels, fontsize=9)
    ax.set_xlabel("Prediksi")
    ax.set_ylabel("Label aktual")
    ax.set_title(f"Confusion matrix Model B (test set, n={table.sum():,})".replace(",", "."))
    save(fig, "confusion_matrix.png")


def model_comparison() -> None:
    metrics = load_json(SOURCES["metrics"])
    test = _test_table(read_text(SOURCES["hasil_evaluasi"]))

    fig, (ax_cv, ax_test) = plt.subplots(1, 2, figsize=(11, 4.4))

    folds = np.arange(1, metrics["split"]["cv_folds"] + 1)
    for key, model, color, marker in (
        ("A", "model_a", C["blue"], "o"),
        ("B", "model_b", C["phishing"], "s"),
    ):
        best = metrics[model]["best"]
        values = metrics[model][best]["cv_folds"]
        ax_cv.plot(folds, values, marker=marker, color=color, label=f"Model {key} ({best})")
    ax_cv.set_xticks(folds, [f"lipatan {i}" for i in folds], fontsize=9)
    ax_cv.set_ylim(0.98, 1.001)
    ax_cv.set_ylabel("F1 kelas phishing (CV)")
    ax_cv.set_title("5-fold CV pada data latih")
    ax_cv.legend(frameon=False, fontsize=9)

    names = ["accuracy", "precision", "recall", "f1"]
    x = np.arange(len(names))
    width = 0.38
    for offset, key, color in ((-width / 2, "A", C["blue"]), (width / 2, "B", C["phishing"])):
        values = [test[key][name] for name in names]
        bars = ax_test.bar(x + offset, values, width, color=color, label=f"Model {key}")
        for bar, value in zip(bars, values):
            ax_test.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.002,
                num(value, 4),
                ha="center",
                fontsize=8,
                rotation=90,
                va="bottom",
            )
    ax_test.set_xticks(x, ["accuracy", "precision", "recall", "F1"], fontsize=9)
    ax_test.set_ylim(0.98, 1.012)
    ax_test.set_ylabel("Skor test set")
    ax_test.set_title(f"Metrik test set (n={metrics['split']['n_test']:,})".replace(",", "."))
    ax_test.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)

    fig.tight_layout()
    save(fig, "model_comparison.png")


def auc_benchmarks() -> None:
    rw = load_json(SOURCES["realworld"])["diagnosis"]
    phi = load_json(SOURCES["model_c"])["variants"]["B_refit"]["test_grouped"]["roc_auc"]
    baselines = rw["single_feature_baselines"]["baselines"]

    labels = [
        "PhiUSIIL (split berkelompok)",
        "Dunia nyata: Model B",
        f"Dunia nyata: {next(iter(baselines))} saja",
        f"Dunia nyata: {list(baselines)[1]} saja",
    ]
    values = [phi, rw["auc"]["roc_auc"], baselines["URLLength"]["roc_auc"], baselines["DomainLength"]["roc_auc"]]
    colors = [C["blue"], C["phishing"], C["muted"], C["muted"]]

    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.6)
    for bar, value in zip(bars, values[::-1]):
        ax.text(value + 0.01, bar.get_y() + bar.get_height() / 2, num(value, 4), va="center", fontsize=9)
    ax.set_xlim(0, 1.1)
    ax.set_xlabel("ROC AUC (skor phishing)")
    ax.set_title("ROC AUC: PhiUSIIL vs set dunia nyata")
    save(fig, "auc_benchmarks.png")


def path_ablation() -> None:
    diag = load_json(SOURCES["realworld"])["diagnosis"]
    variants = diag["legit_variants"]
    stripped = diag["phishing_stripped"]
    n_legit = variants["n"]

    fig, (ax_score, ax_auc) = plt.subplots(1, 2, figsize=(9.6, 4.0))

    names = ["URL utuh", "Path/query dibuang"]
    means = [variants["variants"]["original"]["mean"], variants["variants"]["no_path_query"]["mean"]]
    bars = ax_score.bar(names, means, color=[C["phishing"], C["legitimate"]], width=0.55)
    for bar, value in zip(bars, means):
        ax_score.text(bar.get_x() + bar.get_width() / 2, value + 0.02, num(value, 3), ha="center", fontsize=10)
    ax_score.set_ylim(0, 1.05)
    ax_score.set_ylabel("Rerata P(phishing)")
    ax_score.set_title(f"URL legit dunia nyata (n={n_legit})")
    ax_score.tick_params(axis="x", labelsize=9)

    auc_names = ["Skor asli", "Path/query dibuang"]
    auc_values = [stripped["auc_original"]["roc_auc"], stripped["auc_stripped"]["roc_auc"]]
    bars = ax_auc.bar(auc_names, auc_values, color=[C["phishing"], C["legitimate"]], width=0.55)
    for bar, value in zip(bars, auc_values):
        ax_auc.text(bar.get_x() + bar.get_width() / 2, value + 0.015, num(value, 3), ha="center", fontsize=10)
    ax_auc.set_ylim(0, 1.08)
    ax_auc.set_ylabel("ROC AUC")
    ax_auc.set_title(f"Diskriminasi kelompok tanpa allowlist (n={diag['group']['n']})")
    ax_auc.tick_params(axis="x", labelsize=9)

    fig.tight_layout()
    save(fig, "path_ablation.png")


def feature_importance() -> None:
    stats = load_json(SOURCES["stats"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))

    for ax, key, color, title in (
        (axes[0], "model_b", C["phishing"], "Model B (19 fitur URL, dipakai API/UI)"),
        (axes[1], "model_a", C["blue"], "Model A (50 fitur, laporan saja)"),
    ):
        model = stats[key]
        pairs = sorted(zip(model["importances"], model["features"]), reverse=True)[:10]
        values = [pair[0] for pair in pairs][::-1]
        names = [pair[1] for pair in pairs][::-1]
        bars = ax.barh(names, values, color=color, height=0.65)
        for bar, value in zip(bars, values):
            ax.text(value + 0.005, bar.get_y() + bar.get_height() / 2, num(value, 3), va="center", fontsize=8)
        ax.set_xlim(0, max(values) * 1.25)
        ax.set_xlabel("Importance")
        ax.set_title(title, fontsize=10)
        ax.tick_params(axis="y", labelsize=8)

    fig.suptitle("10 fitur paling berpengaruh per model (docs/stats.json)", fontweight="bold")
    fig.tight_layout()
    save(fig, "feature_importance.png")


def feed_decay() -> None:
    data = load_json(SOURCES["denylist"])
    curve = data["age_curve"]
    if not curve:
        raise SystemExit("age_curve kosong di docs/denylist.json.")

    labels = [
        f"{item['later_snapshot'].replace('openphish-', '').replace('.txt', '')}\n({num(item['hours_between_snapshots'])} jam)"
        for item in curve
    ]
    values = [item["pct_still_present"] * 100 for item in curve]

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bars = ax.bar(labels, values, color=C["suspicious"], width=0.5)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.5, f"{num(value, 0)}%", ha="center", fontsize=10)
    ax.axhline(100, color=C["phishing"], linestyle="--", linewidth=1)
    ax.text(len(labels) - 0.5, 101.5, "snapshot awal (0 jam)", ha="right", va="bottom", fontsize=8, color=C["phishing"])
    ax.set_ylim(0, 112)
    ax.set_ylabel("Entri yang masih ada (%)")
    ax.set_title(f"Peluruhan entri denylist (n={data['snapshots'][0]['n_urls']} URL per snapshot)")
    ax.tick_params(axis="x", labelsize=9)
    save(fig, "feed_decay.png")


def decision_composition() -> None:
    data = load_json(SOURCES["layer_tests"])
    fig, (ax_iso, ax_cum) = plt.subplots(1, 2, figsize=(13, 4.8))

    layers = [item["layer"].replace("_", " ") for item in data["isolation"]]
    x = np.arange(len(layers))
    width = 0.38
    for offset, key, color, label in (
        (-width / 2, "phish", C["phishing"], "Sinyal pada phishing"),
        (width / 2, "legit", C["legitimate"], "Sinyal pada legit"),
    ):
        values = [item[key]["rate"] * 100 for item in data["isolation"]]
        bars = ax_iso.bar(x + offset, values, width, color=color, label=label)
        for bar, value in zip(bars, values):
            ax_iso.text(bar.get_x() + bar.get_width() / 2, value + 1.5, num(value, 1), ha="center", fontsize=8)
    ax_iso.set_xticks(x, layers, fontsize=8, rotation=20)
    ax_iso.set_ylim(0, 112)
    ax_iso.set_ylabel("Laju sinyal (%)")
    ax_iso.set_title("Isolasi: sinyal tiap lapisan sendirian\n(L2 = lapisan trust, sinyal berarti diterima sebagai legit)", fontsize=9)
    ax_iso.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2)

    stages = [item["stage"] for item in data["cumulative"]]
    parts = {
        "TP (phishing benar)": ("tp", C["legitimate"]),
        "FN (phishing lolos)": ("fn", C["phishing"]),
        "FP (legit dituduh)": ("fp", C["suspicious"]),
        "TN (legit benar)": ("tn", C["neutral"]),
    }
    bottom = np.zeros(len(stages))
    for label, (key, color) in parts.items():
        values = np.array([item["metrics"][key] for item in data["cumulative"]])
        ax_cum.bar(stages, values, bottom=bottom, color=color, label=label, width=0.65)
        bottom += values
    for index, item in enumerate(data["cumulative"]):
        suspicious = item["suspicious"]
        ax_cum.text(
            index,
            bottom[index] + 8,
            f"SUSP {suspicious['phish']}/{suspicious['legit']}",
            ha="center",
            fontsize=7,
            color=C["neutral"],
        )
    ax_cum.set_xticks(range(len(stages)), stages, fontsize=8, rotation=20)
    ax_cum.set_ylim(0, 420)
    ax_cum.set_ylabel("Jumlah URL")
    ax_cum.set_title(f"Kumulatif: komposisi keputusan (n={data['dataset']['n_total']})", fontsize=10)
    ax_cum.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    save(fig, "decision_composition.png")


def legit_barat_lokal() -> None:
    data = load_json(SOURCES["legit_set"])
    records = data["results"]
    groups: dict[str, dict[str, int]] = {}
    for record in records:
        source = record["decision_source"]
        verdict = "LEGITIMATE" if record["verdict"] == "LEGITIMATE" else "SUSPICIOUS"
        groups.setdefault(source, {"LEGITIMATE": 0, "SUSPICIOUS": 0})[verdict] += 1

    sources = ["allowlist", "model"]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    bottom = np.zeros(len(sources))
    for verdict, color in (("LEGITIMATE", C["legitimate"]), ("SUSPICIOUS", C["suspicious"])):
        values = np.array([groups.get(source, {}).get(verdict, 0) for source in sources])
        bars = ax.bar(sources, values, bottom=bottom, color=color, label=verdict, width=0.5)
        for bar, value, base in zip(bars, values, bottom):
            if value:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    base + value / 2,
                    str(value),
                    ha="center",
                    va="center",
                    fontsize=11,
                    color="white",
                )
        bottom += values
    ax.set_ylabel("Jumlah URL")
    ax.set_title(f"Hasil set legit Barat & Lokal per sumber keputusan (n={data['summary']['n_evaluated']})")
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    save(fig, "legit_barat_lokal.png")


def fn_categories() -> None:
    data = load_json(SOURCES["fn_categories"])
    measured = [item for item in data["categories"] if item["n"] is not None]
    measured.sort(key=lambda item: item["n"], reverse=True)

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    bars = ax.barh([item["id"] for item in measured][::-1], [item["n"] for item in measured][::-1], color=C["phishing"], height=0.6)
    for bar, item in zip(bars, measured[::-1]):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2, str(item["n"]), va="center", fontsize=10)
    ax.set_xlim(0, max(item["n"] for item in measured) * 1.15)
    ax.set_xlabel("Jumlah URL")
    ax.set_title(f"Kategori {data['total_fn']} false negative Model B (test set)")
    missing = [item for item in data["categories"] if item["n"] is None]
    if missing:
        ax.text(
            0.99,
            0.02,
            f"{missing[0]['id']}: MISSING, tidak diukur (tanpa WHOIS/umur domain)",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=8,
            style="italic",
            color=C["neutral"],
        )
    save(fig, "fn_categories.png")


def risk_band() -> None:
    data = load_json(SOURCES["band_distribution"])["sources"]
    rows = [
        ("Dunia nyata", data["realworld"]),
        ("Set legit", data["legit_barat_lokal"]),
    ]
    zones = [("rendah", C["legitimate"]), ("sedang", C["suspicious"]), ("tinggi", C["phishing"]), ("tidak_dinilai", C["muted"])]

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for ax, model_key, title in (
        (axes[0], "model_b", "Model B (URL penuh)"),
        (axes[1], "model_c", "Model C (host-only)"),
    ):
        labels = [f"{name} (n={row['n']})" for name, row in rows]
        left = np.zeros(len(rows))
        for zone, color in zones:
            values = np.array([row["bands"][model_key][zone] for _, row in rows])
            totals = np.array([sum(row["bands"][model_key].values()) for _, row in rows])
            shares = values / totals * 100
            bars = ax.barh(labels, shares, left=left, color=color, label=zone, height=0.55)
            for bar, share, count, start in zip(bars, shares, values, left):
                if share >= 6:
                    ax.text(
                        start + share / 2,
                        bar.get_y() + bar.get_height() / 2,
                        str(count),
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="white" if zone != "tidak_dinilai" else "black",
                    )
            left += shares
        ax.set_xlim(0, 100)
        ax.set_xlabel("Persentase URL (%)")
        ax.set_title(title, fontsize=10)
    axes[0].legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4)
    fig.suptitle("Distribusi zona skor: rendah <0,40, sedang 0,40-0,65, tinggi >=0,65", fontweight="bold")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    save(fig, "risk_band.png")


FIGURES = [
    confusion_matrix,
    model_comparison,
    auc_benchmarks,
    path_ablation,
    feature_importance,
    feed_decay,
    decision_composition,
    legit_barat_lokal,
    fn_categories,
    risk_band,
]


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in SOURCES.values() if not path.exists()]
    if missing:
        raise SystemExit("Sumber hilang: " + ", ".join(missing))
    print(f"Membuat {len(FIGURES)} grafik ke {OUT.relative_to(ROOT)}/")
    for figure in FIGURES:
        figure()
    print("Selesai.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
