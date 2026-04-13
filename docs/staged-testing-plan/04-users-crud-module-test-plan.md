# Users CRUD Module Test Plan

## Objective

Memastikan modul `users` mendukung operasi create, read, update, activate/deactivate, dan delete user secara aman, konsisten, dan sesuai aturan dashboard, sehingga data akun tetap valid sepanjang lifecycle administrasi pengguna.

## Scope In

Komponen dalam cakupan plan ini:

- model `User` pada aspek data profil dan lifecycle administrasi
- model `ModuleAccess` hanya sejauh dibutuhkan untuk persistence field CRUD user form
- form `UserCreateForm`
- form `UserUpdateForm`
- user management views:
  - `user_list`
  - `user_create`
  - `user_update`
  - `user_toggle_active`
  - `user_delete`
- helper view rendering yang mempengaruhi CRUD:
  - `_effective_scope_rows`
  - `_role_defaults_json`
- admin save behavior untuk user creation/update bila relevan dengan lifecycle CRUD

## Scope Out

Di luar plan ini:

- evaluasi matrix role-to-scope secara mendalam
- fallback authorization `perm_required` dan `module_scope_required`
- group sync detail dan policy `is_staff` selain dampaknya terhadap create/update user
- full command synchronization behavior

Catatan:

Plan ini memfokuskan CRUD operation dan lifecycle administrasi user. UAC yang lebih mendalam sudah dicakup terpisah pada [03-users-uac-module-test-plan.md](03-users-uac-module-test-plan.md).

## Related Modules and Dependencies

Related modules yang harus diperhatikan ketika test disusun:

- `items`: relasi `facility` untuk operator Puskesmas
- `core`: redirect target dan pesan error/dashboard behavior yang dipakai view user management
- Django auth: password hashing, validation, dan base user behavior

Dependency teknis utama:

- field uniqueness `username` dan `email`
- password validator Django
- dynamic field `module_scope__*` di form
- soft lifecycle melalui toggle active sebelum delete permanen
- `ProtectedError` saat user masih direferensikan modul lain

## Business Risks

### Critical Risks

1. User baru tersimpan dengan data identitas atau password yang tidak valid.
2. Update user menyebabkan data penting seperti email, role, facility, atau scope tidak tersimpan benar.
3. User aktif terhapus langsung tanpa guard yang diwajibkan.
4. User dapat menonaktifkan atau menghapus dirinya sendiri dan mengunci akses administrator.

### High Risks

1. List user tidak akurat pada filter status, role, atau pencarian.
2. Form create/update tidak mempertahankan data existing atau menghasilkan duplicate username/email.
3. Toggle active tidak konsisten dengan pesan sukses/error dan state di database.
4. Delete gagal diam-diam saat ada relasi `ProtectedError`.

### Medium Risks

1. Context untuk rendering seperti `role_defaults_json` dan `effective_scopes` tidak tersaji dengan benar.
2. Facility assignment untuk operator Puskesmas tidak tervalidasi pada flow CRUD.
3. Pagination list user meleset pada boundary umum.

## Quality Targets

Target kualitas untuk modul ini:

- Semua operasi CRUD utama memiliki positive path dan negative path otomatis.
- Semua guard lifecycle user memiliki regression test.
- Validasi uniqueness, password, dan state transition aktif/nonaktif diuji pada level form dan view.
- Perubahan user melalui dashboard tervalidasi terpisah dari policy UAC yang lebih dalam.
- Tidak ada operasi delete atau toggle yang hanya diuji dari redirect tanpa assertion perubahan data.

## Test Levels

### Level 1: Model and Representation Tests

Fokus:

- representasi string user
- field persistence dasar
- facility relation behavior dasar

### Level 2: Form Validation and Save Tests

Fokus:

- create form
- update form
- uniqueness
- password validation
- module scope persistence yang ikut tersimpan saat CRUD

### Level 3: View CRUD Workflow Tests

Fokus:

- list, create, update, toggle active, delete
- filtering, searching, pagination
- safety guard untuk self-action dan active-state prerequisite

### Level 4: Admin CRUD Baseline Tests

Fokus:

- admin-side create/update effect pada user record
- batasan yang mempengaruhi lifecycle create/update

## Scenario Matrix

### A. User Model Baseline

Priority: Medium

Scenarios:

1. `User.__str__()` memakai `full_name` bila tersedia.
2. `User.__str__()` fallback ke username bila `full_name` kosong.
3. `facility` dapat null untuk user non-PUSKESMAS.
4. Data `nip`, `email`, dan `role` tersimpan dan terbaca benar setelah create.

### B. User Create Form

Priority: Critical

Scenarios:

1. Form valid membuat user baru dengan password ter-hash.
2. Username duplicate case-insensitive ditolak.
3. Email duplicate case-insensitive ditolak.
4. Password confirmation mismatch ditolak.
5. Password yang gagal validator ditolak.
6. Role `ADMIN` tidak dapat dibuat dari dashboard form.
7. Facility dapat disimpan pada create untuk operator Puskesmas.
8. Dynamic field `module_scope__*` tersimpan ke `ModuleAccess` saat submit berhasil.

### C. User Update Form

Priority: Critical

Scenarios:

1. Form valid memperbarui `full_name`, `nip`, `email`, `role`, `facility`, dan `is_active`.
2. Username duplicate ditolak saat bentrok dengan user lain.
3. Email duplicate ditolak saat bentrok dengan user lain.
4. Username/email yang tetap milik instance sendiri tidak dianggap duplicate.
5. Update menyimpan perubahan `module_scope__*` ke `ModuleAccess`.
6. Promosi ke `ADMIN` via dashboard tetap ditolak.

### D. User List View

Priority: High

Scenarios:

1. `user_list` memuat data user dan label dasar halaman.
2. Search bekerja untuk username.
3. Search bekerja untuk `full_name`.
4. Search bekerja untuk email.
5. Filter `jabatan` bekerja.
6. Legacy query param `role` tetap didukung.
7. Filter `active=1` hanya menampilkan user aktif.
8. Filter `active=0` hanya menampilkan user nonaktif.
9. Pagination `25 per page` bekerja pada boundary 25 dan 26 row.
10. Context `can_add_user`, `can_change_user`, dan `can_delete_user` tampil sesuai hak manage.

### E. User Create View

Priority: High

Scenarios:

1. POST valid membuat user dan redirect ke list.
2. POST invalid me-render ulang form dengan error.
3. User yang tidak boleh manage user tidak dapat mengakses create flow.
4. GET create memuat `role_defaults_json` untuk rendering client-side.

### F. User Update View

Priority: High

Scenarios:

1. GET update memuat data user target yang benar.
2. GET update memuat `effective_scopes` untuk ditampilkan.
3. POST valid mengubah data user dan redirect.
4. POST invalid me-render ulang form dengan error.
5. User yang tidak boleh manage user tidak dapat mengakses update flow.

### G. Toggle Active Workflow

Priority: Critical

Scenarios:

1. POST toggle pada user aktif membuatnya nonaktif.
2. POST toggle pada user nonaktif membuatnya aktif.
3. GET pada endpoint toggle tidak mengubah state.
4. Self-deactivation ditolak saat target adalah user yang sedang login dan masih aktif.
5. User tanpa hak manage tidak dapat menjalankan toggle.

### H. Delete Workflow

Priority: Critical

Scenarios:

1. User nonaktif dapat dihapus permanen.
2. User aktif tidak dapat dihapus.
3. Self-delete ditolak.
4. GET ke endpoint delete tidak menghapus data.
5. `ProtectedError` ditangani dan user tetap ada.
6. User tanpa hak manage tidak dapat menjalankan delete.

### I. Facility-Linked CRUD Cases

Priority: Medium

Scenarios:

1. Create operator Puskesmas dengan facility aktif berhasil.
2. Update facility user berhasil tersimpan.
3. User non-PUSKESMAS tetap dapat disimpan tanpa facility.

### J. Admin CRUD Baseline

Priority: Medium

Scenarios:

1. Save via admin membuat atau mempertahankan data user dengan field tambahan `full_name`, `nip`, dan `role`.
2. Admin save tetap menyisakan jejak `ModuleAccess` minimal untuk user baru.
3. Admin create/update tidak merusak lifecycle field penting seperti `is_active` dan `email`.

## Test Data Strategy

Gunakan data minimal tetapi representatif:

- 1 superuser atau admin dashboard sebagai aktor pengelola
- 1 user target aktif
- 1 user target nonaktif
- 1 user pembanding untuk uji duplicate username/email
- 1 facility aktif untuk skenario operator Puskesmas
- set field `module_scope__*` standar untuk memastikan save form menulis `ModuleAccess`
- 26 user untuk pagination test

Prinsip data:

- Gunakan `setUpTestData()` untuk admin actor, facility, dan user pembanding.
- Gunakan helper payload untuk create/update agar test tetap ringkas namun eksplisit.
- Pisahkan skenario negative path yang memerlukan state khusus seperti user nonaktif atau user yang direferensikan modul lain.

## Recommended Test File Layout

Struktur yang direkomendasikan untuk implementasi modul ini:

```text
backend/apps/users/tests/
|- test_user_forms.py
|- test_user_list_view.py
|- test_user_create_update_views.py
|- test_user_toggle_delete_views.py
`- test_user_admin_crud.py
```

Jika repositori masih menahan seluruh test di satu file, pemisahan dapat dilakukan bertahap dengan fokus menjaga test discovery tetap stabil.

## Entry Criteria

Plan ini siap dieksekusi bila:

- app `users` sudah termigrasi penuh
- form create/update berjalan pada environment test
- actor pengelola user sudah punya akses yang dibutuhkan untuk flow dashboard

## Exit Criteria

Modul `users` untuk CRUD dianggap memenuhi baseline plan ini bila:

- semua critical scenario punya automated test
- minimal 80 persen high-priority scenario punya automated test
- create, update, toggle active, dan delete tervalidasi dengan assertion state database
- uniqueness, password validation, dan self-protection rules memiliki regression coverage

## Deliverables

Deliverable yang diharapkan dari implementasi plan ini:

1. File test baru atau refactor file test lama sesuai layout yang disetujui.
2. Helper payload builder untuk create/update user.
3. Regression notes untuk bug lifecycle user yang ditemukan selama implementasi.

## Recommended Execution Order

Urutan implementasi test untuk plan CRUD user ini:

1. `test_user_forms.py`
2. `test_user_list_view.py`
3. `test_user_create_update_views.py`
4. `test_user_toggle_delete_views.py`
5. `test_user_admin_crud.py`

Urutan ini dipilih agar validasi data dan persistence user terkunci terlebih dahulu, lalu workflow dashboard dan operasi lifecycle mengikuti kontrak yang sudah tervalidasi.