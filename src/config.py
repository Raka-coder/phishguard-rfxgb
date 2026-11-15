"""Konstanta proyek: path data, seed, arah label, dan daftar kolom fitur."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_CSV = DATA_DIR / "PhiUSIIL.csv"
DATA_PARQUET = DATA_DIR / "PhiUSIIL.parquet"
DOCS_DIR = ROOT / "docs"

SEED = 42
TEST_SIZE = 0.2
THRESHOLD = 0.5

# PhiUSIIL: 1 = legitimate, 0 = phishing (terbalik dari intuisi) -> P(phishing) = predict_proba[:, 0]
LABEL_LEGIT = 1
LABEL_PHISH = 0

EXPECTED_ROWS = 235_795
EXPECTED_LABEL_COUNTS = {LABEL_PHISH: 100_945, LABEL_LEGIT: 134_850}

IDENTITY_COLUMNS = ["URL", "Domain", "TLD", "Title", "label"]

# Model A: semua kolom numerik dataset (tanpa kolom identitas/teks).
FULL_FEATURES = [
    "URLLength", "DomainLength", "IsDomainIP", "URLSimilarityIndex", "CharContinuationRate",
    "TLDLegitimateProb", "URLCharProb", "TLDLength", "NoOfSubDomain", "HasObfuscation",
    "NoOfObfuscatedChar", "ObfuscationRatio", "NoOfLettersInURL", "LetterRatioInURL",
    "NoOfDegitsInURL", "DegitRatioInURL", "NoOfEqualsInURL", "NoOfQMarkInURL",
    "NoOfAmpersandInURL", "NoOfOtherSpecialCharsInURL", "SpacialCharRatioInURL", "IsHTTPS",
    "LineOfCode", "LargestLineLength", "HasTitle", "DomainTitleMatchScore", "URLTitleMatchScore",
    "HasFavicon", "Robots", "IsResponsive", "NoOfURLRedirect", "NoOfSelfRedirect",
    "HasDescription", "NoOfPopup", "NoOfiFrame", "HasExternalFormSubmit", "HasSocialNet",
    "HasSubmitButton", "HasHiddenFields", "HasPasswordField", "Bank", "Pay", "Crypto",
    "HasCopyrightInfo", "NoOfImage", "NoOfCSS", "NoOfJS", "NoOfSelfRef", "NoOfEmptyRef",
    "NoOfExternalRef",
]

# Model B: dihitung ulang dari string URL oleh feature_utils.extract_features(), bukan disalin dari
# kolom dataset — definisi beberapa kolom dataset (NoOfLettersInURL, CharContinuationRate) tidak bisa
# direproduksi dari string sehingga menyalinnya menimbulkan train/serve skew.
# UrlSimilarityIndex, URLCharProb, TLDLegitimateProb butuh statistik korpus/halaman -> hanya Model A.
URL_FEATURES = [
    "URLLength", "DomainLength", "TLDLength", "NoOfSubDomain", "IsDomainIP", "IsHTTPS",
    "NoOfLettersInURL", "LetterRatioInURL", "NoOfDegitsInURL", "DegitRatioInURL",
    "NoOfEqualsInURL", "NoOfQMarkInURL", "NoOfAmpersandInURL", "NoOfOtherSpecialCharsInURL",
    "SpacialCharRatioInURL", "CharContinuationRate", "HasObfuscation", "NoOfObfuscatedChar",
    "ObfuscationRatio",
]
