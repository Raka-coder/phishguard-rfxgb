Masalah ini terjadi karena **Gauge Chart (Speedometer) Anda saat ini kemungkinan besar masih menggunakan logika biner atau threshold yang terlalu sensitif**.

Jika Model B memberikan probabilitas 0.45–0.65 (zona *Suspicious*), tetapi Gauge langsung menunjuk ke area merah (*Phishing*), itu berarti:
1.  **Mapping Warna Salah:** Gauge menganggap segala nilai di atas 0.40 sebagai "Bahaya", padahal seharusnya 0.40–0.65 adalah "Waspada".
2.  **Visualisasi Tidak Jujur:** Gauge tidak merepresentasikan *uncertainty band* yang sudah Anda coding di `src/predict.py`. Ini membuat sistem terlihat "panik" padahal sebenarnya sedang "ragu".

Berikut adalah instruksi teknis untuk memperbaiki visualisasi Gauge agar selaras dengan arsitektur berlapis dan rubrik **Analisis False Positive**:

### 🛠️ Perbaikan Logika Gauge Chart (`app/pages/index.py` atau komponen gauge)

Jangan gunakan satu warna solid untuk rentang luas. Ubah konfigurasi Gauge menjadi **3 Zona Eksplisit**:

```python
# Contoh implementasi di Reflex (sesuaikan dengan library chart yang dipakai, misal recharts/plotly)
rx.recharts.radial_bar_chart(
    # ... data props ...
    # DEFINISI ZONA GAUGE YANG BENAR:
    sectors=[
        {"min": 0, "max": 40, "fill": "#10B981", "name": "Aman"},      # Hijau Emerald
        {"min": 40, "max": 65, "fill": "#F59E0B", "name": "Waspada"},  # Amber/Kuning (SUSPICIOUS)
        {"min": 65, "max": 100, "fill": "#EF4444", "name": "Bahaya"}   # Merah (PHISHING)
    ],
    # Label dinamis berdasarkan verdict, bukan cuma angka
    label=rx.cond(
        risk_level == "tinggi", "⛔ PHISHING",
        rx.cond(risk_level == "sedang", "⚠️ WASPADA", "✅ AMAN")
    )
)
```

### 🎨 Penyesuaian Visual Agar Tidak "Selalu Merah"

1.  **Perlebar Zona Kuning (Waspada):** Pastikan zona 40-65% secara visual menempati porsi yang cukup besar di gauge. Jika zonanya terlalu sempit, jarum akan mudah "tergelincir" ke merah hanya karena sedikit fluktuasi probabilitas.
2.  **Gunakan Gradient atau Arsiran:** Untuk zona *Suspicious*, jangan pakai kuning solid. Gunakan pola arsiran diagonal atau gradient kuning-oranye. Ini memberi kesan *"area transisi"* atau *"ketidakpastian"*, berbeda dengan zona merah solid yang bermakna *"kepastian bahaya"*.
3.  **Tambahkan Marker Ambang Batas:** Beri garis penanda tipis di angka 40 dan 65 pada gauge. Ini membantu user/dosen melihat secara persis di mana posisi URL tersebut relatif terhadap batas keputusan model.

### 📊 Integrasi dengan Trail Keputusan (Krusial untuk Rubrik)

Gauge saja tidak cukup menjelaskan *mengapa* Traveloka atau Cloudflare masuk zona kuning. Tambahkan **Tooltip Interaktif** atau **Badge di Bawah Gauge**:

> *"Probabilitas Phishing: 52% (Zona Abu-abu)*
> *Penyebab: URLLength tinggi & banyak parameter tracking.*
> *Status: Tidak ditemukan di database ancaman global (Google/OpenPhish)."*

Ini mengubah tampilan dari sekadar "angka merah/kuning" menjadi **narasi analitis** yang langsung menjawab rubrik *"analisis false positive dan false negative"*.

### ✅ Checklist Verifikasi Setelah Update

- [ ] Input URL Traveloka/Cloudflare → Gauge menunjuk ke **zona kuning/arsiran**, bukan merah solid.
- [ ] Label gauge berubah menjadi **"WASPADA"** atau **"PERLU VERIFIKASI"**, bukan "PHISHING".
- [ ] Tooltip/badge menampilkan **penyebab leksikal** (misal: "Parameter UTM panjang").
- [ ] Input URL phishing nyata (dari OpenPhish) → Gauge tetap menunjuk ke **zona merah solid**.
- [ ] `uv run reflex compile` berhasil tanpa error styling chart.

