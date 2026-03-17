# Seed Data Templates

CSV templates used for bootstrap imports via Django Admin.

Last verified: 2026-03-17
Verification sources: `backend/seed/*.csv`, `backend/apps/items/admin.py`, `backend/apps/stock/admin.py`, `backend/apps/receiving/admin.py`

## Import Order

Import lookup and master dependencies first:

1. `units.csv`
2. `categories.csv`
3. `funding_sources.csv`
4. `programs.csv`
5. `locations.csv`
6. `suppliers.csv`
7. `facilities.csv`
8. `items.csv`
9. `receiving.csv`

For initial stock, prefer `receiving.csv` (custom receiving import endpoint) so the system creates receiving headers, stock updates, and `Transaction(IN)` entries consistently.

## How to Import

### Standard django-import-export flow

1. Open `/admin/`.
2. Open target model (for example, Units).
3. Click `Import`.
4. Upload CSV and submit dry run.
5. Confirm import.

### Dedicated receiving import

Use `/admin/receiving/receiving/import-csv/` for `receiving.csv`.

## CSV Column Specifications

### `units.csv`

Columns:

- `code` (required, unique)
- `name` (required)
- `description` (optional)

### `categories.csv`

Columns:

- `code` (required, unique)
- `name` (required)
- `sort_order` (optional, default `0`)

### `funding_sources.csv`

Columns:

- `code` (required, unique)
- `name` (required)
- `description` (optional)
- `is_active` (optional, default `1`)

### `programs.csv`

Columns:

- `code` (required, unique)
- `name` (required)
- `description` (optional)
- `is_active` (optional, default `1`)

### `locations.csv`

Columns:

- `code` (required, unique)
- `name` (required)
- `description` (optional)
- `is_active` (optional, default `1`)

### `suppliers.csv`

Columns:

- `code` (required, unique)
- `name` (required)
- `address` (optional)
- `phone` (optional)
- `email` (optional)
- `notes` (optional)
- `is_active` (optional, default `1`)

### `facilities.csv`

Columns:

- `code` (required, unique)
- `name` (required)
- `facility_type` (optional, default `PUSKESMAS`; values: `PUSKESMAS`, `RS`, `CLINIC`)
- `address` (optional)
- `phone` (optional)
- `is_active` (optional, default `1`)

### `items.csv`

Columns:

- `nama_barang` (required)
- `satuan` (required, maps to `Unit.code`)
- `kategori` (required, maps to `Category.code`)
- `is_program_item` (optional, default `0`)
- `program` (optional, maps to `Program.code`)
- `minimum_stock` (optional, default `0`)
- `description` (optional)
- `is_active` (optional, default `1`)

Notes:

- `kode_barang` is auto-generated when missing.
- If `is_program_item` is true and `program` is blank, importer auto-uses/creates `DEFAULT`.

### `receiving.csv`

Expected columns for custom receiving import:

- `document_number` (required)
- `receiving_type` (optional; defaults to `GRANT` in import handler)
- `receiving_date` (required)
- `supplier_code` (optional)
- `sumber_dana_code` (required at least header/row effective value)
- `location_code` (required at least header/row effective value)
- `item_code` (required, maps to `Item.kode_barang`)
- `quantity` (required)
- `batch_lot` (optional; auto-generated if blank)
- `expiry_date` (optional; defaults to `2099-12-31` when blank)
- `unit_price` (optional; default `0`)

Date formats accepted by parser:

- `DD/MM/YYYY`
- `YYYY-MM-DD`
- `DD-MM-YYYY`
- `DD/MM/YY`

Decimal parsing accepts comma separator.

### `stock.csv` (reference only)

The repository still contains `stock.csv` template and stock admin import resources, but for first-time inventory bootstrap, `receiving.csv` is preferred because it posts auditable inbound transactions.
