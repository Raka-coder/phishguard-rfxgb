# PhishGuard — agent notes

## State of the repo
Scaffolding (T1) is done: `uv` project, locked deps, `.gitignore`, README, `rxconfig.py`, `app/app.py`, empty `src/`/`api/`/`scripts/`/`tests/` trees, dataset in `data/`. **No model, no API, no pages yet** — next work is T2 (`scripts/inspect_data.py`) onwards. The four Indonesian docs in `docs/` are the spec; `docs/phishguard-implementation.md` §5 lists the approved work order (**T1–T12, in order, each with a verifiable DoD**).

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
Installed versions are newer than the spec assumes — **Reflex 0.11, scikit-learn 1.9, xgboost 3.2, pandas 3.x**. Check `uv run reflex --version` before copying Reflex patterns from the docs or the web, and test pandas 3 behaviour rather than assuming pandas 2.

## Dataset facts (verified on the CSV in `data/`)
- `data/PhiUSIIL.csv` (54 MB) is the Kaggle ZIP's single CSV, renamed to the name every doc/script expects. The Kaggle extract name varies per member; rename on arrival, don't branch the code on the filename.
- 235,795 rows × 55 columns (54 features + `label`). Label distribution confirmed: `1 = 134850`, `0 = 100945`.
- **`1 = legitimate`, `0 = phishing`** (inverted vs intuition). So `P(phishing) = predict_proba[:, 0]`. Keep the assertion in `tests/test_predict.py` — everything breaks silently without it.
- Never open the CSV in an editor and never `pd.read_csv` it for exploration: DuckDB queries the file in place. `data/` stays out of git (size + CC BY-NC-SA licence).

## Column names: the schema doc's feature list is unreliable
`docs/phishguard-schema.md` §1.2 lists several columns that **do not exist** in the CSV: `NoOfDots`, `NoOfHyphens`, `NoOfAt`, `NoOfSymbols`, `NoOfEqual`, `NoOfQMark`, `NoOfOtherSpecialChars`, `DomainRegisterLength`, `IsUnresolvableHost`. The real names are different, including:

`URLLength, DomainLength, IsDomainIP, TLD, TLDLength, URLSimilarityIndex, CharContinuationRate, TLDLegitimateProb, URLCharProb, NoOfSubDomain, HasObfuscation, NoOfObfuscatedChar, ObfuscationRatio, NoOfLettersInURL, LetterRatioInURL, NoOfDegitsInURL, DegitRatioInURL, NoOfEqualsInURL, NoOfQMarkInURL, NoOfAmpersandInURL, NoOfOtherSpecialCharsInURL, SpacialCharRatioInURL, IsHTTPS, LineOfCode, LargestLineLength, HasTitle, Title, DomainTitleMatchScore, URLTitleMatchScore, HasFavicon, Robots, IsResponsive, NoOfURLRedirect, NoOfSelfRedirect, HasDescription, NoOfPopup, NoOfiFrame, HasExternalFormSubmit, HasSocialNet, HasSubmitButton, HasHiddenFields, HasPasswordField, Bank, Pay, Crypto, HasCopyrightInfo, NoOfImage, NoOfCSS, NoOfJS, NoOfSelfRef, NoOfEmptyRef, NoOfExternalRef, label`

Notes: dataset spelling is `Degit`/`Spacial` (keep it); `equals`, `qmark`, `ampersand` carry the `InURL` suffix. Run `DESCRIBE` before writing `FULL_FEATURES`/`URL_FEATURES`; never type column names from memory. Features that need a page fetch (`LineOfCode`, `NoOfImage`, `HasTitle`, `Bank/Pay/Crypto`, …) are **Model A only** — they must not reach Model B.

## Hard constraints
- **Two models by design:** Model A (`src/model_full.pkl`, 54 features, ~0.97+ F1, report only) vs Model B (`src/model.pkl`, lexical URL-only subset, served by API/UI). Putting content features in Model B is leakage, not an improvement.
- **No network at inference.** `extract_features()` is a pure string->dict function; no fetching, resolving, or probing the analysed URL (ethics clause). Live test URLs come from PhishTank/Tranco lists as text only.
- **Ports:** FastAPI must be **8001**; 8000 belongs to the Reflex backend.
- **Reflex 0.11:** pages are **not** auto-discovered from `app/pages/` — register each one with `app.add_page(...)` in `app/app.py`. 100% Python: no hand-written JS/HTML/JSX, never edit `.web/`. In the render tree use `rx.cond`/`rx.foreach`/Var operators, never Python `if`/`for` over a Var; mutate state only inside event handlers, derived values via `@rx.var`. Note `reflex init` rewrites `.gitignore` and can overwrite `AGENTS.md` — always pass `--no-agents`.
- **Determinism:** seed 42, stratified split; `uv.lock` always committed.
- Before pushing: `uv run pytest -q`, plus `$env:CI=1; uv run reflex run` if UI changed.
