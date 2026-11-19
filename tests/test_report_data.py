"""Kontrak helper produksi data laporan T31 (tanpa memuat model berat)."""

from scripts.categorize_fn import categorize, levenshtein, load_brands, typosquat_brand
from scripts.eval_legit_set import band_counts, load_urls


def test_load_urls_ignores_comments_and_blank_lines(tmp_path):
    path = tmp_path / "urls.txt"
    path.write_text("# komentar\n\nhttps://a.example/x\n  https://b.example/y  \n", encoding="utf-8")
    assert load_urls(path) == ["https://a.example/x", "https://b.example/y"]


def test_band_counts_model_b_and_c():
    records = [
        {"probability": 0.10, "probability_c": 0.50},
        {"probability": 0.70, "probability_c": None},
        {"probability": None, "probability_c": None},
    ]
    counts = band_counts(records)
    assert counts["model_b"] == {"tinggi": 1, "sedang": 0, "rendah": 1, "tidak_dinilai": 1}
    assert counts["model_c"] == {"tinggi": 0, "sedang": 1, "rendah": 0, "tidak_dinilai": 2}


def test_levenshtein_and_brand_match():
    assert levenshtein("amznn", "amazon") == 2
    brands = load_brands()
    assert typosquat_brand("https://www.amznn.net", brands) == "amazon"
    assert typosquat_brand("https://www.netflix-vn.com", brands) == "netflix"


def test_categorize_priority_and_fallback():
    brands = load_brands()
    assert categorize("https://bit.ly/abc123", brands) == ("shortener", None)
    assert categorize("https://www.netflix-vn.com", brands) == ("typosquatting", "netflix")
    assert categorize("https://example.com", brands) == ("pendek_bersih", None)
    assert categorize("https://example.com/this/is/a/very/long/path?x=1", brands) == ("lainnya", None)
