"""Kontrak T18/T18b: set uji dunia nyata, metrik, breakdown, dan error lokal."""

import csv
import json

from scripts.build_realworld_set import build_rows, read_legit, write_csv
from scripts.eval_realworld import (
    _ERROR_FIELDS,
    evaluate,
    metrics,
    wilson_interval,
    write_errors,
    write_json,
)


def _rows() -> list[dict[str, str]]:
    collected = "2026-11-17T00:00:00+00:00"
    return [
        {"url": "http://192.168.0.1/paypal-login-verify.xyz", "label": "0", "source": "openphish", "collected_at": collected},
        {"url": "https://badsite.xyz/login", "label": "0", "source": "openphish", "collected_at": collected},
        {"url": "http://evil.example/verify", "label": "0", "source": "openphish", "collected_at": collected},
        {"url": "https://www.bbc.com", "label": "1", "source": "manual", "collected_at": collected},
        {"url": "https://github.com/Raka-coder/phishguard-rfxgb", "label": "1", "source": "manual", "collected_at": collected},
        {"url": "bukan-url", "label": "0", "source": "openphish", "collected_at": collected},
    ]


def test_metrics_confusion_matrix_and_extended_metrics():
    y_true = [0, 0, 0, 1, 1, 1]
    y_pred = [0, 1, 0, 0, 1, 1]
    result = metrics(y_true, y_pred)
    assert (result["tp"], result["fn"], result["fp"], result["tn"]) == (2, 1, 1, 2)
    assert result["precision"] == 0.6667
    assert result["recall"] == 0.6667
    assert result["f1"] == 0.6667
    assert result["specificity"] == 0.6667
    assert result["balanced_accuracy"] == 0.6667
    assert result["mcc"] == 0.3333
    assert result["fp_rate"] == 0.3333
    assert result["predicted_phishing_pct"] == 50.0
    assert result["fp_rate_ci95"]["low"] < result["fp_rate"] < result["fp_rate_ci95"]["high"]
    assert result["recall_ci95"]["low"] < result["recall"] < result["recall_ci95"]["high"]


def test_wilson_interval_edge_cases():
    assert wilson_interval(0, 0) is None
    zero = wilson_interval(0, 10)
    assert zero is not None and zero["low"] == 0.0 and 0 < zero["high"] < 1
    full = wilson_interval(10, 10)
    assert full is not None and full["high"] == 1.0 and 0 < full["low"] < 1


def test_metrics_undefined_when_no_positive_prediction():
    result = metrics([0, 1], [1, 1])
    assert result["precision"] is None
    assert result["recall"] == 0.0
    assert result["specificity"] == 1.0
    assert result["balanced_accuracy"] == 0.5
    assert result["mcc"] is None
    assert result["predicted_phishing_pct"] == 0.0


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


def test_evaluate_breakdown_balanced_and_errors(tmp_path):
    rows = _rows()
    csv_path = tmp_path / "urls.csv"
    write_csv(rows, csv_path)
    data, errors = evaluate(rows, csv_path)

    assert data["dataset"]["n_total"] == 6
    assert data["dataset"]["n_evaluated"] == 5
    assert data["dataset"]["n_skipped_invalid"] == 1
    assert data["dataset"]["sources"] == {"openphish": 3, "manual": 2}
    assert set(data["variants"]) == {"full", "balanced"}

    full = data["variants"]["full"]
    reputation = full["with_reputation"]
    assert reputation["primary_group"] == "not_in_allowlist"
    assert reputation["primary"] == reputation["by_allowlist"]["not_in_allowlist"]
    assert reputation["by_allowlist"]["in_allowlist"]["n"] == 1
    assert reputation["by_allowlist"]["not_in_allowlist"]["n"] == 4
    assert "allowlist" in reputation["by_decision_source"]
    assert reputation["by_decision_source"]["uncertainty"]["n"] == 0
    assert reputation["all"]["suspicious"] >= 0
    assert full["model_only"]["n"] == 5

    balanced = data["variants"]["balanced"]
    assert balanced["available"] is True
    assert balanced["seed"] == 42
    assert balanced["n_per_class"] == 2
    assert balanced["equal_classes"] is True
    assert balanced["model_only"]["n"] == 4

    assert len(errors) == (
        full["model_only"]["fp"]
        + full["model_only"]["fn"]
        + reputation["all"]["fp"]
        + reputation["all"]["fn"]
    )

    dumped = json.dumps(data, ensure_ascii=False)
    assert "http" not in dumped  # JSON publik hanya agregat, bukan URL feed

    out = tmp_path / "realworld.json"
    write_json(data, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["dataset"]["n_evaluated"] == 5
    assert "results" not in loaded

    errors_path = tmp_path / "errors.csv"
    write_errors(errors, errors_path)
    with errors_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == _ERROR_FIELDS
        written = list(reader)
    assert len(written) == len(errors)
    assert {row["error_type"] for row in written} <= {"FP", "FN"}
    assert all(row["variant"] in {"model_only", "with_reputation"} for row in written)


def test_suspicious_is_not_phishing():
    from scripts.eval_realworld import binary_from_verdict

    assert binary_from_verdict("PHISHING") == 0
    assert binary_from_verdict("SUSPICIOUS") == 1
    assert binary_from_verdict("LEGITIMATE") == 1
