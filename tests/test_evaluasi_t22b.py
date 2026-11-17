"""Kontrak panel diagnostik T22b: angka, satuan, dan kategori mengikuti artefak."""

from app.pages.evaluasi import (
    build_age_chart,
    build_denylist_sentence,
    build_mcc_chart,
    build_realworld_panel_data,
    build_verdict_chart,
    format_delta,
    format_hours,
    format_percent_value,
    format_pct,
    load_limitation_items,
)


def test_format_helpers_add_units_and_plain_sentinel():
    assert format_pct(0.1234) == "12.34%"
    assert format_delta(0.0123) == "+1.23%"
    assert format_percent_value(12.34) == "12.34%"
    assert format_hours(9.61) == "9.61 jam"
    assert format_pct(None) == "tidak berlaku"
    assert format_percent_value("") == "tidak berlaku"
    assert format_hours(None) == "tidak berlaku"


def test_realworld_panel_title_and_rows_follow_t25_numbers():
    block = {
        "n": 253,
        "candidates": {
            "consensus": {
                "n": 253,
                "specificity_strict": 0.0,
                "specificity_ci95": {"low": 0.0, "high": 0.05},
                "recall": 0.98,
                "recall_ci95": {"low": 0.94, "high": 0.99},
                "recall_terjaring": 1.0,
                "mcc": 0.3083,
                "suspicious_pct": 9.49,
            }
        },
    }
    t25 = {"evaluation": {"realworld": {"dev": block, "final": {"n": 184, "candidates": {}}}}}
    panel = build_realworld_panel_data(t25)
    assert panel["title"] == "Dunia nyata: dev (253 URL) dan final (184 URL)"
    assert len(panel["rows"]) == 1
    row = panel["rows"][0]
    assert row["set"] == "dev"
    assert row["specificity_strict"] == "0.00%"
    assert row["specificity_ci"] == "0.00%–5.00%"
    assert row["recall_ci"] == "94.00%–99.00%"
    assert row["recall_terjaring"] == "100.00%"
    assert row["mcc"] == "30.83%"
    assert row["suspicious"] == "9.49%"


def test_mcc_chart_compares_phiusiil_with_dev_and_final():
    t25 = {
        "test_grouped": {"consensus": {"mcc": 0.7487}},
        "evaluation": {
            "realworld": {
                "dev": {"candidates": {"consensus": {"mcc": 0.3083}}},
                "final": {"candidates": {"consensus": {"mcc": 0.2986}}},
            }
        },
    }
    assert build_mcc_chart(t25) == [
        {"candidate": "consensus", "PhiUSIIL": 0.7487, "dev": 0.3083, "final": 0.2986}
    ]


def test_verdict_chart_keeps_suspicious_out_of_legitimate():
    t25 = {
        "evaluation": {
            "realworld": {
                "dev": {"groups": {"all": {"consensus": {"fp": 2, "tn": 7, "suspicious_legit_n": 3}}}},
                "final": {"groups": {"all": {"consensus": {"fp": 1, "tn": 4}}}},
            }
        }
    }
    assert build_verdict_chart(t25) == [
        {"candidate": "dev · consensus", "PHISHING": 2, "SUSPICIOUS": 3, "LEGITIMATE": 4},
        {"candidate": "final · consensus", "PHISHING": 1, "SUSPICIOUS": 0, "LEGITIMATE": 4},
    ]


def test_age_chart_skips_snapshots_closer_than_one_hour():
    denylist = {
        "age_curve": [
            {"hours_between_snapshots": 0.5, "pct_still_present": 0.2},
            {"snapshot": "a", "later_snapshot": "b", "hours_between_snapshots": 9.61, "pct_still_present": 0.33},
        ],
        "overlap": [
            {"hours_between_snapshots": 0.003},
            {"hours_between_snapshots": 9.61},
        ],
    }
    got = build_age_chart(denylist)
    assert got["skipped"] == 2
    assert got["rows"] == [{"snapshot": "b", "hours": 9.61, "still": 0.33}]


def test_denylist_sentence_uses_disabled_mode_from_artifact():
    denylist = {
        "full_system": {
            "results": {
                "denylist_disabled": {
                    "legit_dev": {"n_tested": 103, "verdicts": {"PHISHING": 0, "LEGITIMATE": 2}},
                    "legit_final": {"n_tested": 34, "verdicts": {"PHISHING": 0, "LEGITIMATE": 5}},
                }
            }
        }
    }
    sentence = build_denylist_sentence(denylist)
    assert sentence.startswith("Tanpa denylist")
    assert "0 dari 103" in sentence
    assert "0 dari 34" in sentence
    assert "1.94%" in sentence
    assert sentence.endswith(".")


def test_limitation_items_come_from_committed_json_file():
    items = load_limitation_items()
    assert len(items) == 6
    joined = " ".join(items)
    for phrase in ("61 domain", "crawl terbatas", "34 URL", "satu sumber", "Tanpa denylist", "Model A"):
        assert phrase in joined
