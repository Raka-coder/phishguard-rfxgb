"""Kontrak baris UI "Jejak keputusan": hasil lapisan -> warna status."""

from app import style as t
from app.app_state import build_trail_rows, display_verdict_label


def test_build_trail_rows_maps_result_to_color():
    rows = build_trail_rows(
        [
            {"layer": "model_b", "result": "tinggi", "detail": "skor tinggi"},
            {"layer": "allowlist", "result": "cocok", "detail": "domain tepercaya"},
            {"layer": "shortener", "result": "tidak cocok", "detail": "bukan shortener"},
            {"layer": "model_c", "result": "tidak tersedia", "detail": "artefak hilang"},
        ]
    )
    assert [row["color"] for row in rows] == [t.RED, t.GREEN, t.MUTED, t.MUTED]
    assert [row["layer"] for row in rows] == ["model_b", "allowlist", "shortener", "model_c"]
    assert all(set(row) == {"layer", "result", "detail", "color"} for row in rows)


def test_build_trail_rows_handles_empty_and_unknown_result():
    assert build_trail_rows([]) == []
    assert build_trail_rows(None) == []
    assert build_trail_rows([{"layer": "x", "result": "baru"}])[0]["color"] == t.MUTED


def test_display_verdict_label_is_neutral_for_suspicious():
    assert display_verdict_label("SUSPICIOUS") == "SUSPICIOUS"
    assert display_verdict_label("PHISHING") == "PHISHING"
    assert display_verdict_label("LEGITIMATE") == "LEGITIMATE"
    assert display_verdict_label("") == ""
