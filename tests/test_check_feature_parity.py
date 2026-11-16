"""Kontrak T18e: parity 19 fitur dan referensi homepage data latih."""

import json

import numpy as np
import pandas as pd

from scripts.check_feature_parity import (
    _is_plain_homepage,
    homepage_comparison,
    homepage_reference,
    parity_report,
)
from src.config import LABEL_LEGIT, LABEL_PHISH, URL_FEATURES
from src.feature_utils import extract_features


def _frame() -> pd.DataFrame:
    urls = [
        "https://www.example.com",
        "https://bad.example/login",
        "https://www.other.org/",
    ]
    labels = [LABEL_LEGIT, LABEL_PHISH, LABEL_LEGIT]
    computed = [extract_features(url) for url in urls]
    frame = pd.DataFrame({"URL": urls, "label": labels})
    for feature in URL_FEATURES:
        frame[feature] = [values[feature] for values in computed]
    return frame


def test_plain_homepage_predicate():
    assert _is_plain_homepage("https://www.example.com")
    assert _is_plain_homepage("https://www.example.com/")
    assert not _is_plain_homepage("https://www.example.com/path")
    assert not _is_plain_homepage("https://www.example.com/?q=1")


def test_parity_report_exact_when_columns_match():
    frame = _frame()
    report = parity_report(
        frame,
        np.arange(len(frame)),
        {},
        0.5,
        seed=42,
        sample_size=3,
    )
    assert report["sample"]["size"] == 3
    assert report["sample"]["n_legit"] == 2
    assert report["sample"]["n_phishing"] == 1
    for label in ("legit", "phishing"):
        for values in report["by_label"][label]["features"].values():
            assert values["exact_match_pct"] == 100.0
            assert values["mean_abs_diff"] == 0.0
            assert values["max_abs_diff"] == 0.0
    assert report["tld_probability"]["sample_default_fallback_pct"] == 100.0
    assert "http" not in json.dumps(report)


def test_parity_report_detects_mismatch_and_keeps_labels_separate():
    frame = _frame()
    frame.loc[0, "NoOfLettersInURL"] = frame.loc[0, "NoOfLettersInURL"] + 2
    report = parity_report(
        frame,
        np.arange(len(frame)),
        {},
        0.5,
        seed=42,
        sample_size=3,
    )
    legit = report["by_label"]["legit"]["features"]["NoOfLettersInURL"]
    phishing = report["by_label"]["phishing"]["features"]["NoOfLettersInURL"]
    assert legit["exact_match_pct"] == 50.0
    assert legit["mean_abs_diff"] == 1.0
    assert legit["max_abs_diff"] == 2.0
    assert phishing["exact_match_pct"] == 100.0
    assert report["worst_features"]["legit"][0]["feature"] == "NoOfLettersInURL"


def test_homepage_reference_and_comparison():
    frame = _frame()
    reference = homepage_reference(frame, np.arange(len(frame)), {}, 0.5)
    assert reference["n_train_legit_homepages"] == 2
    assert set(reference["median"]) == set(URL_FEATURES)

    comparison = homepage_comparison(["https://www.example.com"], reference, {}, 0.5)
    assert comparison["available"] is True
    assert comparison["n_urls"] == 1
    assert len(comparison["rows"]) == len(URL_FEATURES)
    length_row = next(row for row in comparison["rows"] if row["feature"] == "URLLength")
    assert length_row["delta"] == round(
        length_row["t18_median"] - length_row["train_median"], 6
    )
    assert "http" not in json.dumps(comparison)

    assert homepage_comparison([], reference, {}, 0.5)["available"] is False
