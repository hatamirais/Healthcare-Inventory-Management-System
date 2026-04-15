# Rencana Pengujian Modul `items`

## Tujuan

Memastikan modul `items` menjaga kualitas master data, menerapkan aturan bisnis item program secara konsisten, dan mencegah referensi tidak valid masuk ke alur kerja hilir seperti stock, receiving, distribution, recall, expired, puskesmas, lplpo, dan reports.

## Cakupan Yang Diuji

Komponen dalam cakupan plan ini:

- model `Unit`
- model `Category`
- model `FundingSource`
- model `Program`
- model `Location`
- model `Supplier`
- model `Facility`
- model `Item`
- helper model normalization dan duplicate-name guard yang digunakan oleh lookup tertentu
- form `ItemForm`
- form `UnitForm`
- form `CategoryForm`
- form `ProgramForm`
- view `item_list`
- view `item_create`
- view `item_update`
- view `item_delete`
- view `unit_create`
- view `category_create`
- view `program_create`
- endpoint `quick_create_unit`
- endpoint `quick_create_category`
- endpoint `quick_create_program`
- endpoint `quick_create_facility`
- import-export resource di admin untuk lookup master dan `ItemResource`

## Di Luar Cakupan

Di luar plan ini:

- perilaku penuh receiving, distribution, stock, recall, expired, puskesmas, lplpo, dan reports
- integrasi UI typeahead atau selector yang berada di app lain
- permission matrix lintas sistem secara penuh

Catatan:

Rencana ini menguji kontrak master data yang dipakai modul lain, bukan workflow lengkap modul-modul tersebut.

## Modul Terkait dan Dependency

Modul terkait yang perlu diperhatikan saat menyusun pengujian:

- `stock`: `Item`, `Location`, dan `FundingSource` dipakai sebagai foreign key inti
- `receiving`: validitas item, supplier, location, facility, dan sumber dana
- `distribution`: validitas item, facility, location, dan sumber dana
- `puskesmas`: facility isolation dan item visibility
- `lplpo`: facility dan item master reference
- `users`: akses ke create, update, delete, dan lookup endpoints

Dependency teknis utama:

- auto-generation `kode_barang`
- normalization pada `save()` lookup tertentu
- soft-delete via `is_active=False`
- import hook `ItemResource.before_import_row()`
- paginator dan query filtering pada list view

## Risiko Bisnis

### Risiko Kritis

1. Item program dapat tersimpan tanpa `program` saat `is_program_item=True`.
2. Item non-program tetap menyimpan `program` dan menimbulkan data kotor lintas laporan.
3. `kode_barang` tidak unik atau auto-generation melompat ke format salah.
4. Lookup master data duplikat secara case-insensitive sehingga referensi menjadi ambigu.

### Risiko Tinggi

1. Soft delete tidak konsisten sehingga item inactive masih muncul di list dan selector.
2. Quick-create endpoint membuat data duplikat atau menerima tipe fasilitas tidak valid.
3. Filter list item tidak akurat untuk kategori dan program item.
4. Import item program tidak mengisi `DEFAULT` program saat kolom `program` kosong.

### Risiko Menengah

1. Form lookup gagal menormalkan kode dan nama dengan benar.
2. Redirect `next` pada lookup create tidak konsisten.
3. Admin import resource atau list filter tidak lagi sesuai kontrak data master.

## Sasaran Mutu

Target kualitas untuk modul ini:

- Semua aturan bisnis item dan lookup master memiliki unit test eksplisit.
- Semua entry point pembuatan data master memiliki jalur sukses dan duplicate/invalid path.
- Soft-delete behavior pada `Item` dan entitas reference aktif memiliki baseline regression test.
- Import behavior penting untuk item program memiliki cakupan otomatis.
- List view tidak hanya diuji `200`, tetapi juga search, filter, pagination, dan exclusion rule.

## Tingkat Pengujian

### Tingkat 1: Pengujian Model dan Aturan

Fokus:

- normalization
- uniqueness guard
- auto-generated code
- rule program item
- soft-delete semantics dasar

### Tingkat 2: Pengujian Validasi Form

Fokus:

- `clean()` pada item dan lookup form
- field optional vs required
- program clearing untuk non-program item
- normalized code/name output

### Tingkat 3: Pengujian View dan Endpoint

Fokus:

- item CRUD utama
- item list search/filter/pagination
- quick-create AJAX contract
- redirect behavior
- permission guard dasar

### Tingkat 4: Pengujian Admin dan Impor

Fokus:

- import resource identifier
- default program injection
- admin policy dan baseline list/search contract untuk master data

## Matriks Skenario

### A. Lookup Model Normalization

Prioritas: Kritis

Skenario:

1. `Unit.save()` menormalkan `code` menjadi uppercase dan `name` menjadi single-space.
2. `Category.save()` menormalkan `code` dan `name`.
3. `Program.save()` menormalkan `code` dan `name`.
4. Duplicate `name` case-insensitive ditolak pada `Unit`.
5. Duplicate `name` case-insensitive ditolak pada `Category`.
6. Duplicate `name` case-insensitive ditolak pada `Program`.

### B. Item Model Rules

Prioritas: Kritis

Skenario:

1. `Item.save()` membuat `kode_barang` otomatis saat kosong.
2. Format kode mengikuti `ITM-YYYY-NNNNN`.
3. Sequence kode bertambah benar saat item baru dibuat pada tahun yang sama.
4. `Item.__str__()` mengandung kode dan nama barang.
5. Item program valid dapat disimpan dengan `program` terisi.
6. Item non-program membersihkan nilai `program` pada jalur form.
7. Item inactive tetap ada di database tetapi keluar dari list aktif.

### C. Item Form Validation

Prioritas: Kritis

Skenario:

1. `ItemForm` valid untuk item non-program tanpa `program`.
2. `ItemForm` menolak item program tanpa `program`.
3. `ItemForm` membersihkan `program` saat `is_program_item=False` meskipun request mengirim nilai program.
4. `ItemForm` menetapkan `satuan` dan `kategori` tanpa empty choice.
5. `program` tetap optional pada form sampai aturan bisnis memerlukannya.

### D. Lookup Form Validation

Prioritas: Tinggi

Skenario:

1. `UnitForm.clean_code()` meng-uppercase dan trim input.
2. `UnitForm.clean_name()` menormalkan spasi dan menolak duplicate case-insensitive.
3. `CategoryForm.clean_code()` dan `clean_name()` bekerja konsisten.
4. `ProgramForm.clean_code()` dan `clean_name()` bekerja konsisten.
5. Edit existing lookup tidak gagal pada uniqueness jika nama tetap milik instance yang sama.

### E. Item List View

Prioritas: Tinggi

Skenario:

1. `item_list` hanya menampilkan item active.
2. Search bekerja pada `kode_barang`, `nama_barang`, `program__name`, dan `program__code`.
3. Filter kategori bekerja.
4. Filter program item `1` hanya menampilkan `is_program_item=True`.
5. Filter program item `0` hanya menampilkan `is_program_item=False`.
6. Pagination `25 per page` bekerja untuk boundary 25 dan 26 row.
7. Context `default_program` terisi bila program `DEFAULT` ada.

### F. Item CRUD Views

Prioritas: Tinggi

Skenario:

1. User berizin dapat membuat item valid.
2. User tanpa permission create ditolak.
3. User berizin dapat mengubah item.
4. User tanpa permission update ditolak.
5. Delete item melakukan soft delete dengan `is_active=False`, bukan hard delete.
6. Delete view menampilkan confirmation pada GET dan melakukan perubahan pada POST.
7. Setelah soft delete, item tidak tampil lagi di `item_list`.

### G. Lookup Create Views

Prioritas: Tinggi

Skenario:

1. `unit_create` berhasil dan menghormati parameter `next`.
2. `category_create` berhasil dan menghormati parameter `next`.
3. `program_create` berhasil dan menghormati parameter `next`.
4. User tanpa permission ditolak untuk create lookup.
5. Form invalid tetap merender form dengan error.

### H. Quick-Create AJAX Endpoints

Prioritas: Tinggi

Skenario:

1. `quick_create_unit` membuat unit valid dan mengembalikan contract JSON `id` dan `text`.
2. `quick_create_unit` menolak code kosong atau name kosong.
3. `quick_create_unit` menolak duplicate code dan duplicate name.
4. `quick_create_category` membuat category valid dengan `sort_order` default 0 bila invalid.
5. `quick_create_category` menolak duplicate code dan duplicate name.
6. `quick_create_program` membuat program valid.
7. `quick_create_program` menolak duplicate code dan duplicate name.
8. `quick_create_facility` membuat facility valid dengan `facility_type` default `PUSKESMAS`.
9. `quick_create_facility` menolak `facility_type` invalid.
10. Endpoint quick-create mewajibkan login dan method `POST`.

### I. Import and Admin Resources

Prioritas: Tinggi

Skenario:

1. `ItemResource.before_import_row()` membuat atau memakai program `DEFAULT` bila item program tidak memiliki kolom program.
2. Import item non-program tidak memaksa `DEFAULT` program.
3. `ItemResource` memetakan foreign key `satuan`, `kategori`, dan `program` berdasarkan code.
4. Resource master lain memakai `code` sebagai `import_id_fields` sesuai kontrak admin.
5. `ItemAdmin` search fields mendukung kode, nama, dan program.

### J. Soft-Delete and Active Reference Rules

Prioritas: Menengah

Skenario:

1. `FundingSource`, `Location`, `Supplier`, `Facility`, dan `Program` inactive tetap tersimpan tanpa hard delete.
2. Form atau query yang memang membatasi ke active records tetap mengecualikan entitas inactive.
3. `item_list` tidak bocor menampilkan item inactive walaupun direct URL diakses setelah delete.

## Strategi Data Uji

Gunakan data minimal tetapi representatif:

- 1 superuser
- 1 user dengan permission `items.add_item`, `items.change_item`, dan `items.delete_item`
- 1 user tanpa permission untuk jalur gagal
- 2 kategori aktif
- 2 satuan aktif
- 2 program aktif termasuk satu program `DEFAULT` pada test tertentu
- 1 program inactive untuk negative case bila dibutuhkan
- 2 lokasi, 1 funding source, 1 facility, dan 1 supplier untuk baseline master-data relationship
- 26 item aktif untuk pagination test
- 1 item inactive untuk exclusion test

Prinsip data:

- Gunakan `setUpTestData()` untuk lookup master.
- Gunakan helper untuk membuat item program dan non-program agar test tetap eksplisit.
- Pisahkan data yang dipakai test import dari data CRUD biasa untuk menghindari coupling tidak perlu.

## Struktur File Test Yang Direkomendasikan

Struktur yang direkomendasikan untuk implementasi modul ini:

```text
backend/apps/items/tests/
|- test_models.py
|- test_forms.py
|- test_item_views.py
|- test_lookup_views.py
|- test_quick_create_api.py
`- test_admin_import.py
```

Jika masih memakai satu file `tests.py`, pemisahan dapat dilakukan bertahap selama Django test discovery tetap stabil.

## Kriteria Masuk

Rencana ini siap dieksekusi bila:

- lookup master dasar dapat dibuat konsisten di fixture test
- tidak ada migration pending pada app `items`
- permission app `items` tersedia dan dapat dipakai untuk guard view

## Kriteria Selesai

Modul `items` dianggap memenuhi rencana dasar ini bila:

- semua critical scenario punya automated test
- minimal 80 persen high-priority scenario punya automated test
- soft-delete item tervalidasi end-to-end pada view utama
- quick-create endpoints memiliki contract dan validation test
- import item program dengan `DEFAULT` program memiliki regression test stabil

## Hasil Akhir Yang Diharapkan

Hasil akhir yang diharapkan dari implementasi rencana ini:

1. File test baru atau refactor file test lama sesuai layout yang disetujui.
2. Shared helper kecil untuk item program vs non-program jika diperlukan.
3. Catatan regresi untuk defect master data yang ditemukan selama implementasi.

## Urutan Pelaksanaan Yang Direkomendasikan

Urutan implementasi test untuk modul `items`:

1. `test_models.py`
2. `test_forms.py`
3. `test_item_views.py`
4. `test_lookup_views.py`
5. `test_quick_create_api.py`
6. `test_admin_import.py`

Urutan ini dipilih agar aturan data master tervalidasi terlebih dahulu, lalu entry point UI dan import mengikuti kontrak yang sudah terkunci.