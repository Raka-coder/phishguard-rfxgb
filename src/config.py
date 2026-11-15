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

MODEL_B_PATH = ROOT / "src" / "model.pkl"
MODEL_A_PATH = ROOT / "src" / "model_full.pkl"
TLD_PROBS_PATH = ROOT / "src" / "tld_probs.json"
METRICS_PATH = DOCS_DIR / "metrics.json"
STATS_PATH = DOCS_DIR / "stats.json"

CV_FOLDS = 5
N_ESTIMATORS_RF = 300
N_ESTIMATORS_XGB = 400
LR_MAX_ITER = 2000

# Model A: semua kolom numerik dataset (tanpa label + kolom teks URL/Domain/TLD/Title).
# Diverifikasi saat training: kolom numerik Parquet harus sama persis dengan daftar ini.
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
# Dikecualikan: URLSimilarityIndex/URLCharProb (statistik korpus), IsUnresolvableHost (butuh DNS),
# CharContinuationRate (definisi dataset tidak reproducible — dibuang atas keputusan owner).
# TLDLegitimateProb dihitung dari lookup TLD hasil training (src/tld_probs.json).
URL_FEATURES = [
    "URLLength", "DomainLength", "TLDLength", "NoOfSubDomain", "IsDomainIP", "IsHTTPS",
    "NoOfLettersInURL", "LetterRatioInURL", "NoOfDegitsInURL", "DegitRatioInURL",
    "NoOfEqualsInURL", "NoOfQMarkInURL", "NoOfAmpersandInURL", "NoOfOtherSpecialCharsInURL",
    "SpacialCharRatioInURL", "HasObfuscation", "NoOfObfuscatedChar", "ObfuscationRatio",
    "TLDLegitimateProb",
]
