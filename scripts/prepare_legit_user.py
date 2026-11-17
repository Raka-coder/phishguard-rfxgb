"""Siapkan set legitimate pribadi dari ekspor riwayat/bookmark, lalu bagi dev/final.

Mode persiapan (default): baca ekspor di `data/realworld/raw/` (atau `--input`),
normalisasi, saring URL sensitif, dedup, batasi per host, tulis
`data/realworld/legit_review.csv` dengan kolom `keep` kosong untuk review manual.

Mode split (`--split`): baca baris dengan `keep=1`, bagi 70/30 dikelompokkan per host
(seed 42) ke `legit_dev.csv` dan `legit_final.csv`.

Tidak ada URL yang dicetak; hanya agregat. Tidak ada jaringan.
"""

import argparse
import csv
import ipaddress
import json
import numpy as np
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reputation import is_trusted, reset_cache

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "realworld" / "raw"
DEFAULT_REVIEW = ROOT / "data" / "realworld" / "legit_review.csv"
DEFAULT_DEV = ROOT / "data" / "realworld" / "legit_dev.csv"
DEFAULT_FINAL = ROOT / "data" / "realworld" / "legit_final.csv"

URL_COLUMNS = {"url", "href", "link", "uri", "location", "address", "web", "website", "addressurl"}
SENSITIVE_KEYWORDS = (
    "login",
    "signin",
    "sign-in",
    "auth",
    "oauth",
    "account",
    "mail",
    "inbox",
    "token",
    "password",
    "admin",
    "logout",
    "signup",
    "sign-up",
    "register",
    "reset",
    "verify",
    "otp",
    "secret",
)
PERSONAL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "yahoo.com",
    "ymail.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "proton.me",
    "protonmail.com",
    "mail.com",
    "aol.com",
    "gmx.com",
    "gmx.net",
    "yandex.com",
    "yandex.ru",
    "mail.ru",
    "zoho.com",
    "fastmail.com",
    "tutanota.com",
    "paypal.com",
    "stripe.com",
    "wise.com",
    "revolut.com",
    "venmo.com",
    "cash.app",
    "chase.com",
    "bankofamerica.com",
    "wellsfargo.com",
    "citibank.com",
    "hsbc.com",
    "barclays.co.uk",
    "monzo.com",
    "starlingbank.com",
}
PRIVATE_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home", ".corp", ".intranet")
REVIEW_COLUMNS = ["url", "reg_domain", "in_allowlist", "host_type", "person_label", "keep"]
OUTPUT_COLUMNS = ["url", "reg_domain", "in_allowlist", "host_type", "person_label"]

# Suffix dua bagian yang umum (offline, tanpa dependensi jaringan).
TWO_PART_SUFFIXES = {
    "co.id", "ac.id", "go.id", "or.id", "net.id", "sch.id", "web.id", "mil.id",
    "my.id", "biz.id", "co.uk", "org.uk", "ac.uk", "co.jp", "or.jp", "ac.jp",
    "com.au", "org.au", "net.au", "co.nz", "org.nz", "co.kr", "or.kr",
    "com.br", "org.br", "com.cn", "org.cn", "com.tw", "org.tw",
}


def registered_domain(host: str) -> str:
    """Domain terdaftar dari host memakai daftar suffix offline (tanpa PSL penuh)."""
    host = (host or "").strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    labels = [label for label in host.split(".") if label]
    if len(labels) <= 2:
        return host
    suffix = ".".join(labels[-2:])
    if suffix in TWO_PART_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def normalize_url(raw: str) -> str | None:
    """http/https, buang query & fragment, host lowercase, tanpa port."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "http://" + raw
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        return None
    host = (parts.hostname or "").lower()
    if not host or " " in host or not all(c.isalnum() or c in ".-" for c in host):
        return None
    path = parts.path or ""
    return urlunsplit((scheme, host, path, "", ""))


def _is_private_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return bool(ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local or ip.is_multicast)
    except ValueError:
        pass
    if host in ("localhost",) or host.endswith(PRIVATE_SUFFIXES):
        return True
    return False


def is_sensitive(url: str) -> bool:
    """True bila URL berpotensi memuat data pribadi atau akses akun."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path or ""
    if _is_private_host(host):
        return True
    haystack = (host + " " + path + " " + (parts.query or "")).lower()
    if any(keyword in haystack for keyword in SENSITIVE_KEYWORDS):
        return True
    if any(host == domain or host.endswith("." + domain) for domain in PERSONAL_DOMAINS):
        return True
    if len(path) > 120:
        return True
    return False


def host_type(url: str) -> str:
    """root bila path kosong atau '/', selain itu berpath."""
    path = urlsplit(url).path or ""
    return "root" if path in ("", "/") else "berpath"


def _extract_urls_from_obj(obj, found: list[str]) -> None:
    """Ambil string URL dari struktur JSON apa pun (Chrome bookmark, array, dict)."""
    if isinstance(obj, str):
        found.append(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and (key or "").lower() in URL_COLUMNS:
                found.append(value)
            else:
                _extract_urls_from_obj(value, found)
    elif isinstance(obj, list):
        for item in obj:
            _extract_urls_from_obj(item, found)


def read_export(path: Path) -> list[str]:
    """Baca satu file ekspor (CSV/JSON/HTML/txt) menjadi daftar string mentah."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        urls: list[str] = []
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            url_cols = [col for col in (reader.fieldnames or []) if (col or "").lower() in URL_COLUMNS]
            if not url_cols and reader.fieldnames:
                url_cols = [reader.fieldnames[0]]
            for row in reader:
                for col in url_cols:
                    value = (row.get(col) or "").strip()
                    if value:
                        urls.append(value)
        return urls
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        found: list[str] = []
        _extract_urls_from_obj(data, found)
        return found
    if suffix in (".html", ".htm"):
        class _Parser(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.urls: list[str] = []

            def handle_starttag(self, tag, attrs):
                if tag.lower() == "a":
                    for key, value in attrs:
                        if key.lower() == "href" and value:
                            self.urls.append(value)

        parser = _Parser()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        return parser.urls
    # txt atau lainnya: satu URL per baris
    return [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]


def collect_inputs(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        files: list[Path] = []
        for pattern in ("*.csv", "*.json", "*.html", "*.htm", "*.txt"):
            files.extend(sorted(input_path.glob(pattern)))
        return files
    return []


def prepare(
    input_path: Path, person_label: str, max_per_host: int
) -> tuple[list[dict[str, str]], dict[str, int], int]:
    """Kembalikan baris review, hitungan saringan, dan jumlah URL mentah."""
    files = collect_inputs(input_path)
    raw_urls: list[str] = []
    for file_path in files:
        raw_urls.extend(read_export(file_path))

    total = len(raw_urls)
    counts = {
        "invalid": 0,
        "sensitive": 0,
        "long_path": 0,
        "duplicate": 0,
        "cap": 0,
    }
    seen: set[str] = set()
    candidates: list[str] = []
    for raw in raw_urls:
        normalized = normalize_url(raw)
        if normalized is None:
            counts["invalid"] += 1
            continue
        if is_sensitive(normalized) or is_sensitive(raw):
            if len(urlsplit(normalized).path) > 120 or len(urlsplit(raw).path) > 120:
                counts["long_path"] += 1
            else:
                counts["sensitive"] += 1
            continue
        if normalized in seen:
            counts["duplicate"] += 1
            continue
        seen.add(normalized)
        candidates.append(normalized)

    by_reg_domain: dict[str, int] = {}
    kept: list[str] = []
    for url in candidates:
        host = urlsplit(url).hostname or ""
        reg = registered_domain(host)
        if by_reg_domain.get(reg, 0) >= max_per_host:
            counts["cap"] += 1
            continue
        by_reg_domain[reg] = by_reg_domain.get(reg, 0) + 1
        kept.append(url)

    reset_cache()
    rows: list[dict[str, str]] = []
    for url in kept:
        host = urlsplit(url).hostname or ""
        rows.append(
            {
                "url": url,
                "reg_domain": registered_domain(host),
                "in_allowlist": "1" if is_trusted(host) else "0",
                "host_type": host_type(url),
                "person_label": person_label,
                "keep": "",
            }
        )
    return rows, counts, total


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def split_review(
    review_path: Path, dev_path: Path, final_path: Path, test_size: float, seed: int
) -> None:
    from sklearn.model_selection import GroupShuffleSplit

    if not review_path.exists():
        raise SystemExit(f"File tidak ditemukan: {review_path}")
    with review_path.open(encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    selected = [row for row in rows if (row.get("keep") or "").strip() == "1"]
    if not selected:
        raise SystemExit("Tidak ada baris dengan keep=1; isi dulu kolom 'keep'.")

    hosts = np.array([urlsplit(row["url"]).hostname or "" for row in selected])
    labels = np.zeros(len(selected), dtype=int)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    dev_rel, final_rel = next(splitter.split(labels, groups=hosts))
    dev_rows = [selected[i] for i in sorted(dev_rel)]
    final_rows = [selected[i] for i in sorted(final_rel)]

    def project(items: list[dict[str, str]]) -> list[dict[str, str]]:
        return [{column: row.get(column, "") for column in OUTPUT_COLUMNS} for row in items]

    write_csv(dev_path, project(dev_rows), OUTPUT_COLUMNS)
    write_csv(final_path, project(final_rows), OUTPUT_COLUMNS)

    dev_hosts = {urlsplit(row["url"]).hostname or "" for row in dev_rows}
    final_hosts = {urlsplit(row["url"]).hostname or "" for row in final_rows}
    print(f"Baris keep=1: {len(selected)}")
    print(
        f"Dev: {len(dev_rows)} URL ({sum(r['host_type'] == 'root' for r in dev_rows)} root, "
        f"{sum(r['host_type'] == 'berpath' for r in dev_rows)} berpath), {len(dev_hosts)} host"
    )
    print(
        f"Final: {len(final_rows)} URL ({sum(r['host_type'] == 'root' for r in final_rows)} root, "
        f"{sum(r['host_type'] == 'berpath' for r in final_rows)} berpath), {len(final_hosts)} host"
    )
    print(f"Host tumpang tindih dev/final: {len(dev_hosts & final_hosts)}")


def apply_cap_review(path: Path, max_per_reg_domain: int) -> None:
    """Tambah reg_domain dan terapkan cap per reg_domain tanpa menghapus keep=1."""
    if not path.exists():
        raise SystemExit(f"File tidak ditemukan: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]

    for row in rows:
        if not (row.get("reg_domain") or "").strip():
            row["reg_domain"] = registered_domain(urlsplit(row.get("url", "")).hostname or "")

    keep_flags = [(row.get("keep") or "").strip() == "1" for row in rows]
    kept_indices: set[int] = set()
    counts: dict[str, int] = {}
    for index, row in enumerate(rows):
        if keep_flags[index]:
            kept_indices.add(index)
            reg = row["reg_domain"]
            counts[reg] = counts.get(reg, 0) + 1
    for index, row in enumerate(rows):
        if index in kept_indices:
            continue
        reg = row["reg_domain"]
        if counts.get(reg, 0) < max_per_reg_domain:
            kept_indices.add(index)
            counts[reg] = counts.get(reg, 0) + 1

    kept_rows = [rows[index] for index in sorted(kept_indices)]
    dropped = len(rows) - len(kept_rows)
    if "reg_domain" not in fieldnames:
        columns = ["url", "reg_domain"] + [col for col in fieldnames if col != "url"]
    else:
        columns = fieldnames

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in kept_rows:
            writer.writerow({column: row.get(column, "") for column in columns})

    reg_before = len({row["reg_domain"] for row in rows})
    reg_after = len({row["reg_domain"] for row in kept_rows})
    print(f"Review: {len(rows)} baris, {reg_before} reg_domain")
    print(f"Dipertahankan: {len(kept_rows)} baris ({reg_after} reg_domain)")
    print(f"Dibuang: {dropped} baris (melebihi batas {max_per_reg_domain} per reg_domain)")
    print(f"Ditulis: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siapkan set legitimate pribadi dari ekspor riwayat/bookmark")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="file atau direktori ekspor")
    parser.add_argument("--output", default=str(DEFAULT_REVIEW), help="CSV review keluaran")
    parser.add_argument("--person-label", default="", help="label anonim (wajib di mode persiapan)")
    parser.add_argument("--max-per-host", type=int, default=5, help="maks URL per host")
    parser.add_argument("--apply-cap", action="store_true", help="tambah reg_domain dan terapkan cap 5 per reg_domain pada review CSV")
    parser.add_argument("--review", default=str(DEFAULT_REVIEW), help="CSV review untuk --apply-cap / mode split")
    parser.add_argument("--max-per-reg-domain", type=int, default=5, help="maks URL per reg_domain")
    parser.add_argument("--dev", default=str(DEFAULT_DEV), help="CSV dev keluaran")
    parser.add_argument("--final", default=str(DEFAULT_FINAL), help="CSV final keluaran")
    parser.add_argument("--split", action="store_true", help="bagi legit_review.csv (keep=1) menjadi dev/final")
    parser.add_argument("--seed", type=int, default=42, help="seed split")
    args = parser.parse_args(argv)

    if args.apply_cap:
        apply_cap_review(Path(args.review), args.max_per_reg_domain)
        return 0

    if args.split:
        split_review(Path(args.review), Path(args.dev), Path(args.final), args.test_size, args.seed)
        return 0

    if not args.person_label.strip():
        print("--person-label wajib di mode persiapan (label anonim, bukan nama asli).")
        return 2
    input_path = Path(args.input)
    if not input_path.exists():
        input_path.mkdir(parents=True, exist_ok=True)
        print(f"Direktori input dibuat: {input_path}")
        print("Taruh ekspor riwayat/bookmark di sana, lalu jalankan ulang.")
        return 0

    rows, counts, total = prepare(input_path, args.person_label.strip(), args.max_per_host)
    output_path = Path(args.output)
    write_csv(output_path, rows, REVIEW_COLUMNS)

    root_count = sum(row["host_type"] == "root" for row in rows)
    berpath_count = len(rows) - root_count
    allow_count = sum(row["in_allowlist"] == "1" for row in rows)
    outside_count = len(rows) - allow_count
    print(f"Input URL mentah: {total}")
    print(
        f"Disaring: {counts['invalid']} tidak valid, {counts['sensitive']} sensitif, "
        f"{counts['long_path']} path>120, {counts['duplicate']} duplikat, {counts['cap']} melebihi batas per host"
    )
    print(f"Tersimpan: {len(rows)} URL dari {len({urlsplit(r['url']).hostname for r in rows})} host")
    print(f"  root: {root_count}, berpath: {berpath_count}")
    print(f"  di allowlist: {allow_count}, di luar allowlist: {outside_count}")
    print(f"Ditulis: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
