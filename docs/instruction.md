T14–T16: Lapisan Reputasi Offline + Uncertainty Band
Konteks
Model B (XGBoost, 19 fitur leksikal) false positive pada URL legitimate modern seperti github.com dan URL deploy Vercel, karena hanya membaca pola teks. Ini keterbatasan fundamental, bukan bug. Solusi tahap ini: lapisan reputasi offline (allowlist kurasi) + uncertainty band, TANPA network at inference. PhishTank, whois, DNS, dan threat intel ditunda — jangan implementasikan sekarang, hanya siapkan struktur agar mudah disambungkan nanti.

Keputusan desain yang sudah final (jangan diubah)
Jangan tambah label 2. Semantik label proyek ini inverted (1 = legitimate, 0 = phishing, P(phishing) = proba[:,0]) dan semua test/metrics asumsi 0/1. Sebagai gantinya tambahkan field verdict terpisah: "PHISHING" | "LEGITIMATE" | "SUSPICIOUS".
Threshold pada P(phishing): THRESHOLD_PHISHING = 0.65, THRESHOLD_SUSPICIOUS = 0.40. P ≥ 0.65 → PHISHING; 0.40 ≤ P < 0.65 → SUSPICIOUS; P < 0.40 → LEGITIMATE. config.THRESHOLD = 0.5 untuk keperluan model-only tetap tidak disentuh.
Allowlist hanya exact match domain korporat (host == entri). Larangan keras: jangan pernah allowlist host di bawah public suffix (*.vercel.app, *.github.io, *.pages.dev, *.netlify.app, *.web.app, *.herokuapp.com, sites.google.com) dan jangan allowlist URL shortener (tinyurl.com, bit.ly, dst.). Host user-controlled harus jatuh ke model + uncertainty band, bukan auto-LEGITIMATE.
Tanpa network sama sekali di semua kode baru. Tidak ada dependensi baru yang membutuhkan internet saat runtime.
T14 — src/config.py, src/reputation.py, src/predict.py
src/config.py:

Tambah konstanta: THRESHOLD_PHISHING = 0.65, THRESHOLD_SUSPICIOUS = 0.40, TRUSTED_DOMAINS_PATH = ROOT / "src" / "trusted_domains.json", VERDICT_PHISHING/LEGITIMATE/SUSPICIOUS sebagai konstanta string.
src/trusted_domains.json (committed):

Kurasi manual ±60 domain korporat: google.com, youtube.com, github.com, vercel.com, netlify.com, wikipedia.org, python.org, kompas.com, detik.com, bri.co.id, bca.co.id, mandiri.co.id, kemdikbud.go.id, dsb. Format: {"updated": "2026-11-16", "domains": ["github.com", ...]}. Semua root domain korporat, TANPA wildcard, TANPA domain user-content, TANPA shortener.
src/reputation.py (modul baru):

load_trusted() -> set[str] — load JSON sekali (singleton), fallback set kosong jika file hilang (jangan crash).
is_trusted(host: str) -> bool — exact match saja: host.lower() == domain (setelah strip www.? TIDAK — www.github.com dan github.com keduanya harus match; lakukan normalisasi: lowercase, buang trailing dot, dan perlakukan www. sebagai setara). Subdomain lain seperti gist.github.com TIDAK auto-match → biarkan jatuh ke model.
Sertakan konstanta USER_CONTENT_HOSTS (suffix list di atas) dan fungsi is_user_content(host) -> bool — dipakai test dan nanti oleh lapisan online. Fungsi ini belum dipakai keputusan di T14, cukup teruji.
Sertakan docstring yang menjelaskan: lapisan online (PhishTank denylist, whois domain-age) adalah future work dan akan ditambahkan sebagai lapisan sebelum allowlist; struktur decision_source sudah menyediakan nilai "denylist" dan "domain_age" untuk itu.
src/predict.py — ubah predict_url():

Alur baru: validasi (tetap) → is_trusted(host) → jika ya: label=LABEL_LEGIT, label_name="LEGITIMATE", probability=None, verdict="LEGITIMATE", decision_source="allowlist", reason=f"Domain {host} berada dalam daftar domain tepercaya.", top_features=[], inference_ms tetap diukur. TIDAK memanggil model.
Jika tidak trusted: jalankan model seperti sekarang → dari P(phishing): P ≥ 0.65 → verdict="PHISHING", decision_source="model"; 0.40 ≤ P < 0.65 → verdict="SUSPICIOUS", decision_source="uncertainty"; P < 0.40 → verdict="LEGITIMATE", decision_source="model".
label (0/1) TETAP dari aturan lama P >= THRESHOLD(0.5) agar kompatibel dengan metrics dan test lama — verdict adalah keputusan user-facing, label adalah output model biner. Dokumentasikan bedanya di docstring.
Field reason string Bahasa Indonesia untuk semua cabang, mis. "Skor phishing 0.72 ≥ 0.65 (ambang phishing)." / "Skor phishing 0.52 berada di zona tidak pasti (0.40–0.65); perlu verifikasi manual." / "Skor phishing 0.10 < 0.40."
Backward-compat: pertahankan semua field lama (url, label, label_name, probability, inference_ms, top_features).
T15 — api/main.py dan UI Reflex
api/main.py:

Response model: tambah verdict: str, decision_source: str, reason: str, dan probability: float | None. Update skema doc /docs dan contoh response.
/health tetap; tidak ada perubahan CORS (localhost allowlist).
app/app_state.py:

Base vars baru: verdict, decision_source, reason dengan default kosong.
app/pages/index.py:

Kartu hasil: warna merah (PHISHING), kuning (SUSPICIOUS), hijau (LEGITIMATE) + badge sumber keputusan (Allowlist / Model / Zona Tidak Pasti) + tampilkan reason. Untuk hasil allowlist yang probability=None, tampilkan "—" pada kolom probabilitas.
Salinan user-facing dalam Bahasa Indonesia.
app/pages/evaluasi.py:

Tambah catatan singkat: metrik halaman ini adalah metrik model-only pada test set PhiUSIIL; lapisan reputasi offline menurunkan FP dunia nyata tanpa mengubah test set.
T16 — Docs, tests, verifikasi
Docs:

Update docs/phishguard-schema.md (field baru + alur keputusan) dan README (section "Keputusan berlapis" singkat: allowlist → model → uncertainty band; PhishTank/whois disebut sebagai future work).
Amend AGENTS.md section etika dengan KETAT: tambah satu kalimat klarifikasi — "Lapisan reputasi saat ini murni offline (allowlist kurasi). Lapisan online future work (PhishTank/whois) tetap dilarang sampai di-amend eksplisit." Jangan hapus klausul "no network at inference".
docs/hasil_evaluasi.md: tambah subsection "Analisis FP/FN dan mitigasi" — jelaskan bahwa 28 FP test set berskor 0.70–0.99 sehingga uncertainty band tidak menyelamatkannya; yang memperbaiki FP dunia nyata (github.com, URL deploy Vercel) adalah lapisan allowlist; keterbatasan leksikal (IsHTTPS dominan 0.749, FN phishing pendek-bersih) didokumentasikan apa adanya. Jangan ubah angka metrik apa pun, jangan sentuh docs/metrics.json/stats.json.
Tests (pytest, uv run pytest -q harus hijau):

test_reputation.py baru: exact match github.com dan www.github.com → trusted; gist.github.com, evil-github.com, github.com.evil.io → NOT trusted; foo.vercel.app → is_user_content True dan NOT trusted; shortener tidak ada di allowlist; file JSON hilang → fallback kosong tanpa exception.
test_predict.py: kasus allowlist (https://github.com/... → verdict LEGITIMATE, source allowlist, probability None); kasus band (mock/synthesize P dalam 0.40–0.65 → SUSPICIOUS, source uncertainty); label 0/1 tetap mengikuti threshold 0.5.
Update test API untuk field baru.
Test kontrak penting (wajib ada): https://phishing-test.vercel.app/login TIDAK BOLEH menghasilkan decision_source == "allowlist" — kalau model lama menandainya PHISHING, verdict tidak boleh LEGITIMATE karena allowlist.
Verifikasi akhir: uv run pytest -q, reflex compile/run headless jika UI berubah, dan uji manual scripts/test_live_urls.py dengan tests/fixtures/urls.txt (tambahkan https://github.com/Raka-coder/phishguard-rfxgb, https://vercel.com, https://my-project.vercel.app sebagai fixture) — laporkan output sebelum/sebelum/sesudah perubahan.

Yang sengaja TIDAK dilakukan
Tidak ada PhishTank, whois, DNS, atau API eksternal apa pun (ditunda, akan jadi T17).
Tidak melatih ulang model, tidak mengubah threshold 0.5 untuk label, tidak mengubah metrics.json/hasil evaluasi test set.
Tidak menambah dependensi baru.