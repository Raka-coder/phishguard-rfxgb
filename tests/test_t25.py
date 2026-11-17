"""Kontrak T25: normalisasi www. dan aturan kesepakatan B+C."""

import numpy as np

from scripts.train_t25 import consensus_proba
from src.features_host import host_of


def test_host_of_strip_www():
    assert host_of("https://www.Example.com/x", strip_www=True) == "example.com"
    assert host_of("https://www.Example.com/x") == "www.example.com"
    assert host_of("https://example.com/x", strip_www=True) == "example.com"


def test_consensus_proba_rules():
    p_b = np.array([0.9, 0.1, 0.9, 0.1])
    p_c = np.array([0.8, 0.2, 0.2, 0.8])
    verdict, predicted, suspicious_pct = consensus_proba(p_b, p_c)
    assert list(verdict) == ["PHISHING", "LEGITIMATE", "SUSPICIOUS", "SUSPICIOUS"]
    assert list(predicted) == [0, 1, 1, 1]
    assert suspicious_pct == 50.0
