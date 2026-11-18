"""Uji URL mentah (teks) dengan predict_url — tanpa jaringan ke situs yang diuji."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.predict import predict_url

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "urls.txt"


def load_urls(path: Path) -> list[str]:
    """Baca URL dari file: abaikan baris kosong dan komentar (#)."""
    urls: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def _top3(result: dict) -> str:
    items = result.get("top_features") or []
    return "<br>".join(f"{it['feature']}={it['value']} ({it['impact']})" for it in items[:3])


def _probability_text(result: dict) -> str:
    """Allowlist/denylist tidak menyimpan skor; tampilkan '-', bukan 'None'."""
    value = result.get("probability")
    return "-" if value is None else str(value)


def run(urls: list[str]) -> list[tuple[str, object]]:
    """Jalankan predict_url; ValueError ditangkap, bukan crash."""
    out: list[tuple[str, object]] = []
    for url in urls:
        try:
            out.append((url, predict_url(url)))
        except ValueError as exc:
            out.append((url, exc))
    return out


def print_console(results: list[tuple[str, object]]) -> None:
    print(f"{'URL':<60} | {'label':<11} | P(phish) | ms      | top-1 fitur")
    print("-" * 100)
    n_phish = n_legit = n_suspicious = n_err = 0
    for url, result in results:
        if isinstance(result, Exception):
            n_err += 1
            print(f"{url[:60]:<60} | {'ERROR':<11} | -        | -       | {result}")
        else:
            verdict = result.get("verdict") or ("PHISHING" if result["label"] == 0 else "LEGITIMATE")
            if verdict == "PHISHING":
                n_phish += 1
            elif verdict == "LEGITIMATE":
                n_legit += 1
            else:
                n_suspicious += 1
            top = result["top_features"][0]["feature"] if result["top_features"] else "-"
            print(f"{url[:60]:<60} | {result['label_name']:<11} | {_probability_text(result):<8} | {result['inference_ms']:>7} | {top}")
    print("-" * 100)
    print(f"Ringkasan: {n_phish} PHISHING, {n_legit} LEGITIMATE, {n_suspicious} SUSPICIOUS, {n_err} ERROR (total {len(results)})")


def print_markdown(results: list[tuple[str, object]]) -> None:
    print("| URL | label | P(phishing) | inference_ms | top-3 fitur |")
    print("|---|---|---|---|---|")
    for url, result in results:
        if isinstance(result, Exception):
            print(f"| `{url}` | ERROR | - | - | {result} |")
        else:
            print(f"| `{url}` | {result['label_name']} | {_probability_text(result)} | {result['inference_ms']} | {_top3(result)} |")


def main() -> int:
    parser = argparse.ArgumentParser(description="Uji URL mentah dengan predict_url")
    parser.add_argument("--file", default=str(DEFAULT_FIXTURE), help="path file URL (1 per baris)")
    parser.add_argument("--markdown", action="store_true", help="cetak blok Markdown siap-tempel")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"File tidak ditemukan: {path}")
        return 2

    urls = load_urls(path)
    if not urls:
        print("Tidak ada URL untuk diuji.")
        return 0

    # Artefak wajib ada; jangan biarkan 15 baris ERROR.
    try:
        from src.predict import _load

        _load()
    except Exception as exc:
        print(f"Artefak model belum ada: {exc}")
        print("Jalankan `uv run python src/train.py` dulu.")
        return 1

    results = run(urls)
    if args.markdown:
        print_markdown(results)
    else:
        print_console(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
