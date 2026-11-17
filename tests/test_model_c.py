"""Kontrak T24: fitur host-only, dedup, split berkelompok, dan TLD out-of-fold."""

import numpy as np
import pandas as pd

from scripts.eval_model_c import variant_matrix
from scripts.train_model_c import (
    VARIANTS,
    build_host_tld_probs,
    dedupe_by_url,
    group_split,
    grouped_folds,
    score_block,
    tld_values,
)
from src.config import LABEL_LEGIT, LABEL_PHISH
from src.features_host import (
    HOST_FEATURES,
    extract_host_features,
    host_of,
    tld_of_host,
    to_host_frame,
)


def test_host_features_ignore_scheme_path_query():
    base = extract_host_features("https://example.com")
    assert list(base) == HOST_FEATURES
    for url in ("http://example.com/a?b=1#c", "https://example.com/path"):
        assert extract_host_features(url) == base


def test_www_prefix_changes_host_features():
    plain = extract_host_features("https://example.com")
    www = extract_host_features("https://www.example.com")
    assert www["HostLength"] == plain["HostLength"] + 4
    assert www["NoOfSubDomain"] == 1
    assert www["HostLetterCount"] == plain["HostLetterCount"] + 3


def test_host_and_tld_extraction():
    assert host_of("https://EXAMPLE.com:443/x") == "example.com"
    assert host_of("http://[unclosed/x") == ""
    assert tld_of_host("sub.example.co.uk") == "uk"
    assert tld_of_host("localhost") == ""
    assert extract_host_features("http://192.168.0.1/login")["IsDomainIP"] == 1.0


def test_host_frame_columns_and_tld_fallback():
    frame = to_host_frame(["https://example.com"], {"com": 0.9}, 0.5)
    assert list(frame.columns) == HOST_FEATURES
    assert frame.loc[0, "TLDLegitimateProb"] == 0.9
    assert to_host_frame(["https://unknown.zz"], {"com": 0.9}, 0.5).loc[0, "TLDLegitimateProb"] == 0.5


def test_dedupe_by_url_keeps_first_occurrence():
    frame = pd.DataFrame({"URL": ["a", "b", "a"], "label": [1, 0, 0]})
    out = dedupe_by_url(frame)
    assert out["URL"].tolist() == ["a", "b"]
    assert out["label"].tolist() == [1, 0]


def test_group_split_keeps_hosts_apart():
    hosts = np.array([f"h{i}.com" for i in range(200)])
    train_pos, test_pos = group_split(hosts)
    assert len(train_pos) + len(test_pos) == 200
    assert set(hosts[train_pos]).isdisjoint(hosts[test_pos])
    assert 0.1 < len(test_pos) / 200 < 0.3


def test_grouped_folds_keep_hosts_apart():
    rng = np.random.default_rng(42)
    hosts = np.array([f"host{i}.com" for i in range(200)])
    labels = rng.integers(0, 2, 200)
    train_pos = np.arange(200)
    folds = grouped_folds(train_pos, labels, hosts)
    assert len(folds) == 5
    for fit_rel, val_rel in folds:
        assert set(hosts[fit_rel]).isdisjoint(hosts[val_rel])


def test_host_tld_probs_laplace_and_unseen_tld():
    table, default = build_host_tld_probs(
        np.array(["a.com", "b.com", "c.xyz"]), np.array([1, 1, 0])
    )
    assert table["com"] == round(3 / 4, 6)
    assert table["xyz"] == round(1 / 3, 6)
    assert default == round(3 / 5, 6)
    # TLD yang hanya muncul di fold validasi tidak boleh masuk tabel fold latih.
    values = tld_values(np.array(["onlyval", "com"]), {"com": table["com"]}, default)
    assert values.tolist() == [default, table["com"]]


def test_score_block_uses_phishing_as_positive():
    y_true = np.array([LABEL_PHISH, LABEL_LEGIT, LABEL_PHISH, LABEL_LEGIT])
    good = score_block(y_true, np.array([0.9, 0.1, 0.8, 0.2]))
    assert (good["tp"], good["fp"], good["fn"], good["tn"]) == (2, 0, 0, 2)
    assert good["f1"] == 1.0
    inverted = score_block(y_true, np.array([0.1, 0.9, 0.2, 0.8]))
    assert inverted["f1"] == 0.0


def test_variant_matrices_match_declarations():
    urls = ["https://example.com/a?q=1"]
    base = variant_matrix(urls, VARIANTS["B_refit"], {}, 0.5)
    assert "IsHTTPS" in base.columns and "URLLength" in base.columns
    no_https = variant_matrix(urls, VARIANTS["B_noHTTPS"], {}, 0.5)
    assert "IsHTTPS" not in no_https.columns
    host_only = variant_matrix(urls, VARIANTS["C_host"], {}, 0.5)
    assert list(host_only.columns) == HOST_FEATURES
