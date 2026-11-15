"""Konstanta proyek: path data, seed, dan arah label dataset."""

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
