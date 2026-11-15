"""Split bersama (config.make_split): deterministik, stratified, dan ukurannya sesuai."""

import numpy as np
import pandas as pd

from src.config import TEST_SIZE, make_split


def _frame(n_legit: int = 60, n_phish: int = 40) -> pd.DataFrame:
    return pd.DataFrame({"label": [1] * n_legit + [0] * n_phish})


def test_split_is_deterministic():
    df = _frame()
    first_train, first_test = make_split(df)
    second_train, second_test = make_split(df)
    np.testing.assert_array_equal(first_train, second_train)
    np.testing.assert_array_equal(first_test, second_test)


def test_split_sizes_and_stratification():
    df = _frame()
    train_idx, test_idx = make_split(df)
    assert len(train_idx) + len(test_idx) == len(df)
    assert len(test_idx) == round(len(df) * TEST_SIZE)
    assert set(train_idx).isdisjoint(set(test_idx))
    # proporsi phishing di train & test mendekati dataset (stratified)
    assert abs(df["label"].iloc[test_idx].mean() - df["label"].mean()) < 0.02
