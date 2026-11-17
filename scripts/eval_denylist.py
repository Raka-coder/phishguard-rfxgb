"""Evaluasi denylist: overlap antar snapshot, kurva umur entri, FP, evaluasi sistem penuh.

Penggunaan:
    uv run python scripts/eval_denylist.py
    uv run python scripts/eval_denylist.py --snapshot-a X --snapshot-b Y

Metrik utama diganti dari "capture URL baru": kini memakai tumpang tindih
URL/host/domain antar snapshot terurut + kurva umur entri (persentase entri
snapshot pertama yang masih muncul di snapshot berikutnya) + selang waktu antar
snapshot (jam).

Hasil ditulis ke docs/denylist.json (tanpa URL). Semua angka dari skrip.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DOCS_DIR, FEED_DIR
from src.denylist import normalize_url

Z_95 = 1.959963984540054


def wilson_ci(k: int, n: int, z: float = Z_95) -> list[float]:
    """CI Wilson 95% untuk proporsi k/n."""
    if n <= 0:
        return [0.0, 0.0]
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    lo = (centre - half) / denom
    hi = (centre + half) / denom
    return [max(0.0, lo), min(1.0, hi)]


def read_urls(path: Path) -> list[str]:
    if path.suffix.lower() == ".csv":
        urls: list[str] = []
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                u = (row.get("url") or "").strip()
                if u:
                    urls.append(u)
        return urls
    urls = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            if "," in line:
                line = line.split(",", 1)[0].strip()
            urls.append(line)
    return urls


def host_of_key(key: str) -> str:
    """Key 'host/path' -> host."""
    return key.split("/", 1)[0]


def domain_of_host(host: str) -> str:
    """Host -> domain (www. di-stripping), konsisten dengan fitur host Model C."""
    return host[len("www.") :] if host.startswith("www.") else host


def pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 2) if whole > 0 else 0.0


def overlap_between(keys_a: set[str], keys_b: set[str]) -> dict:
    """Tumpang tindih antar snapshot: URL, host, domain + jumlah baru di B."""
    inter = keys_a & keys_b
    hosts_a = {host_of_key(k) for k in keys_a}
    hosts_b = {host_of_key(k) for k in keys_b}
    domains_a = {domain_of_host(h) for h in hosts_a}
    domains_b = {domain_of_host(h) for h in hosts_b}
    n_b = len(keys_b)
    return {
        "n_urls_a": len(keys_a),
        "n_urls_b": len(keys_b),
        "n_url_overlap": len(inter),
        "n_url_overlap_pct_of_b": pct(len(inter), n_b),
        "n_host_overlap": len(hosts_a & hosts_b),
        "n_host_overlap_pct_of_b": pct(len(hosts_a & hosts_b), len(hosts_b)),
        "n_domain_overlap": len(domains_a & domains_b),
        "n_domain_overlap_pct_of_b": pct(len(domains_a & domains_b), len(domains_b)),
        "n_new_in_b": len(keys_b - keys_a),
    }


def collect_snapshots(feed_dir: Path, extra: list[Path] | None = None) -> list[Path]:
    cands: list[Path] = []
    if feed_dir.exists():
        cands += [p for p in feed_dir.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".csv"}]
    for e in (extra or []):
        if e.exists():
            cands.append(e)
    return sorted(set(cands), key=lambda p: p.stat().st_mtime)


def age_curve(snapshots: list[Path]) -> list[dict]:
    """Untuk snapshot pertama: % entri yang masih muncul di snapshot berikutnya + selang waktu (jam)."""
    if len(snapshots) < 2:
        return []
    first = snapshots[0]
    keys_a = {normalize_url(u) for u in read_urls(first) if normalize_url(u)}
    entries = []
    for later in snapshots[1:]:
        keys_b = {normalize_url(u) for u in read_urls(later) if normalize_url(u)}
        hours = (later.stat().st_mtime - first.stat().st_mtime) / 3600.0
        entries.append(
            {
                "snapshot": first.name,
                "later_snapshot": later.name,
                "pct_still_present": pct(len(keys_a & keys_b), len(keys_a)),
                "hours_between_snapshots": round(hours, 3),
            }
        )
    return entries


def _fp_on_legit(deny_keys: set[str], legit_path: Path) -> tuple[int, int]:
    if not legit_path.exists():
        return 0, 0
    urls = read_urls(legit_path)
    fp = sum(1 for u in urls if normalize_url(u) is not None and normalize_url(u) in deny_keys)
    return len(urls), fp


def run_full_system(args: argparse.Namespace, denylist_external: Path | None, source_snapshot: Path) -> dict:
    """Evaluasi sistem penuh: denylist dimatikan, atau memakai snapshot non-sumber set uji."""
    import src.predict as predict

    results: dict[str, dict] = {}

    def evaluate(deny_keys: set[str] | None, mode: str) -> dict:
        out: dict[str, dict] = {}
        for label, legit_path in (("legit_dev", args.legit_dev), ("legit_final", args.legit_final)):
            urls = read_urls(legit_path)
            verdicts = {"PHISHING": 0, "SUSPICIOUS": 0, "LEGITIMATE": 0}
            n_fp = 0
            for u in urls:
                if deny_keys is None:
                    predict.feed_status = lambda: ("missing", None, "eval: denylist dimatikan")
                    predict.is_denied = lambda u: False  # noqa: E731 - eval only
                else:
                    predict.feed_status = lambda p=denylist_external: ("ok", p, "eval: snapshot eksternal")  # noqa: E731
                    predict.is_denied = (  # noqa: E731
                        lambda kk: (lambda u: (normalize_url(u) is not None and normalize_url(u) in kk))  # noqa: E731
                    )(deny_keys)
                r = predict.predict_url(u)
                verdict = str(r.get("verdict") or "LEGITIMATE")
                verdicts[verdict] = verdicts.get(verdict, 0) + 1
                if verdict == "PHISHING":
                    n_fp += 1
            out[label] = {"n_tested": len(urls), "verdicts": verdicts, "n_fp": n_fp}
        return out

    results["denylist_disabled"] = evaluate(None, "denylist_disabled")
    modes = ["denylist_disabled"]
    if denylist_external is not None and denylist_external.resolve() != source_snapshot.resolve():
        modes.append("denylist_external_snapshot")
        results["denylist_external_snapshot"] = evaluate(
            {normalize_url(u) for u in read_urls(denylist_external) if normalize_url(u)},
            "denylist_external_snapshot",
        )

    return {
        "rule": "Evaluasi sistem penuh hanya boleh dijalankan dengan denylist dimatikan atau memakai snapshot yang bukan sumber set uji.",
        "modes_run": modes,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-a", type=Path, default=None)
    parser.add_argument("--snapshot-b", type=Path, default=None)
    parser.add_argument("--legit-dev", type=Path, default=Path("data/realworld/legit_dev.csv"))
    parser.add_argument("--legit-final", type=Path, default=Path("data/realworld/legit_final.csv"))
    parser.add_argument("--out", type=Path, default=DOCS_DIR / "denylist.json")
    args = parser.parse_args()

    if args.snapshot_a is not None and args.snapshot_b is not None:
        seq = [args.snapshot_a, args.snapshot_b]
    else:
        seq = collect_snapshots(FEED_DIR, extra=[Path("data/realworld/openphish.txt")])

    if len(seq) < 2 or not seq[0].exists() or not seq[1].exists():
        raise SystemExit(
            f"Perlu >=2 snapshot. Jalankan `uv run python scripts/sync_feeds.py` minimal dua kali "
            "(atau sediakan data/realworld/openphish.txt) lalu ulangi."
        )

    keys_by: dict[str, set[str]] = {}
    snapshots_info = []
    for p in seq:
        keys = {normalize_url(u) for u in read_urls(p) if normalize_url(u)}
        keys_by[p.name] = keys
        snapshots_info.append({"name": p.name, "n_urls": len(keys)})

    overlap: list[dict] = []
    for a, b in zip(seq, seq[1:]):
        entry = overlap_between(keys_by[a.name], keys_by[b.name])
        entry["snapshot_a"] = a.name
        entry["snapshot_b"] = b.name
        entry["hours_between_snapshots"] = round((b.stat().st_mtime - a.stat().st_mtime) / 3600.0, 3)
        overlap.append(entry)

    age = age_curve(seq)

    deny_set = keys_by[seq[0].name]
    dev_tested, dev_fp = _fp_on_legit(deny_set, args.legit_dev)
    final_tested, final_fp = _fp_on_legit(deny_set, args.legit_final)

    source_snapshot = Path("data/realworld/openphish.txt")
    denylist_external = seq[-1] if seq[-1].resolve() != source_snapshot.resolve() else None

    full_system = run_full_system(args, denylist_external, source_snapshot)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshots": snapshots_info,
        "overlap": overlap,
        "age_curve": age,
        "false_positives": {
            "denylist_snapshot": seq[0].name,
            "legit_dev": {"n_tested": dev_tested, "n_fp": dev_fp},
            "legit_final": {"n_tested": final_tested, "n_fp": final_fp},
        },
        "full_system": full_system,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nDitulis ke {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
