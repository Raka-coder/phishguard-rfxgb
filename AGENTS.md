# PhishGuard — agent notes

## State of the repo
T1–T14 are done: `uv` project, locked deps (incl. kagglehub 1.0.3, python-dotenv 1.2.4), `.gitignore`, README, `rxconfig.py`, `app/app.py`, `app/app_state.py`, `app/pages/index.py`, `app/pages/evaluasi.py`, `app/style.py`, `src/config.py` (constants + thresholds + load_dotenv), `src/reputation.py` (offline allowlist), `src/trusted_domains.json` (~60 domain), `src/feature_utils.py`, `src/train.py`, `src/evaluate.py`, `src/predict.py` (verdict/decision_source/reason + allowlist + uncertainty band), `api/main.py` (FastAPI :8001, response + verdict fields, load_dotenv), `scripts/*`, `tests/` (54 tests), `tests/fixtures/urls.txt`, `.env.example`. **Tag `v1.0` pending owner.** The four Indonesian docs in `docs/` are the spec. Optional `.env` (gitignored) supported via python-dotenv; `.env.example` committed.

Test-set results (T6): Model B (xgb, 19 feats) accuracy 0.9968, precision 0.9986, recall 0.9940, F1 0.9963, FP 28, FN 122; Model A (rf, 50 feats) all 1.0000. Artifacts are gitignored (`src/*.pkl`, `src/tld_probs.json`) — regenerate with `uv run python src/train.py`; `docs/metrics.json`, `docs/stats.json`, `docs/hasil_evaluasi.md` are committed. `uv run python src/train.py --sample 4000` is the smoke run (≈14 s) and **overwrites the committed metrics/stats**, so back them up or retrain after.

`predict_url` contract: `ValueError` on empty/non-string/non-http(s) scheme/empty host; `_load()` runs before the `perf_counter` timer so first-call `inference_ms` excludes load; missing `stats.json` → `top_features=[]`, missing `model.pkl` → `RuntimeError` telling you to train. Ranking = `importance × |value − mean of predicted class|`, impact direction from the closer class mean, neutral zone 5%. Tests: `tests/test_predict.py` (18).

Reflex UI contract (T9): `app/app_state.py` pakai base var bertipe (`url`, `loading`, `error`, `has_result`, `label_name`, `probability_pct`, `inference_ms`, `top_features: list[dict]`) + `@rx.var` `is_phishing`/`verdict_color`; event handler async `check_url` memakai client module-level `_CLIENT` (`httpx.AsyncClient`) dan `yield` setelah `loading=True`; `set_url` handler eksplisit (Reflex 0.11 tidak auto-generate setter). Halaman `app/pages/index.py` memakai `rx.form.root(on_submit=State.check_url, reset_on_submit=False)` agar Enter di input juga submit (Reflex 0.11 `rx.input` tidak punya `on_key_down`); `rx.cond`/`rx.foreach` saja, tidak ada `if`/`for` Python atas Var. Verifikasi T9: `uv run reflex compile` + `$env:CI=1; uv run reflex run` (frontend :3000, backend :8000) + `curl http://localhost:3000` → 200; klik/Enter tervalidasi via Chrome DevTools (LEGITIMATE 0.08%, PHISHING 100%, error 400 tampil). `PHISHGUARD_API_URL` env override base URL (default http://localhost:8001/check).

EvalState contract (T10): `app/pages/evaluasi.py` memuat `docs/metrics.json` + `docs/hasil_evaluasi.md` di `@rx.event async load_artifacts()` (dipicu `on_load` di `app.add_page`), bukan saat compile — sehingga edit docs tanpa recompile terbaca setelah refresh. Base var: `artefak_ok`, `trained_at`, `n_train`, `n_test`, `best_a`, `best_b`, `cv_data: list[list[str]]`, `hasil_md`. CV table dari `rx.table.root` + `rx.foreach(EvalState.cv_data, lambda row: ...)`. `rx.markdown(EvalState.hasil_md)` dibungkus `rx.box(overflow_x="auto")`. Warna/link dari `app/style.py`. Verifikasi: `/evaluasi` → 200, CV F1 = metrics.json (A RF 1.0000, B XGB 0.9962); run `evaluate.py` ulang → refresh → timestamp berubah.

Download data contract (T13): `scripts/download_data.py` (bootstrap sys.path) unduh via `kagglehub.dataset_download("ndarvind/phiusiil-phishing-url-dataset")`, copy (bukan move) CSV terpilih ke `data/PhiUSIIL.csv` (idempotent: jika sudah ada → skip + ukuran). Pilih CSV: 1 file → pakai; 0 → error; >1 → pilih `PhiUSIIL.csv` atau error daftar nama (jangan acak). Sanity: ukuran >100 MB OK, <100 MB warning. Tangkap exception → pesan ramah + fallback manual, tanpa traceback. Deps: `kagglehub==1.0.3` (pyproject + uv.lock). Tests tidak berubah (43). Tag `v1.0` masih ditunda.

Reputation contract (T14): `src/reputation.py` (tanpa network) — `load_trusted()` singleton fallback set(), `is_trusted(host)` exact match dengan normalisasi lowercase + trailing dot + www., `is_user_content(host)` suffix list (vercel.app, github.io, pages.dev, netlify.app, web.app, herokuapp.com, sites.google.com), `is_shortener(host)`. `src/trusted_domains.json` berisi ~60 domain korporat; tidak ada wildcard/user-content/shortener (test). `src/config.py`: `THRESHOLD_PHISHING=0.65`, `THRESHOLD_SUSPICIOUS=0.40`, `VERDICT_*`, `TRUSTED_DOMAINS_PATH`. `predict_url()` alur: allowlist -> LEGITIMATE (source allowlist, probability None, top_features []); else model; P>=0.65 -> PHISHING; 0.40<=P<0.65 -> SUSPICIOUS; P<0.40 -> LEGITIMATE. `label` (0/1) tetap threshold 0.5; `verdict` user-facing; field baru `verdict`, `decision_source`, `reason`. Tests: `tests/test_reputation.py` (6), `tests/test_predict.py` (22), `tests/test_api.py` (13). Future work: lapisan online PhishTank/whois (T17) akan ditambahkan sebelum allowlist; decision_source sudah menyediakan "denylist"/"domain_age".

Test live URL contract (T11): `scripts/test_live_urls.py` (bootstrap sys.path seperti scripts lain) membaca `tests/fixtures/urls.txt` (abaikan baris kosong/#), memanggil `predict_url`, menangkap `ValueError` sebagai baris ERROR (bukan crash); tanpa artefak → pesan "jalankan train.py dulu" dan exit 1. Output konsol top-1 fitur + ringkasan; `--markdown` mencetak tabel siap-tempel (top-3 fitur). Script tidak menulis ke `hasil_evaluasi.md`; fixture memakai contoh sintetis berlabel (bukan URL phishing nyata dari feed). Catatan temuan: `https://github.com` diskor PHISHING 0.9987 (false positive model pada URL pendek) — cocok dicatat di T12. Tests: `tests/test_live_urls.py` (4).

API contract (T8): `api/main.py` runs from the repo root (`uv run uvicorn api.main:app --port 8001`); endpoints are sync `def` (CPU-bound `predict_url` in threadpool); both `ValueError` and `RequestValidationError` map to **400** with `{"detail": ...}`; `/health` tries `_load()` and reports `model_loaded`; CORS is an explicit allowlist (`localhost:3000`, `127.0.0.1:3000`) with `allow_credentials=False` — never `"*"`. Tests: `tests/test_api.py` (11, via `TestClient`).

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
- **Test set is untouched until T6.** T5 selects models with 5-fold `StratifiedKFold` **on train only**; `src/evaluate.py` is the only place that scores the holdout, and it must obtain indices from `config.make_split(df)` (never a fresh `train_test_split` call), asserting 188.636/47.159.
- **F1 is always phishing-as-positive:** `pos_label=LABEL_PHISH` (0) for scoring/CV, and `P(phishing) = predict_proba[:, 0]`.
- **Inline/delegated layout quirk:** `sys.path` bootstrap is only in `scripts/`; `tests/` relies on `[tool.pytest.ini_options] pythonpath = ["."]` in `pyproject.toml`, and `src/*.py` modules import each other as `from src.x import y`, so run from the repo root.
- **Network/ethics clause.** Default inference tidak mengakses jaringan dan tidak pernah membuka, me-resolve, atau memprobe URL yang dianalisis; `extract_features()` murni string->dict. Pengecualian opt-in: bila `PHISHGUARD_USE_GOOGLE=true` dan `PHISHGUARD_GOOGLE_API_KEY` diisi, Layer 0 `src/google_sb.py` mengirim URL yang diperiksa ke Google Safe Browsing (HTTP, timeout 5 detik, fail-safe); default `false` tetap offline. Hanya `scripts/sync_feeds.py` yang boleh mengunduh daftar feed publik secara berkala (ke `data/feeds/`); data feed tidak didistribusikan ulang. Fixture uji memakai contoh sintetis, bukan URL phishing nyata.
- **Ports:** FastAPI must be **8001**; 8000 belongs to the Reflex backend.
- **Reflex 0.11:** pages are **not** auto-discovered from `app/pages/` — register each one with `app.add_page(...)` in `app/app.py`. 100% Python: no hand-written JS/HTML/JSX, never edit `.web/`. In the render tree use `rx.cond`/`rx.foreach`/Var operators, never Python `if`/`for` over a Var; mutate state only inside event handlers, derived values via `@rx.var`. Note `reflex init` rewrites `.gitignore` and can overwrite `AGENTS.md` — always pass `--no-agents`.
- **Determinism:** seed 42, stratified split; `uv.lock` always committed.
- Before pushing: `uv run pytest -q`, plus `$env:CI=1; uv run reflex run` if UI changed.
