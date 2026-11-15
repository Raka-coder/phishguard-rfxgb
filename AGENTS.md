# PhishGuard — agent notes

## State of the repo
T1–T5 are done: `uv` project, locked deps, `.gitignore`, README, `rxconfig.py`, `app/app.py`, `src/config.py`, `src/feature_utils.py` (`extract_features(url, tld_probs, default)` / `to_frame(...)`), `src/train.py` (LR/RF/XGB × model A/B, 5-fold CV on train, writes `src/model.pkl`, `src/model_full.pkl`, `src/tld_probs.json`, `docs/metrics.json`, `docs/stats.json`), `scripts/inspect_data.py`, `scripts/convert_parquet.py`, `tests/test_features.py`. **No evaluate/API/pages yet** — next is T6 (`evaluate.py`, the first code allowed to touch the test set). The four Indonesian docs in `docs/` are the spec; `docs/phishguard-implementation.md` §5 lists the approved work order (**T1–T12, in order, each with a verifiable DoD**).

Model artifacts are gitignored (`src/*.pkl`, `src/tld_probs.json`) — regenerate with `uv run python src/train.py` (full run ≈ 235k rows); `docs/metrics.json` + `docs/stats.json` are committed. `uv run python src/train.py --sample 4000` is the smoke run (≈14 s).

Write user-facing copy, docs and commit messages in Indonesian to match. Remote: `https://github.com/Raka-coder/phishguard-rfxgb`.

Two layout decisions already made (differ from `uv init` defaults): `src/` is a **flat module dir** (`src/config.py`, `src/train.py`, …) with `src/__init__.py`, not an installable package — the packaged `src/phishguard_rfxgb/` and `[project.scripts]`/`[build-system]` were removed so `uv run python src/train.py` and `from src.feature_utils import …` work. Run commands from the repo root.

## Sources of truth
| Question | Read |
|---|---|
| task order, DoD per task, commands, `.gitignore` | `docs/phishguard-implementation.md` |
| API response shape, Reflex state vars, artifact JSON shape | `docs/phishguard-schema.md` |
| layer boundaries, why two models, ports | `docs/phishguard-architecture.md` |
| goals, success targets, risk register (R1–R11) | `docs/phishguard-prd.md` |

When a doc disagrees with the data or a script, trust the data and fix the doc.

## Commands (every Python command goes through `uv run` — never bare `python`/`pip`)
```powershell
uv run python scripts/inspect_data.py        # data check; must print 235795 rows, 1:134850 / 0:100945
uv run python scripts/convert_parquet.py     # CSV -> data/PhiUSIIL.parquet (once per machine)
uv run python src/train.py                   # -> src/model.pkl, src/model_full.pkl, docs/metrics.json
uv run python src/evaluate.py                # -> docs/hasil_evaluasi.md
uv run pytest -q                             # single: uv run pytest -q tests/test_predict.py::test_name
uv run uvicorn api.main:app --port 8001      # API
$env:CI=1; uv run reflex run                 # UI gate: frontend :3000, backend :8000, headless
uv run reflex compile                        # faster UI check when you only need a build
uv sync                                      # after pulling changes to uv.lock
```
Installed versions are newer than the spec assumes — **Reflex 0.11, DuckDB 2.0, scikit-learn 1.9, xgboost 3.2, pandas 3.x**. Confirmed gotchas: DuckDB `Relation` has `.fetchall()`/`.df()` but **no `fetchone()`**; `reflex init` requires `--no-agents` or it overwrites this file; pages are not auto-discovered (see Hard constraints). Test pandas 3 behaviour rather than assuming pandas 2.

`src/` is not an installed package, so `uv run python scripts/foo.py` does **not** put the repo root on `sys.path`. Every file under `scripts/` starts with:

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

Copy that into new scripts, or run them as modules (`uv run python -m scripts.foo`).

## Dataset facts (verified on the CSV in `data/`)
- `data/PhiUSIIL.csv` (54 MB) is the user's own Kaggle extract ([ndarvind/phiusiil-phishing-url-dataset](https://www.kaggle.com/datasets/ndarvind/phiusiil-phishing-url-dataset)), renamed to the name every doc/script expects. Rename on arrival; never branch code on the Kaggle filename. `data/PhiUSIIL.parquet` (15.1 MB) is generated locally. Both are gitignored and absent from the remote — **never commit or upload them** (54 MB + CC BY-NC-SA licence).
- 235,795 rows × 55 columns (54 features + `label`). Label distribution confirmed: `1 = 134850`, `0 = 100945`.
- **`1 = legitimate`, `0 = phishing`** (inverted vs intuition). So `P(phishing) = predict_proba[:, 0]`. Keep the assertion in `tests/test_predict.py` — everything breaks silently without it.
- Never open the CSV in an editor and never `pd.read_csv` it for exploration: DuckDB queries the file in place. `data/` stays out of git (size + CC BY-NC-SA licence).

## Column names: the schema doc's feature list is unreliable
`docs/phishguard-schema.md` §1.2 lists several columns that **do not exist** in the CSV: `NoOfDots`, `NoOfHyphens`, `NoOfAt`, `NoOfSymbols`, `NoOfEqual`, `NoOfQMark`, `NoOfOtherSpecialChars`, `DomainRegisterLength`, `IsUnresolvableHost`. The real names are different, including:

`URLLength, DomainLength, IsDomainIP, TLD, TLDLength, URLSimilarityIndex, CharContinuationRate, TLDLegitimateProb, URLCharProb, NoOfSubDomain, HasObfuscation, NoOfObfuscatedChar, ObfuscationRatio, NoOfLettersInURL, LetterRatioInURL, NoOfDegitsInURL, DegitRatioInURL, NoOfEqualsInURL, NoOfQMarkInURL, NoOfAmpersandInURL, NoOfOtherSpecialCharsInURL, SpacialCharRatioInURL, IsHTTPS, LineOfCode, LargestLineLength, HasTitle, Title, DomainTitleMatchScore, URLTitleMatchScore, HasFavicon, Robots, IsResponsive, NoOfURLRedirect, NoOfSelfRedirect, HasDescription, NoOfPopup, NoOfiFrame, HasExternalFormSubmit, HasSocialNet, HasSubmitButton, HasHiddenFields, HasPasswordField, Bank, Pay, Crypto, HasCopyrightInfo, NoOfImage, NoOfCSS, NoOfJS, NoOfSelfRef, NoOfEmptyRef, NoOfExternalRef, label`

Notes: dataset spelling is `Degit`/`Spacial` (keep it); `equals`, `qmark`, `ampersand` carry the `InURL` suffix. Run `DESCRIBE` before writing `FULL_FEATURES`/`URL_FEATURES`; never type column names from memory. Features that need a page fetch (`LineOfCode`, `NoOfImage`, `HasTitle`, `Bank/Pay/Crypto`, …) are **Model A only** — they must not reach Model B.

## Hard constraints
- **Two models by design:** Model A (`src/model_full.pkl`, 50 numeric dataset columns, report only) vs Model B (`src/model.pkl`, 19 lexical features, served by API/UI). Putting content features in Model B is leakage, not an improvement.
- **Model B is recomputed, not copied.** Train it from `feature_utils.to_frame(df.URL, tld_probs, default)`, never from the dataset's feature columns: `NoOfLettersInURL`, `NoOfOtherSpecialCharsInURL` and `CharContinuationRate` in the CSV cannot be reproduced from a URL string (checked on 2,000 rows), so copying them creates train/serve skew. `CharContinuationRate`, `URLSimilarityIndex`, `URLCharProb`, `IsUnresolvableHost` are deliberately **not** in `URL_FEATURES`; `TLDLegitimateProb` comes from `src/tld_probs.json` (fit on train only, Laplace-smoothed). Changing a definition in `extract_features()` invalidates the model — retrain.
- **Test set is untouched until T6.** T5 selects models with 5-fold `StratifiedKFold` **on train only**; the 20% holdout is split there but never fitted or scored. Do not add evaluation code to `train.py`.
- **F1 is always phishing-as-positive:** `pos_label=LABEL_PHISH` (0) for scoring/CV, and `P(phishing) = predict_proba[:, 0]`.
- **Inline/delegated layout quirk:** `sys.path` bootstrap is only in `scripts/`; `tests/` relies on `[tool.pytest.ini_options] pythonpath = ["."]` in `pyproject.toml`, and `src/*.py` modules import each other as `from src.x import y`, so run from the repo root.
- **No network at inference.** `extract_features()` is a pure string->dict function; no fetching, resolving, or probing the analysed URL (ethics clause). Live test URLs come from PhishTank/Tranco lists as text only.
- **Ports:** FastAPI must be **8001**; 8000 belongs to the Reflex backend.
- **Reflex 0.11:** pages are **not** auto-discovered from `app/pages/` — register each one with `app.add_page(...)` in `app/app.py`. 100% Python: no hand-written JS/HTML/JSX, never edit `.web/`. In the render tree use `rx.cond`/`rx.foreach`/Var operators, never Python `if`/`for` over a Var; mutate state only inside event handlers, derived values via `@rx.var`. Note `reflex init` rewrites `.gitignore` and can overwrite `AGENTS.md` — always pass `--no-agents`.
- **Determinism:** seed 42, stratified split; `uv.lock` always committed.
- Before pushing: `uv run pytest -q`, plus `$env:CI=1; uv run reflex run` if UI changed.
