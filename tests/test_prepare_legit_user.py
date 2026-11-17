"""Kontrak T24a: persiapan set legitimate pribadi dan split dev/final."""

import csv
import io
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.prepare_legit_user import (
    DEFAULT_FINAL,
    DEFAULT_REVIEW,
    OUTPUT_COLUMNS,
    REVIEW_COLUMNS,
    host_type,
    is_sensitive,
    main,
    normalize_url,
    prepare,
    read_export,
    split_review,
)


def test_normalize_url_strips_query_fragment_and_lowercases():
    assert normalize_url("https://Example.com/Path?a=1#frag") == "https://example.com/Path"
    assert normalize_url("http://example.com/") == "http://example.com/"
    assert normalize_url("example.com/x") == "http://example.com/x"


def test_normalize_url_rejects_non_http():
    assert normalize_url("ftp://example.com") is None
    assert normalize_url("") is None
    assert normalize_url("not a url") is None


def test_host_type():
    assert host_type("https://example.com") == "root"
    assert host_type("https://example.com/") == "root"
    assert host_type("https://example.com/a") == "berpath"


def test_is_sensitive_filters_keywords_private_ip_and_length():
    assert is_sensitive("https://example.com/login")
    assert is_sensitive("https://example.com/x?token=abc")
    assert is_sensitive("http://192.168.1.5/x")
    assert is_sensitive("https://example.com/" + "a" * 121)
    assert is_sensitive("https://mail.google.com/inbox")
    assert is_sensitive("https://paypal.com/x")
    assert not is_sensitive("https://example.com/docs/guide")


def test_read_export_csv_json_html(tmp_path):
    csv_path = tmp_path / "a.csv"
    csv_path.write_text("url,title\nhttps://example.com/a,x\nhttps://example.com/b,y\n", encoding="utf-8")
    assert read_export(csv_path) == ["https://example.com/a", "https://example.com/b"]

    json_path = tmp_path / "b.json"
    json_path.write_text(json.dumps({"roots": {"children": [{"url": "https://x.com/1"}, {"href": "https://x.com/2"}]}}), encoding="utf-8")
    assert read_export(json_path) == ["https://x.com/1", "https://x.com/2"]

    html_path = tmp_path / "c.html"
    html_path.write_text('<a href="https://y.com/1">a</a><A HREF="https://y.com/2">b</A>', encoding="utf-8")
    assert read_export(html_path) == ["https://y.com/1", "https://y.com/2"]


def test_prepare_dedups_and_caps_per_host(tmp_path):
    csv_path = tmp_path / "in.csv"
    urls = [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
        "https://example.com/d",
        "https://example.com/e",
        "https://example.com/f",
        "https://example.com/a?x=1",
        "https://other.com/x",
        "https://other.com/login",
    ]
    csv_path.write_text("url\n" + "\n".join(urls) + "\n", encoding="utf-8")
    rows, counts, total = prepare(csv_path, "anon-1", 2)
    assert total == len(urls)
    assert counts["duplicate"] == 1
    assert counts["cap"] == 4  # 6 kandidat example.com, cap 2 -> 4 dibuang
    assert counts["sensitive"] == 1
    assert len(rows) == 3
    assert {row["url"] for row in rows} == {
        "https://example.com/a",
        "https://example.com/b",
        "https://other.com/x",
    }
    assert all(row["person_label"] == "anon-1" for row in rows)
    assert all(row["keep"] == "" for row in rows)
    assert {row["host_type"] for row in rows} <= {"root", "berpath"}


def test_prepare_marks_allowlist(tmp_path, monkeypatch):
    csv_path = tmp_path / "in.csv"
    csv_path.write_text("url\nhttps://github.com/x\nhttps://unknown.example/x\n", encoding="utf-8")
    rows, _, _ = prepare(csv_path, "anon-1", 5)
    by_url = {row["url"]: row["in_allowlist"] for row in rows}
    assert by_url["https://github.com/x"] == "1"
    assert by_url["https://unknown.example/x"] == "0"


def test_split_review_grouped_and_ratio(tmp_path):
    review = tmp_path / "review.csv"
    fieldnames = REVIEW_COLUMNS
    rows = [
        {"url": "https://a.com/1", "in_allowlist": "0", "host_type": "berpath", "person_label": "anon-1", "keep": "1"},
        {"url": "https://a.com/2", "in_allowlist": "0", "host_type": "berpath", "person_label": "anon-1", "keep": "1"},
        {"url": "https://b.com/", "in_allowlist": "1", "host_type": "root", "person_label": "anon-1", "keep": "1"},
        {"url": "https://c.com/x", "in_allowlist": "0", "host_type": "berpath", "person_label": "anon-1", "keep": "0"},
    ]
    with review.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    dev = tmp_path / "dev.csv"
    final = tmp_path / "final.csv"
    split_review(review, dev, final, test_size=0.3, seed=42)
    dev_rows = list(csv.DictReader(dev.open(encoding="utf-8")))
    final_rows = list(csv.DictReader(final.open(encoding="utf-8")))
    assert len(dev_rows) + len(final_rows) == 3
    dev_hosts = {r["url"].split("/")[2] for r in dev_rows}
    final_hosts = {r["url"].split("/")[2] for r in final_rows}
    assert dev_hosts.isdisjoint(final_hosts)
    assert list(dev_rows[0].keys()) == OUTPUT_COLUMNS


def test_split_review_requires_keep_one(tmp_path):
    review = tmp_path / "review.csv"
    review.write_text("url,in_allowlist,host_type,person_label,keep\nhttps://a.com/x,0,berpath,anon-1,0\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        split_review(review, tmp_path / "dev.csv", tmp_path / "final.csv", 0.3, 42)


def test_prepare_no_url_in_stdout(tmp_path, monkeypatch, capsys):
    csv_path = tmp_path / "in.csv"
    out_path = tmp_path / "review.csv"
    csv_path.write_text("url\nhttps://example.com/a\nhttps://example.com/login\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["x", "--input", str(csv_path), "--output", str(out_path), "--person-label", "anon-1"])
    assert main() == 0
    captured = capsys.readouterr().out
    assert "://" not in captured
    assert "Tersimpan" in captured
