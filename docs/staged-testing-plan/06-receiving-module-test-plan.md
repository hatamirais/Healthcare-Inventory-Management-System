# Receiving Module Test Plan

## Objective

Memastikan modul `receiving` menangani seluruh alur masuk inventaris secara valid, menciptakan atau menginkrementasi `Stock` dengan benar, menghasilkan audit trail `Transaction(IN)` yang akurat, dan menjaga dokumen workflow tetap aman dari transisi status yang tidak valid.

## Scope In

Komponen dalam cakupan plan ini:

- model `Receiving`
- model `ReceivingItem`
- model `ReceivingOrderItem`
- model `ReceivingDocument`
- model `ReceivingTypeOption`
- property turunan seperti `is_rs_return`, `receiving_type_label`, `remaining_quantity`, `total_price`
- `generate_document_number()` pada `Receiving`
- view `receiving_list`
- view `receiving_create`
- view `receiving_detail`
- view `receiving_plan_list`
- view `receiving_plan_create`
- view `receiving_plan_detail`
- view `receiving_plan_submit`
- view `receiving_plan_approve`
- view `receiving_plan_receive`
- view `receiving_plan_close`
- view `receiving_plan_close_items`
- view `rs_return_list`
- view `rs_return_create`
- view `rs_return_from_borrow_create`
- view `rs_return_detail`
- endpoint `quick_create_supplier`
- endpoint `quick_create_funding_source`
- endpoint `quick_create_receiving_type`
- logika pembuatan `Stock` dan `Transaction(IN)` saat receiving terverifikasi
- admin CSV import untuk `Receiving` dan `ReceivingItem`
- helper `_validate_rs_return_items` dan `_get_prefillable_borrow_rs_distribution`

## Scope Out

Di luar plan ini:

- workflow distribution secara penuh, termasuk outstanding settlement behavior yang bukan dikontrak langsung oleh receiving
- full admin CRUD untuk master data items, location, atau funding source
- laporan dan agregasi dashboard dari data receiving
- template styling dan visual presentation

Catatan:

Plan ini menguji kontrak receiving sebagai alur masuk stok. Behavior detail pada `distribution`, `stock`, `items`, `reports`, dan modul lain tetap dimiliki oleh plan modul masing-masing. Interaksi dengan modul lain diuji sebatas kontrak langsung yang disentuh oleh receiving.

## Related Modules and Dependencies

Related modules yang harus diperhatikan ketika test disusun:

- `items`: `Item`, `Supplier`, `FundingSource`, `Location`, `Facility` sebagai referensi utama
- `stock`: `Stock` dan `Transaction` sebagai target side effect saat receiving diverifikasi
- `distribution`: `Distribution` dan `DistributionItem` sebagai referensi untuk RS return settlement
- `users`: autentikasi, role, dan module scope sebagai gatekeeper akses
- `core`: decorator `perm_required` dan `module_scope_required`

Dependency teknis utama:

- Django `transaction.atomic()` untuk operasi verifikasi receiving
- `select_for_update()` untuk guard duplikat verifikasi
- formset inline untuk `ReceivingItem` dan `ReceivingOrderItem`
- `setUpTestData()` untuk fixture master reference yang mahal dibuat ulang
- unique constraint pada `document_number` di `Receiving`

## Business Risks

### Critical Risks

1. Stock tidak bertambah atau bertambah dengan nilai yang salah saat receiving diverifikasi.
2. `Transaction(IN)` tidak dibuat atau dibuat dengan quantity, batch, atau referensi dokumen yang salah.
3. CSV import menciptakan records tidak konsisten atau melewati validasi yang harusnya gagal.
4. Return RS mismatch dengan distribusi asal, menyebabkan outstanding quantity tidak akurat.
5. Rollback tidak terjadi saat proses verifikasi gagal di tengah jalan, meninggalkan partial state.

### High Risks

1. Planned receiving status transition salah, seperti APPROVED langsung ke RECEIVED tanpa submit.
2. Regular receiving dibuat sebagai VERIFIED tetapi stock increment tidak terjadi.
3. ReceivingTypeOption nonaktif masih bisa dipilih di form.
4. `quick_create_supplier` atau `quick_create_funding_source` dapat dibuat oleh user tanpa scope yang cukup.
5. Document number `RCV-YYYY-NNNNN` tidak unik atau formatnya salah.

### Medium Risks

1. `remaining_quantity` pada `ReceivingOrderItem` menghitung nilai negatif atau melebihi `planned_quantity`.
2. `receiving_type_label` fallback ke custom type tidak berjalan ketika built-in choices tidak cocok.
3. Filter dan pagination list view menyembunyikan data secara tidak konsisten.
4. Admin import tidak menulis `Transaction(IN)` saat dipakai untuk initial stock seeding.

## Quality Targets

Target kualitas untuk modul ini:

- Setiap receiving path yang mengubah stok harus memiliki assertion terhadap `Stock.quantity` dan `Transaction`, bukan hanya response HTTP.
- Semua transisi status pada `Receiving` harus punya positive path dan negative path.
- CSV import harus memiliki happy path test dan test untuk baris tidak valid atau data tidak lengkap.
- Return RS flow harus diverifikasi terhadap settlement linkage dan outstanding quantity distribution asal.
- Tidak ada behavior kritis yang hanya diuji lewat template response `200` saja.

## Test Levels

### Level 1: Model and Rule Tests

Fokus:

- document number generation
- property turunan pada `Receiving` dan `ReceivingOrderItem`
- custom type label resolution
- constraint dan validasi model dasar

### Level 2: Workflow Tests

Fokus:

- regular receiving: create, detail, verify
- planned receiving: create, submit, approve, receive, close
- return RS receiving: create, prefill dari BORROW_RS, validate settlement, verify
- guard terhadap transisi status invalid

### Level 3: Stock and Transaction Side Effect Tests

Fokus:

- stock creation bila batch belum ada
- stock increment bila batch sudah ada
- `Transaction(IN)` creation per line item
- atomicity dan rollback saat verifikasi gagal
- RS return settlement update pada `outstanding_quantity`

### Level 4: Import Tests

Fokus:

- CSV import happy path menulis receiving, items, stock, dan transaction
- baris dengan field kosong atau tidak valid ditolak dengan pesan yang jelas
- duplicate document number ditangani dengan benar
- import admin hanya dapat diakses oleh user dengan scope cukup

### Level 5: View and Access Tests

Fokus:

- list, search, dan filter view
- pagination
- permission dan scope access control
- quick-create supplier, funding source, dan receiving type

## Scenario Matrix

### A. Document Number Generation

Priority: High

Scenarios:

1. `generate_document_number()` menghasilkan format `RCV-YYYY-NNNNN`.
2. Save tanpa `document_number` mengisi otomatis dengan nomor yang benar.
3. `document_number` kedua dalam tahun yang sama menginkrementasi sekuensial.
4. Nomor tidak duplikat meskipun dua receiving dibuat dalam satu request bersamaan.

### B. Receiving Model Properties

Priority: High

Scenarios:

1. `is_rs_return` bernilai true hanya untuk `receiving_type == RETURN_RS`.
2. `receiving_type_label` mengembalikan label built-in untuk type standar.
3. `receiving_type_label` mengembalikan nama custom dari `ReceivingTypeOption` aktif bila type bukan built-in.
4. `receiving_type_label` fallback ke nilai raw `receiving_type` bila custom type tidak ditemukan.
5. `ReceivingItem.total_price` mengembalikan `quantity * unit_price` dengan benar.
6. `ReceivingOrderItem.remaining_quantity` mengembalikan `planned_quantity - received_quantity` bila positif.
7. `ReceivingOrderItem.remaining_quantity` mengembalikan `0` bila `received_quantity >= planned_quantity`.
8. `ReceivingOrderItem.remaining_quantity` mengembalikan `0` bila `is_cancelled`.

### C. Regular Receiving Create

Priority: Critical

Scenarios:

1. User dengan scope `OPERATE` dapat membuat regular receiving dengan minimal satu item valid.
2. Receiving dibuat langsung dengan status `VERIFIED`.
3. Stock dinaikkan sesuai quantity untuk setiap item pada receiving yang terverifikasi.
4. `Transaction(IN)` dibuat per item dengan `reference_type`, `reference_id`, dan `reference_number` yang benar.
5. Line item dengan quantity kosong atau nol tidak membuat row receiving item.
6. Receiving gagal dibuat bila semua item tidak valid.
7. User tanpa scope yang cukup ditolak dengan status 403.
8. Receiving dengan item nonaktif ditolak.

### D. Stock Creation and Increment Side Effects

Priority: Critical

Scenarios:

1. Verifikasi receiving membuat `Stock` baru bila tuple `(item, location, batch_lot, sumber_dana)` belum ada.
2. Verifikasi receiving menginkrementasi `Stock.quantity` bila tuple sudah ada.
3. Setiap item receiving menghasilkan tepat satu `Transaction` dengan `type=IN`.
4. `Transaction.quantity`, `Transaction.batch_lot`, `Transaction.expiry_date`, dan `Transaction.unit_price` sesuai item receiving.
5. `Transaction.reference_number` sesuai `document_number` receiving.
6. Kegagalan pada satu item membatalkan seluruh operasi atomik dan tidak mengubah stok apapun.

### E. Planned Receiving Workflow

Priority: High

Scenarios:

1. User dengan scope `OPERATE` dapat membuat planned receiving dengan status awal `DRAFT`.
2. Planned receiving dapat di-submit ke status `SUBMITTED`.
3. User dengan scope `APPROVE` dapat meng-approve planned receiving ke status `APPROVED`.
4. `APPROVED` receiving dapat di-receive menghasilkan `RECEIVED` atau `PARTIAL`.
5. `PARTIAL` receiving dapat menerima batch berikutnya hingga menjadi `RECEIVED`.
6. Planned receiving dapat di-close dengan alasan dan mengubah status ke `CLOSED`.
7. Transisi langsung dari `DRAFT` ke `APPROVED` tanpa submit ditolak.
8. Transisi dari `RECEIVED` ke status manapun ditolak.
9. Stock dan `Transaction(IN)` dibuat saat planned receiving menerima item aktual.
10. `remaining_quantity` pada `ReceivingOrderItem` berkurang setelah item diterima.

### F. Return RS Receiving

Priority: High

Scenarios:

1. RS return hanya bisa dibuat dengan `receiving_type = RETURN_RS` dan facility terkait.
2. Setiap item RS return wajib dikaitkan ke `settlement_distribution_item` yang valid.
3. RS return ditolak bila item tidak cocok dengan item distribusi asal.
4. RS return ditolak bila quantity melebihi `outstanding_quantity` distribusi asal.
5. RS return ditolak bila distribution asal bukan `BORROW_RS` atau `SWAP_RS`.
6. RS return ditolak bila distribution asal berasal dari fasilitas yang berbeda.
7. `rs_return_from_borrow_create` mengisi prefill item dari distribution aktif secara benar.
8. Prefill ditolak bila BORROW_RS tidak memiliki sisa outstanding.
9. Verifikasi RS return membuat `Transaction(IN)` dan menginkrementasi stok dengan benar.

### G. Status Transition Guards

Priority: High

Scenarios:

1. Submit planned receiving dari non-`DRAFT` ditolak.
2. Approve planned receiving dari non-`SUBMITTED` ditolak.
3. Receive planned receiving dari non-`APPROVED` ditolak.
4. Close planned receiving dari `RECEIVED` ditolak.
5. Action oleh user yang tidak memiliki scope yang diperlukan ditolak.

### H. CSV Import

Priority: High

Scenarios:

1. Import CSV valid membuat `Receiving`, `ReceivingItem`, menginkrementasi `Stock`, dan menulis `Transaction(IN)`.
2. Import CSV dengan baris quantity kosong menghasilkan error pada baris tersebut.
3. Import CSV dengan kode item tidak dikenal ditolak dengan pesan error yang jelas.
4. Import CSV dengan `document_number` duplikat ditolak.
5. Dry-run mode menampilkan preview tanpa menyimpan data.
6. Import admin hanya dapat diakses oleh superuser atau user dengan scope `MANAGE`.

### I. List, Filter, and Search Views

Priority: High

Scenarios:

1. `receiving_list` menampilkan dokumen regular receiving terurut terbaru.
2. Filter status bekerja untuk setiap nilai status yang valid.
3. Search bekerja untuk `document_number`, nama supplier, dan tanggal.
4. Pagination `25 per page` bekerja untuk boundary 25 dan 26 baris.
5. `receiving_plan_list` hanya menampilkan planned receiving.
6. `rs_return_list` hanya menampilkan `RETURN_RS` receiving.

### J. Quick-Create Endpoints

Priority: Medium

Scenarios:

1. `quick_create_supplier` membuat supplier baru dan mengembalikan id serta nama.
2. `quick_create_funding_source` membuat sumber dana baru dan mengembalikan id serta nama.
3. `quick_create_receiving_type` membuat `ReceivingTypeOption` baru dan mengembalikan code serta name.
4. Supplier dengan nama duplikat ditolak dengan pesan error.
5. Endpoint ditolak bagi user tanpa scope yang cukup.
6. Non-POST request ke endpoint mengembalikan status error yang sesuai.

### K. Permission and Scope Access

Priority: Critical

Scenarios:

1. User tidak login diarahkan ke halaman login dari semua view.
2. User dengan scope `VIEW` dapat mengakses list dan detail, tetapi tidak dapat create atau approve.
3. User dengan scope `OPERATE` dapat create receiving tetapi tidak dapat approve planned receiving.
4. User dengan scope `APPROVE` dapat approve planned receiving.
5. Superuser dapat mengakses semua view tanpa memerlukan permission khusus.

## Test Data Strategy

Gunakan data minimal tetapi representatif:

- 1 superuser
- 1 user dengan scope `OPERATE` untuk receiving
- 1 user dengan scope `APPROVE` untuk planned receiving
- 1 user dengan scope `VIEW` untuk validasi akses baca saja
- 1 user tanpa akses receiving untuk validasi deny-path
- 2 item aktif dengan batch yang berbeda
- 1 item nonaktif untuk negative path
- 2 lokasi aktif
- 1 funding source utama
- 1 supplier aktif
- 1 fasilitas aktif untuk RS return
- 1 distribution `BORROW_RS` dengan status `DISTRIBUTED` dan outstanding positif
- contoh `ReceivingTypeOption` aktif dan nonaktif untuk label resolution test

Prinsip data:

- Gunakan `setUpTestData()` untuk master reference yang tidak berubah lintas test.
- Gunakan `setUp()` hanya untuk state yang dimutasi oleh test tertentu.
- Pisahkan fixture workflow tests dari fixture model tests agar debugging lebih mudah.
- Gunakan data sekecil mungkin tetapi tetap cukup untuk memverifikasi perhitungan stok dan transaksi.

## Recommended Test File Layout

Struktur yang direkomendasikan untuk implementasi modul ini:

```text
backend/apps/receiving/tests/
|- test_models.py
|- test_regular_receiving_workflow.py
|- test_planned_receiving_workflow.py
|- test_rs_return_workflow.py
|- test_stock_transaction_effects.py
|- test_import.py
|- test_list_views.py
`- test_access_control.py
```

Jika test masih dipertahankan dalam satu file sementara waktu, grouping class test sebaiknya mengikuti struktur area di atas.

## Entry Criteria

Plan ini siap dieksekusi bila:

- app `receiving` sudah termigrasi penuh
- modul `stock`, `items`, dan `users` sudah memiliki baseline coverage yang stabil
- fixture dasar item, lokasi, funding source, supplier, fasilitas, dan user sudah bisa dibuat konsisten
- tidak ada migration pending yang mempengaruhi model `receiving`, `stock`, atau `distribution`

## Exit Criteria

Modul `receiving` dianggap memenuhi baseline plan ini bila:

- semua critical scenario punya automated test
- minimal 80 persen high-priority scenario punya automated test
- setiap receiving path yang mengubah stok memiliki assertion `Stock.quantity` dan `Transaction`
- CSV import memiliki happy path test dan coverage baris tidak valid
- RS return flow memiliki settlement validation dan denial test
- transisi status invalid diblokir dan diuji

## Deliverables

Deliverable yang diharapkan dari implementasi plan ini:

1. File test baru atau refactor file test lama sesuai layout yang disetujui.
2. Shared helper atau factory untuk fixture master reference bila dipakai lebih dari satu test file.
3. Catatan regression untuk defect receiving yang ditemukan selama implementasi.

## Recommended Execution Order

Urutan implementasi test untuk modul `receiving`:

1. `test_models.py`
2. `test_stock_transaction_effects.py`
3. `test_regular_receiving_workflow.py`
4. `test_planned_receiving_workflow.py`
5. `test_rs_return_workflow.py`
6. `test_import.py`
7. `test_list_views.py`
8. `test_access_control.py`

Urutan ini dipilih agar rule model dan kontrak side effect stok dikunci terlebih dahulu sebelum workflow dan access control yang lebih luas diuji.
