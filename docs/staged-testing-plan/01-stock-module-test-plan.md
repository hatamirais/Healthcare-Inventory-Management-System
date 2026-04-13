# Stock Module Test Plan

## Objective

Memastikan modul `stock` menjaga integritas inventaris per batch, menghasilkan audit trail yang benar, dan menyediakan data yang konsisten untuk workflow hilir seperti receiving, distribution, recall, expired, stock opname, dan reports.

## Scope In

Komponen dalam cakupan plan ini:

- model `Stock`
- model `Transaction`
- model `StockTransfer`
- model `StockTransferItem`
- property turunan seperti `available_quantity`, `total_value`, `is_expired`, `is_near_expiry`
- view `stock_list`
- view `transaction_list`
- `stock_card_select`
- `stock_card_detail`
- `transfer_list`
- `transfer_create`
- `transfer_detail`
- `transfer_complete`
- endpoint `api_item_search`
- endpoint `api_location_stock_search`
- admin rules untuk `Transaction` dan `StockTransfer`

## Scope Out

Di luar plan ini:

- workflow receiving detail
- workflow distribution detail
- workflow recall dan expired detail
- report rendering detail
- dashboard aggregation detail

Catatan:

Interaksi dengan modul lain tetap diuji sebatas kontrak yang dibutuhkan modul `stock`, bukan behavior penuh modul terkait.

## Related Modules and Dependencies

Related modules yang harus diperhatikan ketika test disusun:

- `items`: item, location, funding source, dan master reference lain
- `users`: autentikasi user dan permission
- `receiving`: sumber transaksi `IN`
- `distribution`: sumber transaksi `OUT`
- `recall`: sumber transaksi `OUT`
- `expired`: sumber transaksi `OUT`

Dependency teknis utama:

- Django ORM transaction handling
- unique constraint pada kombinasi stok
- `select_for_update()` pada completion transfer
- pagination dan filtering list view

## Business Risks

### Critical Risks

1. Pengurangan atau penambahan stok salah pada batch tertentu.
2. `Transaction` tidak selaras dengan perubahan stok aktual.
3. Transfer stok menghasilkan quantity sumber dan tujuan yang tidak seimbang.
4. Batch yang reserved tetap bisa dipindah atau dipakai melebihi `available_quantity`.

### High Risks

1. Stock card menampilkan running balance yang salah.
2. API stok menampilkan batch tidak valid, batch salah lokasi, atau batch tanpa availability.
3. Transfer completed dua kali atau completed pada draft invalid state.
4. Filter list dan pagination menutupi data penting secara tidak konsisten.

### Medium Risks

1. Perhitungan near-expiry atau expired salah di boundary date.
2. Search endpoint terlalu longgar atau mengembalikan item inactive.
3. Admin memungkinkan perubahan data yang seharusnya immutable.

## Quality Targets

Target kualitas untuk modul ini:

- Semua perubahan stok yang berasal dari modul `stock` harus memiliki assertion terhadap stock quantity dan `Transaction`.
- Semua state transition pada `StockTransfer` harus punya positive path dan negative path.
- Semua property inti model harus memiliki unit test untuk normal case dan boundary case.
- Semua endpoint JSON harus memiliki contract test untuk shape data dan filtering utama.
- Tidak ada behavior kritis yang hanya diuji lewat template response `200` saja.

## Test Levels

### Level 1: Model and Rule Tests

Fokus:

- constraint bisnis
- property perhitungan
- validasi `clean()`
- document number generation

### Level 2: Service-Like Workflow Tests

Fokus:

- transfer completion sebagai workflow atomic
- quantity movement source ke destination
- paired transaction creation
- guard terhadap invalid state dan insufficient stock

### Level 3: View and Endpoint Tests

Fokus:

- search
- filter
- pagination
- access control
- response contract JSON
- running balance di stock card

### Level 4: Admin Policy Tests

Fokus:

- `TransactionAdmin` immutable policy
- `StockTransferAdmin` inline behavior dasar
- import resource behavior untuk `Stock`

## Scenario Matrix

### A. Stock Model

Priority: Critical

Scenarios:

1. `available_quantity` mengembalikan `quantity - reserved`.
2. `total_value` mengembalikan `quantity * unit_price`.
3. `is_expired` bernilai true saat expiry sama dengan hari ini.
4. `is_near_expiry` true untuk expiry dalam 90 hari dan false bila sudah expired.
5. Constraint `quantity >= 0` ditolak saat invalid.
6. Constraint `reserved >= 0` ditolak saat invalid.
7. Unique stock tuple `(item, location, batch_lot, sumber_dana)` tidak boleh duplikat.

### B. Transaction Model

Priority: Critical

Scenarios:

1. Ordering default newest-first tetap konsisten.
2. String representation tidak kosong dan mengandung identitas transaksi.
3. Transaction list filter per type bekerja.
4. Search transaction bekerja pada item code, nama barang, batch, dan notes.

### C. Stock Transfer Model Rules

Priority: Critical

Scenarios:

1. `generate_document_number()` menghasilkan format `TRF-YYYY-NNNNN`.
2. Save tanpa nomor dokumen menghasilkan nomor otomatis.
3. Source dan destination location tidak boleh sama.
4. `StockTransferItem.clean()` menolak quantity `<= 0`.
5. `StockTransferItem.clean()` menolak item yang tidak cocok dengan stock source.

### D. Transfer Create Workflow

Priority: High

Scenarios:

1. User berizin dapat membuat transfer draft dengan minimal satu line valid.
2. Line dengan quantity kosong dilewati, bukan membuat line invalid.
3. Line dengan quantity non-numeric diabaikan dan tidak membuat crash.
4. Transfer gagal dibuat bila semua line invalid.
5. Stock dari lokasi berbeda dengan source location ditolak.
6. Quantity melebihi `available_quantity` tidak dibuat.
7. User tanpa permission ditolak.

### E. Transfer Complete Workflow

Priority: Critical

Scenarios:

1. Draft valid dapat di-complete dan status berubah ke `COMPLETED`.
2. Completion mengurangi source stock sesuai quantity.
3. Completion menambah existing destination stock bila tuple batch sudah ada.
4. Completion membuat destination stock baru bila batch belum ada.
5. Completion membuat dua `Transaction` per line: `OUT` dari source dan `IN` ke destination.
6. Completion men-set `completed_by` dan `completed_at`.
7. Transfer non-draft tidak boleh di-complete ulang.
8. Transfer tanpa item ditolak.
9. Transfer gagal bila source stock tidak cukup.
10. Transfer gagal bila batch ternyata bukan milik source location dokumen.
11. Kegagalan pada satu line membatalkan seluruh atomic workflow.

### F. Stock Card Views

Priority: High

Scenarios:

1. `stock_card_select` tampil untuk user login.
2. Recent item session hanya memuat item aktif.
3. `stock_card_detail` menghitung opening balance benar saat ada `date_from`.
4. `stock_card_detail` menghitung closing balance dan running balance benar.
5. Filter lokasi hanya menampilkan transaksi lokasi terkait.
6. Transfer internal dikecualikan dari total external bila tanpa filter lokasi.
7. Referensi label dokumen di-resolve ke nomor dokumen bila data tersedia.
8. Input tanggal invalid tidak meledakkan view.

### G. List and Search Views

Priority: High

Scenarios:

1. `stock_list` hanya menampilkan stok dengan `quantity > 0`.
2. Search di `stock_list` bekerja untuk kode barang, nama, dan batch.
3. Filter lokasi dan sumber dana bekerja bersama.
4. Pagination `25 per page` bekerja untuk boundary 25 dan 26 row.
5. `transaction_list` filter type dan search dapat digabung.

### H. JSON API Contracts

Priority: High

Scenarios:

1. `api_item_search` mengembalikan result kosong saat query kosong.
2. `api_item_search` hanya mengembalikan item aktif.
3. `api_item_search` membatasi hasil maksimum 20.
4. `api_item_search` memuat field `id`, `text`, `satuan`, `kategori`, dan `stock`.
5. `api_location_stock_search` mengembalikan kosong bila location tidak diberikan.
6. `api_location_stock_search` hanya menampilkan stock dengan `quantity > reserved`.
7. Ordering FEFO pada `api_location_stock_search` benar.
8. Query filter bekerja untuk item code, nama, kategori, dan batch.
9. User tanpa permission yang cukup ditolak dari endpoint location stock.

### I. Admin Policy

Priority: Medium

Scenarios:

1. `TransactionAdmin.has_change_permission()` selalu false.
2. `TransactionAdmin.has_delete_permission()` selalu false.
3. `StockResource` import identifier sesuai tuple import yang didefinisikan.
4. `StockTransferAdmin` menampilkan inline item tanpa membuka hak edit yang tidak semestinya.

## Test Data Strategy

Gunakan data minimal tetapi representatif:

- 1 superuser
- 1 user gudang dengan permission terbatas
- 2 lokasi aktif
- 1 lokasi inactive untuk filter negatif bila perlu
- 2 item aktif dan 1 item inactive
- 2 batch pada item yang sama untuk verifikasi FEFO
- 1 funding source utama dan 1 pembanding
- kombinasi source stock dengan reserved > 0 untuk test availability

Prinsip data:

- Gunakan `setUpTestData()` untuk master reference yang tidak berubah.
- Gunakan `setUp()` hanya untuk state yang dimutasi test tertentu.
- Hindari pembuatan fixture berulang jika helper test dapat dipakai ulang.

## Recommended Test File Layout

Struktur yang direkomendasikan untuk implementasi modul ini:

```text
backend/apps/stock/tests/
|- test_models.py
|- test_stock_card_views.py
|- test_transfer_workflow.py
|- test_list_views.py
|- test_api.py
`- test_admin.py
```

Jika repo belum dipecah ke package test per modul, transisi dapat dilakukan bertahap dengan menjaga backward compatibility import Django test discovery.

## Entry Criteria

Plan ini siap dieksekusi bila:

- fixture dasar item, lokasi, funding source, dan user sudah bisa dibuat konsisten
- command test per app berjalan stabil
- tidak ada migration pending yang mempengaruhi model `stock`

## Exit Criteria

Modul `stock` dianggap memenuhi baseline plan ini bila:

- semua critical scenario punya automated test
- minimal 80 persen high-priority scenario punya automated test
- workflow `transfer_complete` memiliki success, rejection, dan rollback test
- stock card memiliki test running balance dan filter utama
- JSON API memiliki contract test untuk response shape dan filtering penting

## Deliverables

Deliverable yang diharapkan dari implementasi plan ini:

1. File test baru atau refactor file test lama sesuai layout yang disetujui.
2. Shared helper atau factory bila dibutuhkan oleh lebih dari satu file stock test.
3. Catatan regression untuk defect yang ditemukan selama implementasi.

## Recommended Execution Order

Urutan implementasi test untuk modul `stock`:

1. `test_models.py`
2. `test_transfer_workflow.py`
3. `test_api.py`
4. `test_stock_card_views.py`
5. `test_list_views.py`
6. `test_admin.py`

Urutan ini dipilih agar rule inti dan workflow stok tervalidasi sebelum view-level dan admin-level coverage ditambah.