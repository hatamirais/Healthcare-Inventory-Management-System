# Program Stage Roadmap

Dokumen ini menjadi peta jalan tingkat program untuk seluruh staged testing plan. Tujuannya adalah memberi gambaran urutan eksekusi, alasan prioritas, dependency antar stage, dan quality gate yang harus dipenuhi sebelum melanjutkan ke stage berikutnya.

## Tujuan Roadmap

- Menyatukan seluruh module test plan ke dalam urutan program yang jelas dan dapat dieksekusi.
- Memastikan pengujian bergerak dari fondasi data ke workflow operasional, lalu ke laporan dan pengambilan keputusan.
- Mengurangi rework dengan mengunci kontrak shared layer lebih awal sebelum modul hilir bergantung padanya.
- Menjaga agar setiap stage memiliki entry criteria, exit criteria, dan alasan bisnis yang eksplisit.
- Menjadi referensi program sebelum detail plan per modul dibuat.

## Prinsip Penyusunan Stage

Roadmap ini mengikuti prinsip berikut:

- Risk-based testing: modul dengan dampak bisnis dan data tertinggi diuji lebih dahulu.
- Dependency-first sequencing: modul fondasi diuji sebelum modul hilir yang bergantung padanya.
- Shared-contract locking: decorator, UAC, singleton settings, dan shared context dikunci sebelum workflow lintas modul melebar.
- Regression discipline: setiap defect penting yang ditemukan selama implementasi stage harus menghasilkan regression test.
- Stage gate review: satu stage tidak dianggap selesai hanya karena file test bertambah; stage harus lolos quality gate yang disepakati.

## Stage 1: Inventory Integrity Foundation

Modul:

- `stock`

Fokus utama:

- integritas quantity per batch
- pairing `Transaction(IN/OUT)`
- `available_quantity` dan `reserved`
- transfer antar lokasi
- stock card dan lookup stok dasar

Alasan prioritas:

`stock` adalah fondasi seluruh mutasi inventaris. Hampir semua workflow lain bergantung pada ketepatan modul ini. Kesalahan pada layer ini akan merusak receiving, distribution, recall, expired, stock opname, dashboard, dan reports.

Risiko dominan:

- quantity salah pada batch tertentu
- transaction ledger tidak sinkron
- transfer tidak atomic atau tidak seimbang
- FEFO atau batch selection tidak valid

Deliverable utama:

- model dan rule tests
- transfer workflow tests dengan success, rejection, dan rollback
- available quantity dan reservation tests
- JSON API contract tests

Quality gate:

- semua critical stock mutation path memiliki assertion data, bukan hanya status response
- transaction `IN/OUT` pairing diverifikasi langsung
- tidak ada transfer flow tanpa regression coverage

## Stage 2: Master Data Reliability

Modul:

- `items`

Fokus utama:

- validitas item aktif dan nonaktif
- rule item program
- lookup normalization
- referensi supplier, location, category, funding source, dan facility

Alasan prioritas:

Referensi item yang tidak valid merusak receiving, distribution, stock, dan reports. Kegagalan master data menyebar luas dan sulit di-debug di modul hilir.

Risiko dominan:

- item nonaktif masih bisa dipilih di workflow operasional
- metadata item tidak valid merusak transaksi
- normalisasi lookup tidak konsisten
- referensi soft-deleted tidak difilter dengan benar

Deliverable utama:

- CRUD dan validation tests
- soft-delete visibility tests
- lookup dan quick-create tests
- normalization dan uniqueness tests

Quality gate:

- item nonaktif dikecualikan dari semua flow operasional
- rule bisnis item program tercakup
- semua lookup penting memiliki deterministic test

## Stage 3: Access Control and Shared Platform Layer

Modul:

- `users`
- `core`

Fokus utama:

- role dan group sync
- module scope fallback
- decorator behavior lintas modul
- dashboard aggregation dan scoping
- singleton system settings
- context processor global

Alasan prioritas:

Layer ini menentukan kontrol akses untuk seluruh aplikasi. Decorator, UAC, dan context processor dipakai oleh setiap modul lain. Kegagalan di sini mengakibatkan permission leakage atau false denial yang sulit dilacak di modul hilir.

Risiko dominan:

- permission leakage antar modul
- facility scoping yang salah di dashboard Puskesmas
- notification bell menghitung dokumen secara salah
- singleton settings tidak konsisten

Deliverable utama:

- role dan group sync tests
- decorator allow-path dan deny-path tests
- dashboard aggregation tests
- notification logic tests
- singleton settings regression tests

Urutan sub-modul yang direkomendasikan:

1. `users` UAC
2. `users` CRUD
3. `core`

Quality gate:

- decorator contract diverifikasi langsung, bukan hanya via view test
- facility isolation Puskesmas dibuktikan
- shared context dan global behavior stabil di kondisi fallback

## Stage 4: Inbound Inventory Flow

Modul:

- `receiving`

Fokus utama:

- workflow dokumen penerimaan
- regular receiving dan planned receiving
- return RS receiving
- CSV import
- stock increment dan `Transaction(IN)` side effect

Alasan prioritas:

`receiving` adalah entry point utama penambahan stok. Setelah fondasi data dan platform layer stabil, alur masuk stok harus diverifikasi sebelum alur keluar diuji.

Risiko dominan:

- `Transaction(IN)` tidak dibuat atau nilai salah
- CSV import membuat data tidak konsisten
- planned vs regular receiving divergen di edge case
- return RS mismatch dengan distribusi asal
- rollback gagal pada transisi status invalid

Deliverable utama:

- workflow tests untuk semua path status
- CSV import happy path dan error handling
- planned vs regular receiving distinction tests
- stock increment dan transaction side effect assertions
- permission dan scope tests

Quality gate:

- setiap receiving path yang mengubah stok memiliki assertion data langsung
- CSV import memiliki coverage happy path dan baris tidak valid
- transisi status tidak valid diblokir dan diuji

## Stage 5: Outbound Inventory Flow

Modul:

- `distribution`

Fokus utama:

- workflow distribusi dari DRAFT ke DISTRIBUTED
- alokasi stok dan deduction
- `BORROW_RS` dan `SWAP_RS`
- outstanding quantity dan value
- step-back dan reset actions

Alasan prioritas:

Distribution adalah workflow stok keluar paling operasional dan paling sensitif. Bergantung pada stok yang sudah stabil, master data yang valid, dan access control yang terkunci.

Risiko dominan:

- over-allocation atau under-deduction stok
- outstanding quantity atau value salah
- RS settlement mismatch dengan receiving asal
- transisi status tidak valid lolos guard

Deliverable utama:

- full workflow state transition tests
- `BORROW_RS` dan `SWAP_RS` settlement tests
- outstanding quantity dan value tests
- reserved vs distributed quantity assertions
- step-back dan reset behavior tests

Quality gate:

- semua transisi stok keluar memiliki guard-path test
- outstanding metric diverifikasi langsung
- settlement behavior terbukti end-to-end

## Stage 6: Reverse and Disposal Flows

Modul:

- `recall`
- `expired`

Fokus utama:

- workflow pengembalian ke supplier
- workflow disposal barang kadaluarsa
- `Transaction(OUT)` side effect
- guard status transition

Alasan prioritas:

Keduanya mengurangi stok dan menulis `Transaction(OUT)` dengan aturan bisnis yang berbeda dari distribution. Bergantung pada stok yang stabil dan permission layer yang terkunci.

Risiko dominan:

- penghapusan stok tidak otorisasi
- `OUT` transaction tidak dibuat atau salah
- audit trail tidak lengkap
- transisi status invalid lolos validasi

Deliverable utama:

- recall workflow tests
- expired workflow tests
- transaction side effect assertions
- permission dan guard tests
- disposal dan reversal regression tests

Quality gate:

- setiap pengurangan stok membuat side effect ledger yang benar
- restrict dan reject path diuji
- audit integrity diverifikasi

## Stage 7: Physical Reconciliation

Modul:

- `stock_opname`

Fokus utama:

- create, progress, dan complete workflow
- discrepancy computation
- location dan facility scoping
- adjustment result

Alasan prioritas:

`stock_opname` adalah kontrol fisik terhadap akurasi stok sistem. Harus datang setelah stok sudah cukup andal sebagai pembanding.

Risiko dominan:

- discrepancy logic salah
- completion flow tidak mencerminkan variance aktual
- hitungan bocor lintas lokasi atau fasilitas
- workflow hanya diuji access, bukan reconciliation accuracy

Deliverable utama:

- create dan complete workflow tests
- discrepancy computation tests
- adjustment result tests
- filter dan list tests
- permission dan isolation tests

Quality gate:

- discrepancy behavior diverifikasi secara numerik
- completion path diuji melebihi HTTP response
- hasil rekonsiliasi divalidasi

## Stage 8: Facility Request and Planning Workflows

Modul:

- `puskesmas`
- `lplpo`

Fokus utama:

- facility isolation
- request dan review lifecycle
- LPLPO submission dan review
- dashboard dan notifikasi facility-scoped
- link ke distribution

Alasan prioritas:

Kedua modul ini bergantung pada facility isolation yang stabil, access control yang terkunci, dan distribution yang sudah punya baseline coverage.

Risiko dominan:

- cross-facility data leakage
- request atau LPLPO dari fasilitas lain terlihat
- review atau approval behavior salah
- link ke distribution atau replenishment tidak konsisten

Deliverable utama:

- facility isolation tests
- request lifecycle tests
- LPLPO submission dan review tests
- scope-based action tests

Quality gate:

- tidak ada fasilitas yang dapat melihat atau mengubah data fasilitas lain
- transisi submission dan review diblokir tanpa akses yang tepat
- integrasi downstream diverifikasi

## Stage 9: Reporting and Decision Support

Modul:

- `reports`

Fokus utama:

- akurasi agregat
- filter dan pagination
- export dan print output
- cross-check terhadap data transaksional

Alasan prioritas:

Reports adalah read-model layer terakhir. Kualitas laporan bergantung pada akurasi semua modul upstream. Menguji reports terlalu awal menghasilkan noise dari modul yang belum stabil.

Risiko dominan:

- aggregate salah menghitung atau double count
- filter tidak bekerja dengan benar
- export atau print rusak
- laporan kritis tidak merefleksikan data operasional

Deliverable utama:

- smoke tests untuk semua laporan utama
- accuracy tests untuk laporan operasional kritis
- filter dan pagination tests
- export dan print response tests

Quality gate:

- laporan kritis memiliki assertion data, bukan hanya status 200
- export dan print output divalidasi secara struktural
- tidak ada laporan kritis yang menjadi blind spot

## Urutan Review Modul yang Direkomendasikan

Urutan ini adalah urutan eksekusi yang disarankan untuk membuat detail plan dan menjalankan pengujian:

1. `01-stock-module-test-plan.md`
2. `02-items-module-test-plan.md`
3. `03-users-uac-module-test-plan.md`
4. `04-users-crud-module-test-plan.md`
5. `05-core-module-test-plan.md`
6. `06-receiving-module-test-plan.md`
7. `07-distribution-module-test-plan.md`
8. `08-recall-module-test-plan.md`
9. `09-expired-module-test-plan.md`
10. `10-stock-opname-module-test-plan.md`
11. `11-puskesmas-module-test-plan.md`
12. `12-lplpo-module-test-plan.md`
13. `13-reports-module-test-plan.md`

## Governance Program

### Entry Criteria Per Stage

Stage siap dieksekusi bila:

- modul target sudah termigrasi penuh
- modul upstream pada dependency langsung sudah memenuhi exit criteria
- strategi fixture minimal sudah disepakati
- peta status dan workflow utama modul sudah teridentifikasi

### Exit Criteria Per Stage

Stage dianggap selesai bila:

- semua critical scenario memiliki automated test
- minimal 80 persen high-priority scenario memiliki automated test
- success path dan deny/failure path keduanya diuji
- setiap workflow yang mengubah stok atau menulis transaksi memiliki assertion data langsung
- tidak ada regression dari defect modul yang ditemukan selama implementasi

### Aturan Lintas Stage

Aturan-aturan berikut berlaku untuk seluruh program:

- Setiap workflow yang mengubah stok harus memiliki assertion perubahan data, bukan hanya status code.
- Setiap protected action harus memiliki allow-path test dan deny-path test.
- Setiap bug fix harus menghasilkan regression test.
- Modul dengan facility scope harus memiliki isolation test.
- Reports divalidasi terhadap data fixture yang diketahui nilainya.
- Shared fixtures sebaiknya bergerak ke helper atau factory yang dapat dipakai ulang, terutama untuk:
  - user dan role
  - fasilitas
  - item
  - stok dan transaksi
  - dokumen workflow umum
