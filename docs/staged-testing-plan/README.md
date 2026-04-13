# Staged Test Program

Dokumen di folder ini menggantikan pendekatan test plan tunggal dengan program pengujian bertahap yang lebih formal dan lebih dekat ke praktik industri.

## Tujuan Program

- Membangun coverage secara bertahap dengan urutan yang mengikuti dependency dan risiko bisnis.
- Menggunakan quality gate per modul: satu modul direncanakan, direview, lalu baru lanjut ke modul berikutnya.
- Menstandarkan struktur test plan agar setiap modul punya objective, scope, risk, scenario matrix, entry criteria, dan exit criteria yang konsisten.

## Standar Yang Diadopsi

Program ini mengikuti prinsip umum yang lazim dipakai pada tim QA dan software engineering modern:

- Risk-based testing: prioritas ditentukan oleh dampak bisnis dan peluang kegagalan.
- Testing pyramid: lebih banyak unit/service test, lebih sedikit UI-heavy integration test.
- Shift-left testing: validasi rule bisnis sedekat mungkin dengan model, form, service, dan signal.
- Traceability: setiap modul punya pemetaan antara risk area dan target test.
- Stage gate review: satu plan per modul direview sebelum lanjut ke plan berikutnya.
- Regression discipline: setiap defect penting harus menghasilkan regression test.

## Struktur Dokumen Per Modul

Setiap file module plan wajib memuat:

1. Objective
2. Scope in
3. Scope out
4. Dependency dan related modules
5. Risk assessment
6. Test levels
7. Scenario matrix
8. Test data strategy
9. Entry criteria
10. Exit criteria
11. Deliverables
12. Recommended execution order

## Urutan Tahap Semua Modul

Urutan ini disusun dari fondasi sistem ke workflow bisnis tingkat atas.

### Stage 1: Inventory Kernel

- `stock`

Alasan:

- Menjadi fondasi mutasi stok, transaction ledger, stock card, stock transfer, dan API pencarian stok.
- Hampir semua workflow lain bergantung pada ketepatan modul ini.

### Stage 2: Master Data Foundation

- `items`

Alasan:

- Menentukan validitas referensi item, satuan, kategori, program, lokasi, sumber dana, supplier, dan fasilitas.
- Kegagalan di sini menyebar ke receiving, distribution, stock, dan reports.

### Stage 3: Platform Access and Shared Behavior

- `core`
- `users`

Alasan:

- Menentukan kontrol akses, decorator behavior, dashboard shared behavior, role/group sync, dan module scope fallback.

### Stage 4: Inbound Inventory Flow

- `receiving`

Alasan:

- Entry point utama penambahan stok dan sumber transaksi `IN`.
- Memiliki CSV import, regular receiving, planned receiving, dan return RS.

### Stage 5: Outbound Inventory Flow

- `distribution`

Alasan:

- Workflow stok keluar paling penting dan paling sensitif secara operasional.
- Memiliki branch bisnis tambahan: `LPLPO`, `BORROW_RS`, dan `SWAP_RS`.

### Stage 6: Reverse and Disposal Flows

- `recall`
- `expired`

Alasan:

- Keduanya mengurangi stok dan menulis `Transaction(OUT)` dengan aturan bisnis yang berbeda.

### Stage 7: Reconciliation and Physical Control

- `stock_opname`

Alasan:

- Menjadi kontrol fisik terhadap akurasi stok sistem.
- Harus memverifikasi discrepancy behavior, bukan hanya akses.

### Stage 8: Facility Request and Routine Planning

- `puskesmas`
- `lplpo`

Alasan:

- Sangat bergantung pada facility isolation, workflow lintas modul, dan link ke distribution.

### Stage 9: Reporting and Decision Support

- `reports`

Alasan:

- Bergantung pada akurasi semua modul upstream.
- Paling tepat direncanakan setelah transaksi inti sudah punya baseline coverage yang kuat.

## Review Workflow

- Saya hanya akan membuat detail plan untuk satu modul aktif pada satu waktu.
- Setelah modul aktif direview dan disetujui, baru saya lanjut ke file plan modul berikutnya.
- Jika ada koreksi pada format atau depth, format itu akan dibawa ke modul-modul berikutnya agar konsisten.

## Modul Yang Sudah Disiapkan

- [01-stock-module-test-plan.md](01-stock-module-test-plan.md)
- [02-items-module-test-plan.md](02-items-module-test-plan.md)
- [03-users-uac-module-test-plan.md](03-users-uac-module-test-plan.md)
- [04-users-crud-module-test-plan.md](04-users-crud-module-test-plan.md)
- [05-core-module-test-plan.md](05-core-module-test-plan.md)

## Modul Aktif Saat Ini

Modul aktif untuk review berikutnya:

- [05-core-module-test-plan.md](05-core-module-test-plan.md)

## Deliverable Rules

- Nama file memakai prefix numerik untuk menjaga urutan review.
- Satu file hanya untuk satu modul utama.
- Related module disebut di dalam plan, tetapi tidak dibuatkan plan terpisah sampai modul itu menjadi giliran aktif.
