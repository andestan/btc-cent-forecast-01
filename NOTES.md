# Catatan model & hasil uji — btc-cent-forecast-01

## Lomba (dicek 15 Nov 2026 ~13:00 WIB)

- Slug: `btc-cent-forecast-01` — "Forecast Bitcoin's price 4 hours ahead,
  12 times over 48 hours"
- Status: open. Deadline entry: **15 Nov 2026 08:00 UTC = 15:00 WIB**.
- Hadiah total $250 USDC (escrow on-chain, sudah terkunci penuh):
  1st $40, 2nd $25, 3rd $15, 4–10 masing-masing $5, 11–100 masing-masing $1,50.
- Peserta saat dicek: **3.802 submission** (angka "agents" di halaman).
- Final: 12 checkpoint (h00–h11) tiap 4 jam mulai deadline sampai +44 jam;
  target tiap checkpoint = close 240 menit setelahnya. Hasil final paling
  lambat 1 Des 2026.
- Satu entry per akun (max_total = 1, max 1/hari). **Hanya ada satu
  kesempatan submit — tidak bisa coba-coba lalu perbaiki.**
- Biaya entry: $0.

## Aturan main program (dari kit RULES.txt)

- Entrypoint `main.py` (Python 3.13) atau `main.ts` (Node 22) di root repo,
  hanya standard library, tanpa network, tanpa model call.
- Input: `/input/<id>.in`, JSON: `{"schema": "makefun/btc-cent-case/v1",
  "competition", "case", "at", "horizon_minutes": 240,
  "markets": [{"id": "btc-usdc", "name", "start",
  "prices": [4.320 close 1-menit, terakhir = close checkpoint]}]}`.
  Harga = cbBTC/USDC di Orca Whirlpool (bukan harga Binance/OKX).
- Output: `/output/<id>.out`, JSON persis
  `{"forecasts": [{"case": "<id>", "price": <angka>}]}`
  0 < price < 10.000.000. Baca `$MAKEFUN_INPUT_DIR`/`$MAKEFUN_OUTPUT_DIR`
  kalau di-set, kalau tidak pakai `/input` dan `/output`.
- Maks 8 detik, 1 CPU, 1024 MB per case. Dua run pada case yang sama harus
  menghasilkan byte yang identik (deterministik).
- Skor: MAE dalam cents = 100 × rata-rata |tebakan − close aktual| dari
  12 case. Paling rendah menang. **Hadiah butuh skor di bawah baseline
  house (persistence: tebakan = close checkpoint) DAN semua case valid.**
  Case invalid = dinilai seperti tebakan = close checkpoint, dan entry
  dengan case invalid apa pun tidak dapat hadiah.
- Baseline practice (6 case p00–p05, dari RULES.txt): MAE 44.521,576667
  cents (rata-rata error $445,22; terburuk $766,97). Skor practice BUKAN
  patokan final — final dinilai pada harga 15–17 Nov yang belum terjadi.

## Model yang dipilih

```
forecast = 0,75 * close_checkpoint + 0,25 * EMA_180(close 72 jam)
```

EMA_180 = exponential moving average span 180 menit (alpha = 2/181) atas
4.320 close. Alasan:

1. Harga BTC 4 jam ke depan hampir seperti random walk. Ekstrapolasi tren
   justru merusak: di backtest, model slope OLS 6/12/24 jam dan AR(1)
   return 4 jam hasilnya +3% sampai +55% LEBIH BURUK dari persistence.
2. Close checkpoint mengandung noise mikrostruktur (harga satu pool Orca;
   satu trade besar bisa menggesernya sesaat), sementara target juga
   satu close menit tunggal. Mencampur 25% EMA mengurangi noise itu
   tanpa ketinggalan jauh saat tren berjalan. EMA penuh (100%) malah
   +13,6% lebih buruk karena lag.
3. Tidak ada penyesuaian jam (time-of-day): rata-rata return 4 jam per jam
   checkpoint (00/04/08/12/16/20 UTC) mediannya semua mendekati nol
   (±0,13%); yang tampak di mean hanya efek outlier crash.

## Hasil uji lokal (MAE cents; makin kecil makin baik)

Data uji 1: OKX BTC-USDT close 1-menit, 19 Okt–15 Nov 2026 (38.100 bar,
di `data/btc_usdt_1m_okx.csv`), checkpoint tiap 4 jam, n=139.
Data ini PROXY — harga OKX bukan harga Orca cbBTC, tapi pola geraknya
sama dan sampelnya besar (banyak rezim: reli Okt, crash Nov).

| Model | MAE semua (n=139) | vs persistence | Tune 23 Okt–8 Nov (n=102) | Validasi 9–15 Nov, rezim crash (n=37) |
|---|---|---|---|---|
| **Dipilih: 0,75·last + 0,25·EMA180** | **43.782** | **−1,37%** | −1,29% | −1,54% |
| 0,75·last + 0,25·EMA120 | 43.776 | −1,39% | −1,42% | −1,32% |
| 0,80·last + 0,20·EMA120 | 43.780 | −1,38% | −1,46% | −1,23% |
| Persistence (baseline) | 44.392 | 0% | 0% | 0% |
| AR(1) return 4 jam, damp 0,5 | 44.325 | −0,15% | +1,12% | −2,54% |
| Drift OLS 12 jam, damp 0,25 | 45.731 | +3,02% | +3,89% | +1,37% |
| Drift OLS 12 jam, damp 0,5 | 48.396 | +9,02% | +11,02% | +5,26% |
| Mean-reversion 72 jam, α=0,10 | 46.342 | +4,39% | +2,18% | +8,56% |

Data uji 2: seri cbBTC ASLI dari kit (gabungan 6 file practice,
7 Nov 06:01–11 Nov 02:00 UTC, tanpa gap), checkpoint tiap jam 10 Nov,
n=17. Model dipilih: **−4,29% vs persistence** (49.808 vs 52.041 cents).
Smoothing membantu LEBIH BESAR di data Orca asli daripada di OKX —
konsisten dengan noise mikrostruktur pool yang lebih besar.

Data uji 3: 6 case practice resmi (aktual p00–p04 dirantai dari file kit;
aktual p05 = $73.864,44, disimpulkan dari total baseline practice yang
dipublikasikan 44.521,576667 cents, dan dikonfirmasi arahnya oleh close
OKX $73.929 pada 11 Nov 06:00 UTC — selisih $65 adalah basis wajar
Orca vs OKX). Model dipilih: MAE **45.552,22 cents** vs persistence
44.521,58 cents (**+2,31%**). n=6 terlalu kecil untuk dipercaya: satu
case (p01, error $767) mendominasi, dan hasilnya bertentangan dengan
kedua uji yang sampelnya lebih besar. Practice BUKAN patokan final.

**Penilaian jujur:** keunggulan model ini ~1–1,5% pada sampel besar
(n=139, selisih ≈1,2–1,4× standard error) — mengarah benar, tapi TIDAK
terbukti secara statistik. Model ini mengalahkan persistence di SETIAP
split out-of-sample (tune, validasi crash, seri cbBTC per jam), itu
sinyal robustness terbaik yang tersedia. Final hanya 12 case, jadi
keberuntungan akan sangat menentukan; ini perkiraan terbaik yang bisa
dibuat, bukan jaminan menang. Perkiraan peluang masuk 100 besar: kecil
(3.802 submission, 100 tempat); perkiraan hadiah yang diharapkan kalau
masuk pun hanya $1,50–$40.

## Uji program (main.py) — semua lolos

- Dijalankan per case seperti grader (`python3 -P -s main.py`, env
  `MAKEFUN_INPUT_DIR`/`MAKEFUN_OUTPUT_DIR` di-set): 6/6 case practice
  menghasilkan output valid. Juga lolos saat env TIDAK di-set (pakai
  `/input` dan `/output` bawaan) dan saat 6 case dalam satu folder input.
- Format output dicek: persis `{"forecasts": [{"case", "price"}]}`
  price di dalam (0, 10.000.000), 5 desimal.
- Deterministik: 2 run menghasilkan file byte-identik (`diff` kosong).
- Kecepatan: ~0,05 detik per case (batas 8 detik).
- Fallback: case rusak (harga tidak valid) tetap menulis tebakan =
  close checkpoint dan exit 0 — jadi tidak pernah ada case invalid
  karena crash; yang terburuk adalah skor setara baseline.
- Per-case practice (model vs persistence, $): p00 308,48 vs 317,11;
  p01 780,13 vs 766,97; p02 586,45 vs 470,33; p03 556,19 vs 566,85;
  p04 197,78 vs 231,47; p05 304,11 vs 318,56.

## Yang BELUM dilakukan (butuh keputusan Andes)

- TIDAK dibuat: keypair Solana baru, register/sign-in make.fun,
  submit entry, repo GitHub publik.
- Yang masih dibutuhkan untuk submit:
  1. Persetujuan Andes atas draf ini dan atas wallet payout
     `CbL1Kgj4FqfMxkDjf6KgYLzEz48tUfUMo5wmHD6MPwj1` (alamat publik
     milik Andes; TIDAK ADA seed phrase/private key yang diminta
     atau disimpan — jangan pernah dibagikan).
  2. Repo GitHub publik BARU (dibuat SETELAH kompetisi dibuka
     14 Nov 2026 20:00 UTC), berisi `main.py`, `LICENSE`, `README.md`,
     `.makefun/owner.json` (sudah disiapkan; ganti
     `ANDES-GITHUB-OWNER`/`btc-cent-forecast` di badge README dengan
     owner/repo GitHub yang sebenarnya, dan isi About repo: deskripsi,
     homepage https://make.fun/bounty/btc-cent-forecast-01, topik
     makefun, ai-agents, bounties, forecasting).
  3. Tanda tangan entry dengan wallet yang terhubung ke akun make.fun
     milik Andes (via `node cli/makefun.mjs submit ... --keypair`,
     atau delegasi payout ke wallet di atas lewat Phantom milik Andes).
  4. Bundle transkrip sesi agent yang membangun entry ini — WAJIB,
     dan ini titik rawan: `handed_over_places = none`, jadi kalau
     transkrip hanya "handed-over" (bukan log harness yang terekam),
     entry tetap dinilai tapi TIDAK BISA dapat tempat berbayar.
     Sesi ini juga harus memenuhi transcript gate: ≥30% baris kode
     dipertanggungjawabkan transkrip, ≥5 assistant turn, usage
     tercatat, dan (per `competition.yaml`) `min_authored_coverage: 0.8`.
     Pengiriman dari Muse app butuh `--muse-usage` (baris usage dari
     database Muse) — ini harus dicek dengan kit sebelum submit.
  5. Submit SEBELUM 15 Nov 2026 15:00 WIB — dan karena hanya 1 entry
     per akun, submit pertama = submit final, tidak bisa diperbaiki
     setelahnya.
