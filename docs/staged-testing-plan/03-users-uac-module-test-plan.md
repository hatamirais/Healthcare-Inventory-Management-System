# Rencana Pengujian Modul `users` untuk UAC

## Tujuan

Memastikan modul `users` dan lapisan User Access Control (UAC) menegakkan kontrol akses secara konsisten melalui kombinasi role, `ModuleAccess`, Django permission/group, `is_staff` policy, dan guard view, sehingga user hanya dapat melihat atau mengoperasikan fitur yang memang diizinkan.

## Cakupan Yang Diuji

Komponen dalam cakupan plan ini:

- model `User`
- model `ModuleAccess`
- role matrix pada `ROLE_DEFAULT_SCOPES`
- helper lapisan akses:
  - `default_scope_for_role`
  - `get_user_module_scope`
  - `has_module_scope`
  - `required_scope_for_perm`
  - `has_module_permission`
  - `ensure_default_module_access`
- signal `sync_user_group`
- peta kebijakan `ROLE_GROUP_MAP`
- policy `STAFF_ROLES`
- form `UserCreateForm`
- form `UserUpdateForm`
- user management views:
  - `user_list`
  - `user_create`
  - `user_update`
  - `user_toggle_active`
  - `user_delete`
- helper kebijakan view:
  - `_can_view_users`
  - `_can_manage_users`
  - `_effective_scope_rows`
- perilaku admin di `UserAdmin` dan `ModuleAccessAdmin`
- management command `sync_module_access`
- decorator interaction yang relevan untuk UAC:
  - `perm_required`
  - `module_scope_required`

## Di Luar Cakupan

Di luar plan ini:

- agregasi dashboard logic non-UAC
- alur kerja bisnis receiving, distribution, recall, expired, dan lainnya selain sisi kontrol aksesnya
- facility isolation detail di `puskesmas` dan `lplpo` selain kontrak access-control yang bergantung pada user role/facility
- full end-to-end Django Admin permission matrix di semua app

Catatan:

Rencana ini fokus pada UAC sebagai sistem kontrol akses dan siklus manajemen pengguna, bukan seluruh behavior domain tiap app pemakai UAC.

## Modul Terkait dan Dependency

Modul terkait yang perlu diperhatikan saat menyusun pengujian:

- `core`: decorator `perm_required` dan `module_scope_required`
- `items`: relasi `User.facility`
- semua app bisnis yang memakai `has_perm` atau fallback `ModuleAccess`
- Django auth group/permission framework

Dependency teknis utama:

- post-save signal untuk sync group dan `is_staff`
- fallback otorisasi dari Django permission ke module scope
- role-to-scope matrix `ROLE_DEFAULT_SCOPES`
- role choice restriction pada form dan admin
- management command untuk reseed/repair access state

## Risiko Bisnis

### Risiko Kritis

1. User memperoleh akses modul melebihi role atau scope yang seharusnya.
2. User kehilangan akses yang seharusnya dimiliki karena scope fallback gagal.
3. Role `ADMIN` atau `is_staff` policy bocor sehingga akses admin panel tidak sesuai kebijakan.
4. Group, `ModuleAccess`, dan role tidak sinkron sehingga otorisasi berbeda antar jalur akses.

### Risiko Tinggi

1. Management view `users` dapat diakses atau dimodifikasi oleh role yang tidak berhak.
2. Form dashboard memungkinkan pembuatan atau promosi `ADMIN` yang seharusnya hanya via CLI.
3. Toggle active atau delete policy mengizinkan self-lockout atau penghapusan user aktif.
4. Management command sinkronisasi justru merusak scope kustom ketika mode overwrite tidak dimaksudkan.

### Risiko Menengah

1. Role default matrix berubah tanpa regression test.
2. `required_scope_for_perm()` salah memetakan action ke scope minimum.
3. `effective scope` display menampilkan hasil yang tidak sesuai real access state.

## Sasaran Mutu

Target kualitas untuk modul ini:

- Seluruh policy UAC inti memiliki test eksplisit pada level helper/service, signal, form, dan view.
- Setiap role utama memiliki minimal satu assertion terhadap hak akses expected dan hak akses yang harus ditolak.
- Jalur akses dashboard dan jalur akses admin panel tervalidasi terpisah.
- Backfill/synchronization path melalui management command memiliki safety cakupan untuk overwrite dan non-overwrite.
- Tidak ada aturan akses penting yang hanya diuji lewat satu jalur berhasil UI saja.

## Tingkat Pengujian

### Level 1: Access Rule Unit Tests

Fokus:

- role-to-scope mapping
- permission-to-scope mapping
- helper access evaluation
- fallback resolution order

### Tingkat 2: Pengujian Sinkronisasi dan Signal

Fokus:

- group assignment
- `is_staff` sync
- module access seeding
- idempotence saat user disimpan berulang

### Tingkat 3: Pengujian Form dan Kebijakan

Fokus:

- role restriction di dashboard
- username/email uniqueness
- module scope field generation dan persistensi
- safety rules untuk create/update user

### Tingkat 4: Pengujian View dan Otorisasi

Fokus:

- read vs manage access ke user management
- active/inactive lifecycle policy
- redirect/error behavior untuk unauthorized user

### Tingkat 5: Pengujian Admin dan Command

Fokus:

- admin restriction untuk role `ADMIN`
- module access seed via admin save
- `sync_module_access` command behavior

## Matriks Skenario

### A. User and ModuleAccess Model Contracts

Prioritas: Tinggi

Skenario:

1. `User.__str__()` memakai `full_name` bila tersedia, jika tidak kembali ke username.
2. `ModuleAccess` unik per kombinasi `(user, module)`.
3. `ModuleAccess.__str__()` mengandung username, module, dan scope label.
4. `User.facility` dapat kosong untuk role non-PUSKESMAS tanpa memecahkan create/update.

### B. Role Default Scope Matrix

Prioritas: Kritis

Skenario:

1. Setiap role di `ROLE_DEFAULT_SCOPES` memiliki matrix yang ter-seed benar ke `ModuleAccess`.
2. `default_scope_for_role()` mengembalikan `NONE` untuk role atau module tak dikenal.
3. `get_user_module_scope()` memakai assignment aktual bila ada.
4. `get_user_module_scope()` fallback ke role default bila assignment belum ada.
5. `ensure_default_module_access(overwrite=False)` tidak menimpa scope kustom existing.
6. `ensure_default_module_access(overwrite=True)` menyamakan scope ke default role.

### C. Permission Mapping Logic

Prioritas: Kritis

Skenario:

1. `required_scope_for_perm('app.view_x')` memetakan ke `VIEW`.
2. `required_scope_for_perm('app.add_x')` memetakan ke `OPERATE`.
3. `required_scope_for_perm('app.change_x')` memetakan ke `OPERATE`.
4. `required_scope_for_perm('app.delete_x')` memetakan ke `OPERATE`.
5. `has_module_permission()` mengembalikan false untuk format permission invalid.
6. `has_module_permission()` mengembalikan false untuk app label yang bukan module valid.
7. Module `users` membutuhkan `MANAGE` untuk operasi non-view.
8. Module selain `users` cukup `OPERATE` untuk add/change/delete sesuai policy saat ini.

### D. Decorator Authorization Fallback

Prioritas: Kritis

Skenario:

1. `perm_required` meloloskan superuser tanpa cek lanjutan.
2. `perm_required` meloloskan user dengan Django permission walau tanpa module scope.
3. `perm_required` meloloskan user dengan module scope walau tanpa Django permission.
4. `perm_required` menolak user yang tidak punya kedua-duanya.
5. `module_scope_required` meloloskan user sesuai minimum scope.
6. `module_scope_required` menolak user di bawah minimum scope.

### E. Signal Sync Behavior

Prioritas: Kritis

Skenario:

1. `sync_user_group` menempatkan user ke group sesuai role.
2. `sync_user_group` menghapus group role lama saat role berubah.
3. `sync_user_group` membuat group bila belum ada.
4. Role `ADMIN` memberi `is_staff=True` untuk non-superuser.
5. Role non-`ADMIN` memberi `is_staff=False` untuk non-superuser.
6. Superuser selalu tetap `is_staff=True` walau role berubah.
7. Save user memicu seed `ModuleAccess` bila belum ada.
8. Save berulang tidak membuat duplicate `ModuleAccess`.

### F. User Create Form Policy

Prioritas: Tinggi

Skenario:

1. `UserCreateForm` tidak menawarkan role `ADMIN` di UI.
2. Form menolak create role `ADMIN` bila payload dipaksakan.
3. Username unique case-insensitive tervalidasi.
4. Email unique case-insensitive tervalidasi.
5. Password confirmation mismatch ditolak.
6. Password mengikuti validator Django.
7. Save form membuat user dengan password ter-hash.
8. Save form menyimpan `ModuleAccess` sesuai field `module_scope__*`.
9. Facility dapat diisi untuk operator Puskesmas.

### G. User Update Form Policy

Prioritas: Tinggi

Skenario:

1. User non-`ADMIN` tidak dapat dipromosikan menjadi `ADMIN` via dashboard.
2. Existing `ADMIN` tetap dapat diedit tanpa membuka jalur promosi user lain ke `ADMIN`.
3. Update form mempertahankan module scope kustom existing sebagai initial value.
4. Username/email uniqueness mengecualikan instance sendiri.
5. Save update menyimpan perubahan `ModuleAccess` per module.

### H. User Management Views

Prioritas: Kritis

Skenario:

1. User dengan scope `users:VIEW` dapat membuka `user_list`.
2. User tanpa scope `users:VIEW` diarahkan keluar dan tidak melihat halaman.
3. User dengan scope `users:MANAGE` dapat create/update/toggle/delete.
4. User dengan scope `VIEW` tetapi tanpa `MANAGE` tidak dapat mengubah data user.
5. `user_list` mendukung search username, full_name, dan email.
6. `user_list` mendukung filter `jabatan`, legacy param `role`, dan `active`.
7. Pagination `25 per page` bekerja pada boundary 25 dan 26 row.
8. `effective_scopes` tampil sesuai hasil helper access.
9. Toggle active menolak self-deactivation saat akun aktif.
10. Delete menolak self-delete.
11. Delete menolak user aktif.
12. Delete menangani `ProtectedError` dengan pesan yang sesuai.

### I. UAC Role Regression Matrix

Prioritas: Tinggi

Skenario:

1. `ADMIN` memiliki `MANAGE` untuk seluruh module termasuk `admin_panel`.
2. `KEPALA` punya `APPROVE` pada modul operasional yang disetujui bisnis.
3. `ADMIN_UMUM` tidak punya akses `users` dan `admin_panel`.
4. `GUDANG` hanya operasional pada modul gudang, bukan approval.
5. `AUDITOR` bersifat read-only.
6. `PUSKESMAS` hanya operasional pada `puskesmas` dan `lplpo`.

### J. Admin Policy

Prioritas: Tinggi

Skenario:

1. `UserAdmin.get_form()` menyembunyikan choice `ADMIN` untuk create dan non-admin edit.
2. `UserAdmin.save_model()` menolak create `ADMIN` via admin panel.
3. `UserAdmin.save_model()` menolak promosi ke `ADMIN` via admin panel.
4. Save via admin memanggil seeding `ModuleAccess` defaults.
5. `ModuleAccessAdmin` baseline search dan filter contract tetap sesuai.

### K. Management Command Safety

Prioritas: Tinggi

Skenario:

1. `sync_module_access` menambah scope default yang belum ada.
2. Mode default tidak menimpa scope kustom existing.
3. Mode `--overwrite` menimpa scope kustom ke role default.
4. Command menyelaraskan `is_staff` sesuai `STAFF_ROLES`.
5. Command memulihkan `is_staff=True` untuk superuser yang salah konfigurasi.

## Strategi Data Uji

Gunakan data minimal tetapi representatif:

- 1 superuser
- 1 admin dashboard
- 1 user per role utama: `KEPALA`, `ADMIN_UMUM`, `GUDANG`, `AUDITOR`, `PUSKESMAS`
- 1 facility aktif untuk operator Puskesmas
- 1 set Django Group dasar sesuai `ROLE_GROUP_MAP`
- kombinasi user dengan dan tanpa explicit `ModuleAccess`
- kombinasi user dengan scope kustom override untuk test overwrite vs non-overwrite

Prinsip data:

- Gunakan `setUpTestData()` untuk role fixtures dan facility.
- Pisahkan fixture untuk helper tests dari fixture view tests agar assertion access tetap jelas.
- Untuk decorator tests, gunakan view dummy lokal atau test view kecil agar sumber kegagalan mudah dibaca.

## Struktur File Test Yang Direkomendasikan

Struktur yang direkomendasikan untuk implementasi modul ini:

```text
backend/apps/users/tests/
|- test_access_rules.py
|- test_signals.py
|- test_forms.py
|- test_user_management_views.py
|- test_admin.py
`- test_management_command.py
```

Jika ada test decorator fallback yang lebih tepat ditempatkan di `apps/core`, file terpisah dapat ditambahkan di app tersebut tetapi tetap ditautkan sebagai dependency cakupan untuk UAC.

## Kriteria Masuk

Rencana ini siap dieksekusi bila:

- role matrix dan module choices sudah stabil untuk sprint implementasi saat ini
- app `users` sudah termigrasi penuh
- Django auth dan group table tersedia di test database

## Kriteria Selesai

Modul `users` untuk UAC dianggap memenuhi rencana dasar ini bila:

- semua critical scenario punya automated test
- minimal 80 persen high-priority scenario punya automated test
- fallback otorisasi Django permission dan `ModuleAccess` tervalidasi
- sync group, `is_staff`, dan module access memiliki cakupan regresi
- user management dashboard punya cakupan read/manage split dan safety rule utama

## Hasil Akhir Yang Diharapkan

Hasil akhir yang diharapkan dari implementasi rencana ini:

1. File test baru atau refactor file test lama sesuai layout yang disetujui.
2. Helper kecil untuk membuat user per role dan seeding scope default.
3. Catatan regresi untuk perubahan matriks role atau policy akses.

## Urutan Pelaksanaan Yang Direkomendasikan

Urutan implementasi test untuk modul `users` berfokus UAC:

1. `test_access_rules.py`
2. `test_signals.py`
3. `test_forms.py`
4. `test_user_management_views.py`
5. `test_admin.py`
6. `test_management_command.py`

Urutan ini dipilih agar rule otorisasi dan sinkronisasi state terkunci terlebih dahulu sebelum test UI/dashboard dan perkakas administrasi ditambahkan.