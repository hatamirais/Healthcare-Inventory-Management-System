# Core Module Test Plan

## Objective

Memastikan modul `core` berfungsi sebagai platform layer yang stabil untuk seluruh aplikasi, dengan kontrak yang benar pada authorization decorator, dashboard bersama, context processor global, singleton system settings, dan utility versioning.

## Scope In

Komponen dalam cakupan plan ini:

- model `TimeStampedModel`
- model `SystemSettings`
- view `dashboard`
- view `SystemSettingsUpdateView`
- context processor:
  - `app_version`
  - `system_settings_processor`
  - `nav_notifications`
- decorator:
  - `perm_required`
  - `role_required`
  - `module_scope_required`
- utility versioning:
  - `SemanticVersion`
  - `read_version`
  - `write_version`
  - `get_version_file`

## Scope Out

Di luar plan ini:

- workflow CRUD atau transaksi bisnis di app lain
- full authorization matrix `users` selain kontrak yang disentuh decorator `core`
- report-specific aggregation
- template styling atau visual presentation

Catatan:

Plan ini menguji `core` sebagai shared infrastructure layer. Behavior detail pada `stock`, `items`, `users`, `receiving`, `distribution`, dan modul lain tetap dimiliki oleh plan modul masing-masing.

## Related Modules and Dependencies

Related modules yang harus diperhatikan ketika test disusun:

- `users`: role, `ModuleAccess`, dan helper access layer dipakai langsung oleh decorator dan notification logic
- `stock`: data stok, transaksi, low stock, expiring stock
- `distribution`: outstanding RS summary dan distribusi dashboard
- `receiving`: notification bell untuk receiving plan dan regular receiving
- `puskesmas`: dashboard Puskesmas dan notification item
- `lplpo`: dashboard Puskesmas dan notification item
- `items`: data item untuk low-stock dan stock summary

Dependency teknis utama:

- Django auth middleware dan `login_required`
- context processor execution pada setiap request
- query aggregation dengan `Count`, `Sum`, `Coalesce`, dan filter expression
- singleton persistence untuk `SystemSettings`
- filesystem access pada utility versioning

## Business Risks

### Critical Risks

1. Decorator authorization salah sehingga akses ke view lintas modul bocor atau terblokir keliru.
2. Dashboard utama menampilkan agregasi stok atau outstanding RS yang salah dan menyesatkan operasi.
3. Dashboard Puskesmas membocorkan data lintas fasilitas.
4. Singleton `SystemSettings` rusak sehingga header/facility identity sistem tidak konsisten.

### High Risks

1. Notification bell menghitung dokumen actionable secara salah, menyebabkan pekerjaan terlewat atau false alarm.
2. Context processor global gagal dan merusak rendering layout aplikasi.
3. Non-admin dapat mengubah system settings.
4. Utility versioning membaca atau menulis versi secara tidak valid.

### Medium Risks

1. `role_required` lama berperilaku tidak konsisten dibanding ekspektasi backward compatibility.
2. `TimeStampedModel` tidak memuat timestamp dengan konsisten pada model turunan.
3. `app_version` atau `system_settings_processor` gagal dalam kondisi fallback.

## Quality Targets

Target kualitas untuk modul ini:

- Semua shared contract yang dipakai lintas app memiliki automated test eksplisit.
- Dashboard dan notification logic tidak hanya diuji status `200`, tetapi juga isi agregasi dan scoping data.
- Decorator authorization memiliki deny-path dan allow-path yang jelas.
- `SystemSettings` singleton dan update flow memiliki regression coverage.
- Utility versioning tetap menjadi unit-test layer yang cepat dan stabil.

## Test Levels

### Level 1: Utility and Model Tests

Fokus:

- semantic version parsing dan bumping
- singleton behavior `SystemSettings`
- baseline timestamp behavior

### Level 2: Authorization Contract Tests

Fokus:

- decorator behavior
- superuser bypass
- Django permission path
- module scope fallback path
- forbidden path

### Level 3: Context and Aggregation Tests

Fokus:

- dashboard summary
- facility scoping
- notification counts
- context processor resilience

### Level 4: View Access and Update Flow Tests

Fokus:

- system settings update access
- message and persistence behavior
- dashboard template split between user types

## Scenario Matrix

### A. Versioning Utilities

Priority: High

Scenarios:

1. `SemanticVersion.parse()` menerima format semver valid.
2. `SemanticVersion.parse()` menolak format invalid.
3. `bump_major()`, `bump_minor()`, dan `bump_patch()` menghasilkan nilai benar.
4. `read_version()` fallback ke `DEFAULT_VERSION` saat file belum ada.
5. `write_version()` dan `read_version()` round-trip konsisten.
6. `get_version_file()` mengarah ke file `VERSION` di root project.

### B. SystemSettings Singleton

Priority: Critical

Scenarios:

1. `SystemSettings.get_settings()` selalu mengembalikan instance singleton.
2. Pemanggilan berulang tidak membuat row duplikat.
3. `save()` memaksa `id=1` walau object dibuat dengan id lain.
4. `__str__()` merepresentasikan facility/system identity dengan benar.

### C. TimeStampedModel Baseline

Priority: Medium

Scenarios:

1. Model turunan `TimeStampedModel` memiliki `created_at` saat create.
2. `updated_at` berubah saat record di-update.

### D. Authorization Decorators

Priority: Critical

Scenarios:

1. `perm_required` meloloskan superuser.
2. `perm_required` meloloskan user dengan Django permission yang sesuai.
3. `perm_required` meloloskan user dengan `ModuleAccess` fallback yang sesuai.
4. `perm_required` menolak user tanpa permission maupun scope.
5. `perm_required` mendukung banyak permission dan meloloskan jika salah satu valid.
6. `module_scope_required` meloloskan user dengan minimum scope yang cukup.
7. `module_scope_required` menolak user di bawah minimum scope.
8. `role_required` masih bekerja untuk backward compatibility pada role yang diizinkan.
9. `role_required` menolak role di luar allow-list.

### E. Main Dashboard Aggregation

Priority: Critical

Scenarios:

1. User non-Puskesmas menerima template dashboard utama.
2. `total_items` hanya menghitung item aktif.
3. `total_stock_entries`, `total_stock_quantity`, dan `total_stock_value` dihitung benar.
4. `low_stock_count` menghitung item dengan stok di bawah `minimum_stock` atau null stock.
5. `expiring_soon_count` dan daftar `expiring_soon` memakai batas 90 hari.
6. `today_transaction_count` benar untuk transaksi hari ini.
7. Ringkasan in/out 30 hari dan persentasenya benar.
8. `recent_transactions` tampil terurut terbaru.
9. Outstanding `BORROW_RS` dan `SWAP_RS` hanya menampilkan item dengan sisa outstanding positif.
10. `outstanding_rs_count` dan `outstanding_rs_value` dihitung benar.

### F. Puskesmas Dashboard Scoping

Priority: Critical

Scenarios:

1. User `PUSKESMAS` menerima template dashboard khusus.
2. Bila user tidak punya facility, dashboard tetap render dengan data kosong aman.
3. `LPLPO` hanya dihitung untuk facility milik user.
4. `PuskesmasRequest` hanya dihitung untuk facility milik user.
5. `recent_lplpos`, `recent_requests`, dan `latest_lplpo` tidak bocor lintas facility.

### G. Notification Context Processor

Priority: High

Scenarios:

1. Anonymous user menerima notifikasi kosong.
2. User `PUSKESMAS` menerima notifikasi kosong.
3. Receiving notifications membedakan path `APPROVE` vs `OPERATE`.
4. Planned receiving dan regular receiving dihitung terpisah sesuai status actionable.
5. Distribution notification menghitung tipe distribusi yang relevan secara terpisah.
6. Recall dan expired notification hanya muncul untuk scope yang cukup.
7. Stock opname notification hanya muncul untuk scope `OPERATE` ke atas.
8. Puskesmas request notification muncul untuk scope `VIEW` ke atas.
9. LPLPO notification membedakan `SUBMITTED` dan `REVIEWED` sesuai scope.
10. `nav_notification_count` sama dengan total seluruh item notifikasi.

### H. Global Context Processors

Priority: High

Scenarios:

1. `app_version` mengembalikan `APP_VERSION` dari settings.
2. `system_settings_processor` mengembalikan singleton settings saat tersedia.
3. `system_settings_processor` fail-safe ke `None` bila exception terjadi.

### I. System Settings Update View

Priority: High

Scenarios:

1. Hanya role `ADMIN` yang dapat mengakses update view.
2. Non-admin ditolak dari update view.
3. `get_object()` selalu mengembalikan singleton settings.
4. Submit valid menyimpan perubahan settings.
5. Submit valid menampilkan success message.
6. `success_url` kembali ke dashboard.

## Test Data Strategy

Gunakan data minimal tetapi representatif:

- 1 superuser
- 1 user `ADMIN`
- 1 user `KEPALA`
- 1 user `ADMIN_UMUM`
- 1 user `PUSKESMAS` dengan facility
- 1 user `PUSKESMAS` tanpa facility
- 2 facility untuk verifikasi scoping
- item aktif dan item nonaktif untuk aggregate dashboard
- stock dengan variasi expiry, quantity, reserved, dan unit price
- transaction `IN` dan `OUT` pada rentang hari yang berbeda
- contoh distribution `BORROW_RS` atau `SWAP_RS` dengan outstanding positif dan nol
- contoh `Receiving`, `LPLPO`, `PuskesmasRequest`, `Recall`, `Expired`, dan `StockOpname` sesuai kebutuhan notification

Prinsip data:

- Gunakan `setUpTestData()` untuk fixture aggregator dan role utama.
- Pisahkan fixture decorator tests dari fixture dashboard tests agar debugging lebih mudah.
- Gunakan data sekecil mungkin tetapi tetap cukup untuk memverifikasi perhitungan agregasi.

## Recommended Test File Layout

Struktur yang direkomendasikan untuk implementasi modul ini:

```text
backend/apps/core/tests/
|- test_versioning.py
|- test_system_settings.py
|- test_decorators.py
|- test_dashboard_views.py
`- test_context_processors.py
```

Jika test tetap dipertahankan dalam satu file sementara waktu, grouping class test sebaiknya mengikuti struktur area di atas.

## Entry Criteria

Plan ini siap dieksekusi bila:

- app `core` sudah termigrasi penuh
- data fixture lintas modul dasar dapat dibuat di test database
- utility versioning dapat diuji secara file-based pada temporary directory

## Exit Criteria

Modul `core` dianggap memenuhi baseline plan ini bila:

- semua critical scenario punya automated test
- minimal 80 persen high-priority scenario punya automated test
- decorator authorization contract tervalidasi dengan allow-path dan deny-path
- dashboard dan notification processor memiliki assertion data agregasi, bukan hanya response sukses
- singleton settings dan update view memiliki regression coverage

## Deliverables

Deliverable yang diharapkan dari implementasi plan ini:

1. File test baru atau refactor file test lama sesuai layout yang disetujui.
2. Helper kecil untuk request factory atau dummy decorated views bila dibutuhkan.
3. Regression notes untuk bug platform-level yang ditemukan selama implementasi.

## Recommended Execution Order

Urutan implementasi test untuk modul `core`:

1. `test_versioning.py`
2. `test_system_settings.py`
3. `test_decorators.py`
4. `test_dashboard_views.py`
5. `test_context_processors.py`

Urutan ini dipilih agar utility dan contract layer terkunci terlebih dahulu sebelum agregasi dashboard dan processor global diuji lebih luas.