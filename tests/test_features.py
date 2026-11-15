"""Kontrak fitur Model B: nama, urutan, tipe, dan perilaku pada input aneh."""

from src.config import URL_FEATURES
from src.feature_utils import extract_features, to_frame


def test_keys_match_contract():
    feats = extract_features("https://www.wikipedia.org")
    assert list(feats) == URL_FEATURES
    assert all(isinstance(v, float) and v is not None for v in feats.values())


def test_ip_host_and_https_flag():
    feats = extract_features("https://192.168.0.1/paypal-login-verify.xyz")
    assert feats["IsDomainIP"] == 1.0
    assert feats["IsHTTPS"] == 1.0
    assert feats["URLLength"] == 43.0


def test_plain_domain_counts():
    feats = extract_features("http://example.com")
    assert feats["IsHTTPS"] == 0.0
    assert feats["DomainLength"] == 11.0
    assert feats["TLDLength"] == 3.0
    assert feats["NoOfSubDomain"] == 0.0


def test_subdomains_are_counted_without_tld():
    assert extract_features("https://www.a.b.example.co.uk").get("NoOfSubDomain") == 4.0


def test_empty_and_garbage_input_returns_numbers():
    for url in ("", "   ", "not a url", "http://"):
        feats = extract_features(url)
        assert feats["URLLength"] >= 0
        assert 0 <= feats["LetterRatioInURL"] <= 1
        assert all(v == v for v in feats.values())  # tidak ada NaN


def test_tld_legit_prob_uses_lookup_with_default():
    probs = {"xyz": 0.2, "com": 0.9}
    assert extract_features("https://a.xyz", probs)["TLDLegitimateProb"] == 0.2
    assert extract_features("https://a.com", probs)["TLDLegitimateProb"] == 0.9
    assert extract_features("https://a.unknown", probs, default_tld_prob=0.55)["TLDLegitimateProb"] == 0.55


def test_tld_legit_prob_default_without_lookup():
    assert extract_features("https://www.wikipedia.org")["TLDLegitimateProb"] == 0.5


def test_to_frame_keeps_column_order():
    frame = to_frame(["https://a.com", "http://b.net/path"])
    assert list(frame.columns) == URL_FEATURES
    assert frame.shape == (2, len(URL_FEATURES))
