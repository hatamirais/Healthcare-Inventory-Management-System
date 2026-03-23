# GitHub Copilot Instructions

## Project Overview

Healthcare Inventory Management System (IMS) for managing medicine and medical equipment distribution at government healthcare facilities (Dinas Kesehatan level). Built with Django 6 + PostgreSQL + Redis.

## Dev Setup

```bash
# 1. Start infrastructure (PostgreSQL + Redis via Docker)
docker compose up -d

# 2. Activate virtualenv (Windows)
venv\Scripts\activate

# 3. All Django commands run from backend/
cd backend
python manage.py migrate
python manage.py runserver
```

## Running Tests

Preferred method — use the PowerShell helper from the repo root (auto-activates venv, sets cwd to `backend/`):

```powershell
.\scripts\run-django-test.ps1 -Target apps.items
.\scripts\run-django-test.ps1 -Target apps.stock_opname
```

Alternatively, run directly from `backend/`:

```bash
cd backend

# Full suite
python manage.py test

# Single app
python manage.py test apps.items

# Single test case
python manage.py test apps.items.tests.ItemModelTest

# Single test method
python manage.py test apps.items.tests.ItemModelTest.test_generate_kode_barang
```

## Architecture

### App Layout

All Django apps live under `backend/apps/`. Each app is a self-contained module (models, views, urls, forms, admin, tests).

| App            | Responsibility                                              |
|----------------|-------------------------------------------------------------|
| `core`         | `TimeStampedModel` base class, `role_required` decorator, dashboard view |
| `users`        | Custom `User` model extending `AbstractUser` with `role` field |
| `items`        | Item master (Master Barang) + all lookup tables (Unit, Category, Location, FundingSource, Program, Supplier, Facility) |
| `stock`        | `Stock` (live inventory per batch/location) + `Transaction` (immutable audit trail) |
| `receiving`    | Incoming stock documents (procurement/grants) with DRAFT → SUBMITTED → VERIFIED workflow |
| `distribution` | Outgoing stock to facilities with DRAFT → SUBMITTED → VERIFIED → PREPARED → DISTRIBUTED workflow |
| `recall`       | Return/recall documents to supplier with DRAFT → SUBMITTED → VERIFIED → COMPLETED workflow |
| `expired`      | Expired/disposal documents with DRAFT → SUBMITTED → VERIFIED → DISPOSED workflow |
| `stock_opname` | Physical inventory counting (stock opname), discrepancy reports |
| `reports`      | Reporting (in progress)                                     |

### Key Data Flow

1. **Receiving** creates `ReceivingItem` line items → on VERIFIED, creates/updates `Stock` entries and writes `Transaction(type=IN)` records.
2. **Distribution** allocates stock batches (FEFO order) → sets `Stock.reserved` → on DISTRIBUTED, decrements `Stock.quantity` and writes `Transaction(type=OUT)` records.
3. **Recall** verifies return batches → decrements `Stock.quantity` and writes `Transaction(type=OUT, reference_type=RECALL)`.
4. **Expired** verifies disposal batches → decrements `Stock.quantity` and writes `Transaction(type=OUT, reference_type=EXPIRED)`.
5. **Stock Opname** compares physical counts against system stock, generates discrepancy reports for investigation.
6. `Transaction` is the immutable audit trail — never update or delete records in this table.

### Stock Model Uniqueness

`Stock` has a unique constraint on `(item, location, batch_lot, sumber_dana)`. Available stock = `quantity - reserved`.

## Key Conventions

### Base Model

All models (except `Transaction` and inline line-item models) inherit from `apps.core.models.TimeStampedModel`, which provides `created_at` and `updated_at`.

### RBAC

Views use `@login_required` + `@role_required(...)` from `apps.core.decorators`. Always apply `@login_required` first, then `@role_required`. Superusers bypass all role checks.

```python
@login_required
@role_required('ADMIN', 'ADMIN_UMUM', 'KEPALA')
def my_view(request):
    ...
```

Roles: `ADMIN`, `KEPALA`, `ADMIN_UMUM`, `GUDANG`, `KEUANGAN`

### Soft Deletes

`Item`, `Location`, `FundingSource`, `Program`, `Supplier`, and `Facility` use `is_active = False` instead of hard deletion. Filter active records with `.filter(is_active=True)`.

### Item Codes

`Item.kode_barang` is auto-generated on save as `ITM-00001`, `ITM-00002`, etc. Do not set it manually.

### Program Item Rules

- `Item.program` is a nullable FK to `Program` (not free-text).
- If `is_program_item=True`, `program` must be provided.
- If `is_program_item=False`, `program` must be cleared (`None`).

### Indonesian Field Names

Several fields on `Item` and related models use Indonesian names (`kode_barang`, `nama_barang`, `satuan`, `kategori`, `sumber_dana`). This is intentional — the domain language is Indonesian.

### Document Workflows

`Receiving`, `Distribution`, `Recall`, and `Expired` follow status-based document workflows. Status transitions should be performed by dedicated view actions, not direct field edits.

- `Recall`: verify step is stock-impacting (deduct stock + write transaction); complete step is administrative closure.
- `Expired`: verify step is stock-impacting (deduct stock + write transaction); dispose step is administrative closure.

### Forms & Templates

- Forms use `django-crispy-forms` with Bootstrap 5 (`crispy_bootstrap5`).
- Templates extend `templates/base.html`. App-specific templates live in `templates/<app_name>/`.
- Paginate list views at 25 items per page using `django.core.paginator.Paginator`.
- Build filter lists with `{'id': ..., 'name': ..., 'selected': 'selected' | ''}` dicts for template rendering.

### Navigation & UX (Latest)

- Sidebar transaction grouping:
  - `Penerimaan` submenu: `Buat Penerimaan`, `Rencana Penerimaan`
  - `Pengeluaran` submenu: `Distribusi`, `Recall / Retur`, `Kadaluarsa`
- Non-list pages may show contextual back button in top navbar to their sub-main list.
- Create pages for Receiving/Distribution/Recall/Expired use full-width layout aligned with their list pages.

### Search & Dynamic Line Items (Latest)

- For large item selectors, prefer **inline typeahead search** (input + suggestion list) over native select-only UX.
- Typeahead should support keyboard: `ArrowUp`, `ArrowDown`, `Enter`, `Esc`.
- Distribution exception: `Stok (Batch)` remains native select and is dependent on chosen `Barang` in the same row.
  - Show no options when `Barang` is empty.
  - Show only matching item batches when `Barang` is selected.
  - FEFO default ordering (earliest expiry first) and only available batches (`quantity > reserved`).
- Dynamic formset rows should support:
  - add row (`Tambah Baris`)
  - remove row
  - clear all (`Hapus Semua`) with confirmation
  - keep minimum one visible row

### Admin & CSV Import

All models are registered in their respective `admin.py`. CSV import/export is provided by `django-import-export`. Seed data imports follow order: `units → categories → funding_sources → programs → locations → suppliers → facilities → items → stock`.

### Settings & Environment

- `DJANGO_SECRET_KEY` is **required** — app fails fast if missing.
- `LANGUAGE_CODE = 'id'`, `TIME_ZONE = 'Asia/Jakarta'`.
- Production security headers are gated on `DEBUG=False`.
- `django-axes` provides brute-force protection (5 failures → 30-min lockout). The `AxesStandaloneBackend` must remain first in `AUTHENTICATION_BACKENDS`.
- Session: 1-hour sliding expiry, HTTP-only cookies, `SameSite=Lax`, expires on browser close.
- Password policy: minimum 10 characters with Django validators.
- OWASP audit report available in `security-audit/`.
