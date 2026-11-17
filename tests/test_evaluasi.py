"""Kontrak helper halaman evaluasi: angka harus mengikuti artefak sumbernya."""

from app.pages.evaluasi import (
    build_age_chart,
    build_benchmark_rows,
    build_candidate_rows,
    build_denylist_rows,
    build_denylist_sentence,
    build_limitations,
    build_mcc_chart,
    build_realworld_metrics,
    build_realworld_panel_data,
    build_roc_shift,
    build_sensitivity_rows,
    build_test_metrics,
    build_verdict_chart,
    build_www_effect,
    format_count,
    format_delta,
    format_hours,
    format_percent_value,
    format_pct,
    load_limitation_items,
)


def _markdown(acc, prec, rec, f1, fp, fn, tp, tn):
    return "\n".join(
        [
            "| Model | fitur | accuracy | precision | recall | F1 | FP | FN |",
            "| B | 7 | %s | %s | %s | %s | %s | %s |" % (acc, prec, rec, f1, fp, fn),
            "### Confusion matrix — Model B",
            "TP=%s, FN=%s, FP=%s, TN=%s" % (tp, fn, fp, tn),
        ]
    )


def test_build_test_metrics_follows_markdown_source():
    sources = {"accuracy": "0.9001", "precision": "0.9112", "recall": "0.9223", "f1": "0.9334",
               "fp": "5", "fn": "6", "tp": "7", "tn": "8"}
    got = build_test_metrics(_markdown(*(sources[k] for k in
                                    ("accuracy", "precision", "recall", "f1", "fp", "fn", "tp", "tn"))))
    assert got == {
        "accuracy": float(sources["accuracy"]),
        "precision": float(sources["precision"]),
        "recall": float(sources["recall"]),
        "f1": float(sources["f1"]),
        "fp": int(sources["fp"]),
        "fn": int(sources["fn"]),
        "tp": int(sources["tp"]),
        "tn": int(sources["tn"]),
    }
    assert build_test_metrics("format tidak dikenal") is None


def test_build_test_metrics_accepts_thousands_separator_in_confusion():
    tp, tn = 20067, 26942
    got = build_test_metrics(_markdown("0.1", "0.2", "0.3", "0.4", "1", "2", tp, tn))
    assert got["tp"] == tp
    assert got["tn"] == tn


def test_build_benchmark_rows_maps_test_and_realworld_artifacts():
    md = _markdown("0.1", "0.2", "0.3", "0.4", "1", "2", "3", "4")
    n_test = 99
    low, high = 0.11, 0.22
    realworld = {
        "variants": {
            "full": {
                "model_only": {"n": 10, "precision": 0.5, "fp_rate_ci95": {"low": low, "high": high}},
                "with_reputation": {
                    "primary_group": "di_luar_allowlist",
                    "primary": {"n": 9, "precision": 0.6},
                },
            }
        }
    }
    rows = build_benchmark_rows({"split": {"n_test": n_test}}, realworld, md)

    assert [row["set"] for row in rows] == [
        "Test set — PhiUSIIL",
        "Uji dunia nyata — model only",
        "Uji dunia nyata — with reputation (di_luar_allowlist)",
    ]
    assert rows[0]["n"] == format_count(n_test)
    assert rows[0]["f1"] == format_pct("0.4")
    assert rows[1]["fp_rate_ci"] == f"{format_pct(low)}–{format_pct(high)}"
    assert rows[1]["n"] == format_count(10)
    assert rows[2]["precision"] == format_pct(0.6)
    assert build_realworld_metrics(realworld)["primary_group"] == "di_luar_allowlist"


def test_build_realworld_metrics_falls_back_to_by_allowlist():
    block = {"n": 4}
    realworld = {
        "variants": {
            "full": {
                "with_reputation": {
                    "primary_group": "kelompok_x",
                    "by_allowlist": {"kelompok_x": block},
                }
            }
        }
    }
    assert build_realworld_metrics(realworld)["primary"] == block


def test_build_roc_shift_uses_test_and_realworld_auc():
    test_auc, rw_auc = 0.9123, 0.4567
    model_c = {
        "variants": {"B_refit": {"source": "url", "test_grouped": {"roc_auc": test_auc}}},
        "evaluation": {
            "realworld": {
                "variants": {
                    "B_refit": {"groups": {"not_in_allowlist": {"roc_auc": rw_auc}}}
                }
            }
        },
    }
    got = build_roc_shift(model_c)
    assert got["candidate"] == "B_refit"
    assert got["test_roc_auc"] == format_pct(test_auc)
    assert got["realworld_roc_auc"] == format_pct(rw_auc)
    assert got["delta"] == format_delta(test_auc - rw_auc)


def test_build_candidate_rows_keeps_suspicious_as_its_own_category():
    block = {
        "n": 10, "tp": 4, "fp": 1, "fn": 2, "tn": 3,
        "precision": 0.8, "recall": 0.7, "f1": 0.75,
        "suspicious_pct": 12.34, "suspicious_n": 5,
    }
    row = build_candidate_rows({"test_grouped": {"zeta": block}})[0]
    assert row["candidate"] == "zeta"
    assert row["benar"] == format_count(4 + 3)
    assert row["salah"] == format_count(1 + 2)
    assert row["suspicious"] == f"{format_count(5)} ({format_percent_value(12.34)})"
    assert row["split"] == "berkelompok"
    assert "suspicious_n" not in row


def test_build_candidate_rows_marks_old_test_set_as_acak():
    md = _markdown("0.9", "0.8", "0.7", "0.75", "1", "2", "3", "4")
    rows = build_candidate_rows({}, md)
    assert len(rows) == 1
    assert rows[0]["split"] == "acak"
    assert rows[0]["candidate"] == "Model B"
    assert rows[0]["n"] == format_count(10)
    assert rows[0]["suspicious"] == "tidak berlaku"


def test_diagnostic_helpers_follow_model_c_and_t25():
    mean, d_f1, d_mcc, d_auc = -0.0123, 0.0111, 0.0222, 0.0333
    model_c = {
        "evaluation": {
            "sensitivity": {
                "variants": {
                    "B_refit": {
                        "variants": {
                            "scheme_flip": {
                                "urls_changed": 2,
                                "mean": mean,
                                "median": 0.0,
                                "increased": 1,
                                "decreased": 0,
                            }
                        }
                    }
                }
            }
        },
        "limitations": ["batas satu", "batas dua"],
    }
    t25 = {
        "www_normalization_effect": {
            "delta_f1": d_f1,
            "delta_mcc": d_mcc,
            "delta_roc_auc": d_auc,
        }
    }
    sensitivity = build_sensitivity_rows(model_c)[0]
    assert sensitivity["candidate"] == "B_refit"
    assert sensitivity["transform"] == "scheme_flip"
    assert sensitivity["mean_delta"] == format_delta(mean)
    assert sensitivity["urls_changed"] == format_count(2)

    assert build_www_effect(t25) == {
        "delta_f1": format_delta(d_f1),
        "delta_mcc": format_delta(d_mcc),
        "delta_roc_auc": format_delta(d_auc),
    }
    assert build_limitations(model_c) == ["batas satu", "batas dua"]


def test_build_denylist_rows_summarizes_snapshots_overlap_fp_and_verdicts():
    denylist = {
        "snapshots": [{"name": "feed", "n_urls": 7}],
        "overlap": [
            {
                "snapshot_a": "a", "snapshot_b": "b",
                "n_url_overlap": 1, "n_host_overlap": 2, "n_domain_overlap": 3,
                "n_new_in_b": 4, "hours_between_snapshots": 5.5,
            }
        ],
        "age_curve": [{"hours_between_snapshots": 5.5, "pct_still_present": 12.25}],
        "false_positives": {"legit_final": {"n_tested": 6, "n_fp": 0}},
        "full_system": {
            "modes_run": ["mode_x"],
            "results": {
                "mode_x": {
                    "legit_final": {
                        "n_tested": 6,
                        "verdicts": {"PHISHING": 0, "SUSPICIOUS": 5, "LEGITIMATE": 1},
                    }
                }
            },
        },
    }
    rows = build_denylist_rows(denylist)
    labels = [row["label"] for row in rows]
    assert labels[0] == "Snapshot feed"
    assert rows[0]["value"] == f"{format_count(7)} URL"
    assert any(label.startswith("Tumpang tindih a → b") for label in labels)
    assert any(label.startswith("Umur") for label in labels)
    assert "False positive legit_final" in labels
    assert "mode_x · legit_final · SUSPICIOUS" in labels
    suspicious = next(row for row in rows if row["label"] == "mode_x · legit_final · SUSPICIOUS")
    assert suspicious["value"] == f"{format_count(5)} dari {format_count(6)}"
