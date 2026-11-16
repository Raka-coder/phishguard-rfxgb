"""Kontrak T18c: diagnosis AUC, sapuan ambang, kontribusi FP, dan varian URL."""

import json
from urllib.parse import urlsplit

import numpy as np

from scripts.build_realworld_set import write_csv
from scripts.diagnose_realworld import (
    aggregate_contributions,
    auc_block,
    build_diagnosis,
    render_markdown,
    score_distribution,
    threshold_sweep,
    with_www,
    without_path_query,
    write_outputs,
)
from scripts.eval_realworld import score_model_only
from src.config import URL_FEATURES
from src.reputation import is_trusted


def test_url_variants_keep_expected_parts():
    assert without_path_query("https://bbc.com/news?x=1#top") == "https://bbc.com"
    assert without_path_query("https://example.com:8443/a?b=1") == "https://example.com:8443"
    assert with_www("https://bbc.com/news?x=1") == "https://www.bbc.com/news?x=1"
    assert with_www("https://www.bbc.com/news") == "https://www.bbc.com/news"


def test_score_distribution_and_quantiles():
    distribution = score_distribution([0.1, 0.4, 0.8, 0.9])
    assert distribution["n"] == 4
    assert distribution["min"] == 0.1
    assert distribution["max"] == 0.9
    assert distribution["predicted_phishing_pct"] == 50.0
    quantiles = distribution["quantiles"]
    assert list(quantiles) == sorted(quantiles, key=float)
    values = [quantiles[key] for key in quantiles]
    assert values == sorted(values)


def test_auc_block_handles_perfect_and_single_class():
    perfect = auc_block([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1])
    assert perfect["roc_auc"] == 1.0
    assert perfect["pr_auc"] == 1.0
    assert auc_block([1, 1], [0.9, 0.8]) == {"roc_auc": None, "pr_auc": None}


def test_threshold_sweep_covers_range_and_is_monotonic():
    rows = threshold_sweep([0, 0, 1], [0.95, 0.85, 0.90])
    assert len(rows) == 90
    assert rows[0]["threshold"] == 0.1
    assert rows[-1]["threshold"] == 0.99
    recalls = [row["recall"] for row in rows]
    assert recalls == sorted(recalls, reverse=True)
    specificities = [row["specificity"] for row in rows]
    assert specificities == sorted(specificities)


def test_aggregate_contributions_sorts_by_absolute_mean():
    matrix = np.zeros((2, len(URL_FEATURES)), dtype=float)
    matrix[:, 0] = [1.0, 3.0]
    matrix[:, 1] = [-5.0, -5.0]
    top = aggregate_contributions(matrix)
    assert top[0]["feature"] == URL_FEATURES[1]
    assert top[0]["mean_contribution_toward_phishing"] == -5.0
    assert top[1]["feature"] == URL_FEATURES[0]


def test_build_diagnosis_outputs_aggregates_without_urls(tmp_path):
    collected = "2026-11-17T00:00:00+00:00"
    rows = [
        {"url": "http://192.168.0.1/paypal-login-verify.xyz", "label": "0", "source": "openphish", "collected_at": collected},
        {"url": "https://badsite.xyz/login", "label": "0", "source": "openphish", "collected_at": collected},
        {"url": "https://www.bbc.com", "label": "1", "source": "manual", "collected_at": collected},
        {"url": "https://github.com/Raka-coder/phishguard-rfxgb", "label": "1", "source": "manual", "collected_at": collected},
    ]
    csv_path = tmp_path / "urls.csv"
    write_csv(rows, csv_path)
    urls = [row["url"] for row in rows]
    probabilities = [0.95, 0.85, 0.90, 0.99]
    in_allowlist = [is_trusted(urlsplit(url).hostname or "") for url in urls]
    assert in_allowlist == [False, False, False, True]

    payload = build_diagnosis(rows, urls, probabilities, in_allowlist)
    payload["generated_at"] = "2026-11-17T00:00:00+00:00"
    payload["parameters"] = {"threshold": 0.5, "thresholds": [0.1, 0.99]}

    assert payload["group"]["n"] == 3
    assert payload["group"]["n_phishing"] == 2
    assert payload["group"]["n_legit"] == 1
    assert payload["auc"]["roc_auc"] is not None
    assert 0 <= payload["auc"]["roc_auc"] <= 1
    assert len(payload["threshold_sweep"]) == 90
    assert payload["fp_outside_allowlist"]["n"] == 1
    assert len(payload["fp_outside_allowlist"]["top_features"]) > 0
    assert payload["legit_variants"]["n"] == 2
    assert set(payload["legit_variants"]["variants"]) == {"original", "no_path_query", "www_prefix"}

    dumped = json.dumps(payload, ensure_ascii=False)
    assert "http" not in dumped  # tidak ada URL di keluaran publik
    assert "http" not in render_markdown(payload)

    json_path = tmp_path / "realworld.json"
    json_path.write_text('{"variants": {}}\n', encoding="utf-8")
    doc_path = tmp_path / "diagnosis.md"
    write_outputs(payload, json_path, doc_path)
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["diagnosis"]["group"]["n"] == 3
    assert "Sapuan ambang" in doc_path.read_text(encoding="utf-8")


def test_real_model_scores_variants_end_to_end():
    urls = ["https://www.bbc.com", "https://github.com/Raka-coder/phishguard-rfxgb"]
    scores = score_model_only(urls)
    assert len(scores) == 2
    assert all(0 <= score <= 1 for score in scores)
