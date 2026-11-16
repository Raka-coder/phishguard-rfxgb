"""Kontrak T18: pembangunan set uji dunia nyata dan evaluasi dua jalur."""

import json

from scripts.build_realworld_set import build_rows, read_legit, write_csv
from scripts.eval_realworld import evaluate, metrics, write_json


def test_metrics_confusion_matrix():
    y_true = [0, 0, 0, 1, 1, 1]
    y_pred = [0, 1, 0, 0, 1, 1]
    result = metrics(y_true, y_pred)
    assert (result["tp"], result["fn"], result["fp"], result["tn"]) == (2, 1, 1, 2)
    assert result["precision"] == 0.6667
    assert result["recall"] == 0.6667
    assert result["f1"] == 0.6667


def test_metrics_undefined_when_no_positive_prediction():
    result = metrics([0, 1], [1, 1])
    assert result["precision"] is None
    assert result["recall"] == 0.0


def test_build_rows_filters_dedups_and_labels():
    rows, stats = build_rows(
        [
            "http://evil.example/login",
            "bukan-url",
            "http://evil.example/login",
            "https://badsite.xyz",
        ],
        [
            {"url": "https://github.com/Raka-coder/phishguard-rfxgb", "source": "manual"},
            {"url": " https://www.youtube.com/watch?v=abc ", "source": "manual"},
        ],
        "2026-11-17T00:00:00+00:00",
    )
    assert stats == {"phishing": 2, "legit": 2, "invalid": 1, "duplicate": 1}
    assert [row["label"] for row in rows] == [0, 0, 1, 1]
    assert rows[0] == {
        "url": "http://evil.example/login",
        "label": 0,
        "source": "openphish",
        "collected_at": "2026-11-17T00:00:00+00:00",
    }
    assert rows[3]["url"] == "https://www.youtube.com/watch?v=abc"


def test_read_legit_requires_url_column(tmp_path):
    path = tmp_path / "legit.csv"
    path.write_text("url,source\nhttps://example.com,manual\n", encoding="utf-8")
    assert read_legit(path) == [{"url": "https://example.com", "source": "manual"}]

    bad = tmp_path / "bad.csv"
    bad.write_text("domain\ncontoh.com\n", encoding="utf-8")
    try:
        read_legit(bad)
    except ValueError as exc:
        assert "url" in str(exc)
    else:
        raise AssertionError("kolom url wajib ditolak")


def test_evaluate_writes_json_with_metadata(tmp_path):
    rows = [
        {"url": "http://192.168.0.1/paypal-login-verify.xyz", "label": "0", "source": "openphish", "collected_at": "2026-11-17T00:00:00+00:00"},
        {"url": "https://www.bbc.com", "label": "1", "source": "manual", "collected_at": "2026-11-17T00:00:00+00:00"},
        {"url": "https://github.com/Raka-coder/phishguard-rfxgb", "label": "1", "source": "manual", "collected_at": "2026-11-17T00:00:00+00:00"},
        {"url": "bukan-url", "label": "0", "source": "openphish", "collected_at": "2026-11-17T00:00:00+00:00"},
    ]
    csv_path = tmp_path / "urls.csv"
    write_csv(rows, csv_path)
    data = evaluate(rows, csv_path)

    assert data["dataset"]["n_total"] == 4
    assert data["dataset"]["n_evaluated"] == 3
    assert data["dataset"]["n_skipped_invalid"] == 1
    assert data["dataset"]["sources"] == {"openphish": 1, "manual": 2}
    assert set(data["variants"]) == {"model_only", "with_reputation"}
    assert data["variants"]["with_reputation"]["suspicious"] >= 0
    assert data["dataset"]["path"] == "data/realworld/urls.csv" or data["dataset"]["path"].endswith("urls.csv")

    out = tmp_path / "realworld.json"
    write_json(data, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["dataset"]["n_evaluated"] == 3
    from src.config import THRESHOLD_PHISHING

    assert loaded["thresholds"]["phishing"] == THRESHOLD_PHISHING
    assert "results" not in loaded  # URL feed tidak boleh didistribusikan ulang


def test_suspicious_is_not_phishing():
    from scripts.eval_realworld import binary_from_verdict

    assert binary_from_verdict("PHISHING") == 0
    assert binary_from_verdict("SUSPICIOUS") == 1
    assert binary_from_verdict("LEGITIMATE") == 1
