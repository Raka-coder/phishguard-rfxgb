"""Kontrak artefak laporan T32: sumber JSON ada dan grafik benar-benar tergambar."""

from PIL import Image

from scripts.make_figures import DPI, OUT, SOURCES

FIGURE_FILES = [
    "confusion_matrix.png",
    "model_comparison.png",
    "auc_benchmarks.png",
    "path_ablation.png",
    "feature_importance.png",
    "feed_decay.png",
    "decision_composition.png",
    "legit_barat_lokal.png",
    "fn_categories.png",
    "risk_band.png",
]


def test_sources_exist():
    missing = [str(path) for path in SOURCES.values() if not path.exists()]
    assert missing == []


def test_all_figures_rendered():
    for name in FIGURE_FILES:
        path = OUT / name
        assert path.exists(), f"Grafik belum dibuat: {name}. Jalankan `uv run python scripts/make_figures.py`."
        assert path.stat().st_size > 1000, f"Grafik terlalu kecil: {name}"
        with Image.open(path) as image:
            width, height = image.size
            assert width >= 600 and height >= 300, f"Ukuran grafik tak wajar: {name} {width}x{height}"
            dpi = image.info.get("dpi")
            if dpi is not None:
                assert round(dpi[0]) >= DPI, f"DPI di bawah {DPI}: {name} {dpi}"
