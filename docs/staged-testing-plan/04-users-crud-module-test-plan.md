# Rencana Pengujian Modul `users` untuk CRUD

## Tujuan

Memastikan modul `users` mendukung operasi create, read, update, activate/deactivate, dan delete user secara aman, konsisten, dan sesuai aturan dashboard, sehingga data akun tetap valid sepanjang siklus administrasi pengguna.

## Cakupan Yang Diuji

Komponen dalam cakupan rencana ini:

- model `User` pada aspek data profil dan siklus administrasi
- model `ModuleAccess` hanya sejauh dibutuhkan untuk persistensi field CRUD pada form pengguna
- form `UserCreateForm`
- form `UserUpdateForm`
- view manajemen pengguna:
  - `user_list`
  - `user_create`
  - `user_update`
  - `user_toggle_active`
  - `user_delete`
- helper perenderan view yang memengaruhi CRUD:
  - `_effective_scope_rows`
  - `_role_defaults_json`
- perilaku simpan di admin untuk pembuatan atau pembaruan user bila relevan dengan siklus CRUD

## Di Luar Cakupan

Hal-hal berikut tidak termasuk dalam rencana ini:

- evaluasi mendalam matriks role-to-scope
- fallback otorisasi `perm_required` dan `module_scope_required`
- detail sinkronisasi group dan kebijakan `is_staff` selain dampaknya terhadap create atau update user
- perilaku sinkronisasi command secara penuh

Catatan:

Rencana ini memfokuskan operasi CRUD dan siklus administrasi user. UAC yang lebih mendalam sudah dicakup terpisah pada [03-users-uac-module-test-plan.md](03-users-uac-module-test-plan.md).

## Modul Terkait dan Dependency

Modul terkait yang perlu diperhatikan saat menyusun pengujian:

- `items`: relasi `facility` untuk operator Puskesmas
- `core`: target redirect dan perilaku pesan error/dashboard yang dipakai view manajemen pengguna
- auth Django: hashing password, validasi, dan perilaku dasar user

Dependency teknis utama:

- keunikan field `username` dan `email`
- validator password Django
- field dinamis `module_scope__*` di form
- siklus soft melalui toggle active sebelum delete permanen
- `ProtectedError` saat user masih direferensikan modul lain

## Risiko Bisnis

### Risiko Kritis

1. User baru tersimpan dengan data identitas atau password yang tidak valid.
2. Pembaruan user menyebabkan data penting seperti email, role, facility, atau scope tidak tersimpan benar.
3. User aktif terhapus langsung tanpa guard yang diwajibkan.
4. User dapat menonaktifkan atau menghapus dirinya sendiri dan mengunci akses administrator.

### Risiko Tinggi

1. Daftar user tidak akurat pada filter status, role, atau pencarian.
2. Form create/update tidak mempertahankan data yang ada atau menghasilkan username/email duplikat.
3. Toggle active tidak konsisten dengan pesan sukses/error dan state di basis data.
4. Delete gagal diam-diam saat ada relasi `ProtectedError`.

### Risiko Menengah

1. Context untuk perenderan seperti `role_defaults_json` dan `effective_scopes` tidak tersaji dengan benar.
2. Penetapan facility untuk operator Puskesmas tidak tervalidasi pada alur CRUD.
3. Pagination daftar user meleset pada batas umum.

## Sasaran Mutu

Sasaran mutu untuk modul ini:

- Semua operasi CRUD utama memiliki jalur sukses dan jalur gagal otomatis.
- Semua guard pada siklus user memiliki regression test.
- Validasi keunikan, password, dan transisi state aktif/nonaktif diuji pada level form dan view.
- Perubahan user melalui dashboard tervalidasi terpisah dari kebijakan UAC yang lebih dalam.
- Tidak ada operasi delete atau toggle yang hanya diuji dari redirect tanpa assertion perubahan data.

## Tingkat Pengujian

### Tingkat 1: Pengujian Model dan Representasi

Fokus:

- representasi string user
- persistensi field dasar
- perilaku dasar relasi facility

### Tingkat 2: Pengujian Validasi Form dan Penyimpanan

Fokus:

- form create
- form update
- keunikan data
- validasi password
- persistensi module scope yang ikut tersimpan saat CRUD

### Tingkat 3: Pengujian Workflow CRUD pada View

Fokus:

- list, create, update, toggle active, dan delete
- filtering, pencarian, dan pagination
- guard aman untuk aksi diri sendiri dan prasyarat state aktif

### Tingkat 4: Pengujian Dasar CRUD di Admin

Fokus:

- dampak create/update dari sisi admin terhadap record user
- batasan yang memengaruhi siklus create/update

## Matriks Skenario

### A. Baseline Model User

Prioritas: Menengah

Skenario:

1. `User.__str__()` memakai `full_name` bila tersedia.
2. `User.__str__()` kembali ke username bila `full_name` kosong.
3. `facility` dapat bernilai null untuk user non-`PUSKESMAS`.
4. Data `nip`, `email`, dan `role` tersimpan dan terbaca benar setelah create.

### B. Form Pembuatan User

Prioritas: Kritis

Skenario:

1. Form valid membuat user baru dengan password yang ter-hash.
2. Username duplikat case-insensitive ditolak.
3. Email duplikat case-insensitive ditolak.
4. Password confirmation mismatch ditolak.
5. Password yang gagal validator ditolak.
6. Role `ADMIN` tidak dapat dibuat dari form dashboard.
7. Facility dapat disimpan saat create untuk operator Puskesmas.
8. Field dinamis `module_scope__*` tersimpan ke `ModuleAccess` saat submit berhasil.

### C. Form Pembaruan User

Prioritas: Kritis

Skenario:

1. Form valid memperbarui `full_name`, `nip`, `email`, `role`, `facility`, dan `is_active`.
2. Username duplikat ditolak saat bentrok dengan user lain.
3. Email duplikat ditolak saat bentrok dengan user lain.
4. Username/email yang tetap milik instance sendiri tidak dianggap duplikat.
5. Pembaruan menyimpan perubahan `module_scope__*` ke `ModuleAccess`.
6. Promosi ke `ADMIN` via dashboard tetap ditolak.

### D. View Daftar User

Prioritas: Tinggi

Skenario:

1. `user_list` memuat data user dan label dasar halaman.
2. Pencarian bekerja untuk username.
3. Pencarian bekerja untuk `full_name`.
4. Pencarian bekerja untuk email.
5. Filter `jabatan` bekerja.
6. Query param legacy `role` tetap didukung.
7. Filter `active=1` hanya menampilkan user aktif.
8. Filter `active=0` hanya menampilkan user nonaktif.
9. Pagination `25 per page` bekerja pada batas 25 dan 26 baris.
10. Context `can_add_user`, `can_change_user`, dan `can_delete_user` tampil sesuai hak kelola.

### E. View Pembuatan User

Prioritas: Tinggi

Skenario:

1. POST valid membuat user dan redirect ke daftar.
2. POST invalid merender ulang form dengan error.
3. User yang tidak boleh mengelola user tidak dapat mengakses alur create.
4. GET create memuat `role_defaults_json` untuk perenderan sisi klien.

### F. View Pembaruan User

Prioritas: Tinggi

Skenario:

1. GET update memuat data user target yang benar.
2. GET update memuat `effective_scopes` untuk ditampilkan.
3. POST valid mengubah data user dan redirect.
4. POST invalid merender ulang form dengan error.
5. User yang tidak boleh mengelola user tidak dapat mengakses alur update.

### G. Workflow Toggle Active

Prioritas: Kritis

Skenario:

1. POST toggle pada user aktif membuatnya nonaktif.
2. POST toggle pada user nonaktif membuatnya aktif.
3. GET pada endpoint toggle tidak mengubah state.
4. Self-deactivation ditolak saat target adalah user yang sedang login dan masih aktif.
5. User tanpa hak kelola tidak dapat menjalankan toggle.

### H. Workflow Delete

Prioritas: Kritis

Skenario:

1. User nonaktif dapat dihapus permanen.
2. User aktif tidak dapat dihapus.
3. Self-delete ditolak.
4. GET ke endpoint delete tidak menghapus data.
5. `ProtectedError` ditangani dan user tetap ada.
6. User tanpa hak kelola tidak dapat menjalankan delete.

### I. Kasus CRUD Terkait Facility

Prioritas: Menengah

Skenario:

1. Pembuatan operator Puskesmas dengan facility aktif berhasil.
2. Pembaruan facility user berhasil tersimpan.
3. User non-`PUSKESMAS` tetap dapat disimpan tanpa facility.

### J. Baseline CRUD di Admin

Prioritas: Menengah

Skenario:

1. Simpan via admin membuat atau mempertahankan data user dengan field tambahan `full_name`, `nip`, dan `role`.
2. Simpan via admin tetap menyisakan jejak `ModuleAccess` minimal untuk user baru.
3. Create/update di admin tidak merusak field penting seperti `is_active` dan `email`.

## Strategi Data Uji

Gunakan data minimal tetapi representatif:

- 1 superuser atau admin dashboard sebagai aktor pengelola
- 1 user target aktif
- 1 user target nonaktif
- 1 user pembanding untuk menguji username/email duplikat
- 1 facility aktif untuk skenario operator Puskesmas
- sekumpulan field `module_scope__*` standar untuk memastikan simpan form menulis `ModuleAccess`
- 26 user untuk test pagination

Prinsip data:

- Gunakan `setUpTestData()` untuk admin actor, facility, dan user pembanding.
- Gunakan helper payload untuk create/update agar test tetap ringkas tetapi eksplisit.
- Pisahkan skenario jalur negatif yang memerlukan state khusus seperti user nonaktif atau user yang direferensikan modul lain.

## Struktur File Test Yang Direkomendasikan

Struktur yang direkomendasikan untuk implementasi modul ini:

```text
backend/apps/users/tests/
|- test_user_forms.py
|- test_user_list_view.py
|- test_user_create_update_views.py
|- test_user_toggle_delete_views.py
`- test_user_admin_crud.py
```

Jika repositori masih menahan seluruh test di satu file, pemisahan dapat dilakukan bertahap dengan fokus menjaga penemuan test tetap stabil.

## Kriteria Masuk

Rencana ini siap dijalankan bila:

- app `users` sudah termigrasi penuh
- form create/update berjalan pada environment test
- aktor pengelola user sudah punya akses yang dibutuhkan untuk alur dashboard

## Kriteria Selesai

Modul `users` untuk CRUD dianggap memenuhi rencana dasar ini bila:

- semua skenario kritis punya automated test
- minimal 80 persen skenario berprioritas tinggi punya automated test
- create, update, toggle active, dan delete tervalidasi dengan assertion state basis data
- keunikan data, validasi password, dan aturan self-protection memiliki cakupan regresi

## Hasil Akhir Yang Diharapkan

Hasil akhir yang diharapkan dari implementasi rencana ini:

1. File test baru atau refactor file test lama sesuai struktur yang disetujui.
2. Helper pembangun payload untuk create/update user.
3. Catatan regresi untuk bug siklus user yang ditemukan selama implementasi.

## Urutan Pelaksanaan Yang Direkomendasikan

Urutan implementasi test untuk rencana CRUD user ini:

1. `test_user_forms.py`
2. `test_user_list_view.py`
3. `test_user_create_update_views.py`
4. `test_user_toggle_delete_views.py`
5. `test_user_admin_crud.py`

Urutan ini dipilih agar validasi data dan persistensi user terkunci terlebih dahulu, lalu workflow dashboard dan operasi siklus mengikuti kontrak yang sudah tervalidasi.