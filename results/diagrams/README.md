# Diagram Mermaid (T32)

Berkas `.mmd` di folder ini adalah sumber diagram untuk Bab 3. Setiap diagram disalin
sebagai blok kode di bawah agar bisa langsung ditempel ke `results/laporan/bab3.md`.
Renderer yang dipakai: Mermaid bawaan GitHub, atau `mmdc` dari `@mermaid-js/mermaid-cli`.
Bila `src/predict.py` berubah, perbarui `.mmd` dan blok di bawah pada saat yang sama.

Isi diagram mengikuti penomoran lapisan yang benar-benar ada di `src/predict.py`:
L0 Google Safe Browsing (opt-in), L1 denylist feed, L2 allowlist, L3 Model B + Model C,
L4 shortener. Lapisan peniruan merek (T20) belum diimplementasikan, sehingga tidak
digambar sebagai lapisan.

## 1. Alur keputusan berlapis (`alur_keputusan.mmd`)

```mermaid
flowchart TD
    U["URL masuk"] --> V{"Skema http/https dan host valid?"}
    V -- "tidak" --> E["ValueError, API memetakan ke HTTP 400"]
    V -- "ya" --> G{"PHISHGUARD_USE_GOOGLE aktif?"}
    G -- "tidak (default)" --> DL{"L1 URL ada di snapshot feed?"}
    G -- "ya" --> GSB["L0 Google Safe Browsing (HTTP, timeout 5 detik)"]
    GSB -- "cocok" --> PH0["PHISHING, risk tinggi, decision_source=google_safe_browsing"]
    GSB -- "tidak cocok atau gagal" --> DL
    DL -- "cocok dan feed segar" --> PH1["PHISHING, risk tinggi, decision_source=denylist"]
    DL -- "tidak cocok, basi, atau hilang" --> AL{"L2 domain ada di allowlist?"}
    AL -- "cocok" --> LG0["LEGITIMATE, risk rendah, probability null, decision_source=allowlist"]
    AL -- "tidak cocok" --> MB["L3 Model B, 19 fitur leksikal, P(phishing)"]
    MB --> MC["L3 Model C, host-only tanpa www, P(phishing)"]
    MC --> CONS{"Zona Model B dan Model C"}
    CONS -- "dua-duanya tinggi" --> S1["SUSPICIOUS, risk tinggi"]
    CONS -- "dua-duanya rendah" --> LG1["LEGITIMATE, risk rendah"]
    CONS -- "berbeda atau C tidak tersedia" --> S2["SUSPICIOUS, risk sedang"]
    LG1 --> SH{"L4 host shortener?"}
    S1 --> OUT["Respons JSON: verdict, risk_level, probability, top_features, trail"]
    S2 --> OUT
    SH -- "ya" --> S3["SUSPICIOUS, risk sedang, decision_source=shortener"]
    SH -- "tidak" --> OUT
    S3 --> OUT
    NOTE["Catatan: lapisan peniruan merek T20 belum ada di src/predict.py"] -.-> CONS

    classDef phish fill:#f6d5d1,stroke:#c0392b,color:#111
    classDef legit fill:#d6ecd9,stroke:#2e7d32,color:#111
    classDef susp fill:#fbeec2,stroke:#b07d00,color:#111
    classDef note fill:#eceff1,stroke:#7f8c8d,color:#111,stroke-dasharray:4 3
    class PH0,PH1 phish
    class LG0,LG1 legit
    class S1,S2,S3 susp
    class NOTE note
```

## 2. Flowchart `predict_url` dengan short-circuit (`predict_url.mmd`)

```mermaid
flowchart TD
    A["predict_url(url)"] --> B["_validate: skema dan host"]
    B -- "gagal" --> ERR["raise ValueError"]
    B -- "lolos" --> C{"google_enabled()"}
    C -- "ya" --> D["check_google_safe_browsing"]
    D -- "cocok" --> R0["return PHISHING, trail google_sb"]
    D -- "tidak cocok atau gagal" --> T0["trail google_sb tidak cocok"]
    C -- "tidak" --> T0
    T0 --> L["_load: Model B, tld_probs, stats (lazy singleton)"]
    L --> F["feed_status()"]
    F --> F1{"status ok dan is_denied(url)?"}
    F1 -- "ya" --> R1["return PHISHING, trail denylist cocok"]
    F1 -- "tidak" --> T1["trail denylist: tidak cocok, dilewati, atau tidak tersedia"]
    T1 --> A2{"is_trusted(host)?"}
    A2 -- "ya" --> R2["return LEGITIMATE, probability null, trail allowlist cocok"]
    A2 -- "tidak" --> T2["trail allowlist tidak cocok"]
    T2 --> E2["extract_features lalu predict_proba Model B"]
    E2 --> T3["trail model_b: zona skor"]
    T3 --> C2["_model_c_probability"]
    C2 --> T4["trail model_c: zona skor atau tidak tersedia"]
    T4 --> S["_decide: matriks zona dua model"]
    S --> T5["trail shortener"]
    T5 --> R3["return verdict, risk_level, decision_source, reason, probability, top_features, trail"]

    classDef stop fill:#f6d5d1,stroke:#c0392b,color:#111
    classDef pass fill:#d6ecd9,stroke:#2e7d32,color:#111
    classDef step fill:#eef3f7,stroke:#2c6e9b,color:#111
    class ERR stop
    class R0,R1 pass
    class R2,R3 pass
    class T0,T1,T2,T3,T4,T5,L,F,E2,C2,S step
```

## 3. Flowchart `sync_feeds.py` (`sync_feeds.mmd`)

```mermaid
flowchart TD
    A["main()"] --> B["mkdir data/feeds (FEED_DIR dari src/config.py)"]
    B --> C["urlopen https://openphish.com/feed.txt, timeout 60 detik"]
    C -- "gagal" --> E["print pesan ramah dan fallback manual, return 1"]
    C -- "berhasil" --> D["decode utf-8, errors=replace"]
    D --> F["stempel waktu UTC YYYYMMDD-HHMMSS"]
    F --> G["tulis openphish-stamp.txt, snapshot lama tidak ditimpa"]
    G --> H["hitung URL non-komentar"]
    H --> I["print path, jumlah URL, peringatan lisensi, return 0"]

    classDef fail fill:#f6d5d1,stroke:#c0392b,color:#111
    classDef ok fill:#d6ecd9,stroke:#2e7d32,color:#111
    classDef step fill:#eef3f7,stroke:#2c6e9b,color:#111
    class E fail
    class I ok
    class A,B,C,D,F,G,H step
```

Catatan sinkronisasi feed: `sync_feeds.py` adalah satu-satunya skrip yang membuka
jaringan secara rutin. Inferensi `predict_url` tetap offline kecuali L0 diaktifkan
lewat `PHISHGUARD_USE_GOOGLE=true`.
