# Seed Data and Import Review Plan

This document defines the audit and revision plan for seed/import documentation and provides the current verified import behavior.

Last verified: 2026-03-17
Verification sources: `backend/seed/*.csv`, `backend/apps/items/admin.py`, `backend/apps/stock/admin.py`, `backend/apps/receiving/admin.py`

## 1) Scope and Objectives

Objectives:

- Keep CSV guides synchronized with actual admin resource fields and parsers.
- Keep import-order guidance aligned with FK dependencies.
- Ensure initial-stock guidance preserves audit trail semantics.

In-scope files:

- `backend/seed/README.md`
- `requirements_draft/README.md`
- `README.md` import sections
- `AGENTS.md` documentation governance sections

## 2) Verified Current Import Behavior

### 2.1 django-import-export based model imports

Configured resources include:

- `UnitResource`, `CategoryResource`, `FundingSourceResource`, `LocationResource`, `SupplierResource`, `FacilityResource`, `ProgramResource`, `ItemResource`
- `StockResource`

Notable behavior:

- `skip_unchanged = True` is enabled across these resources.
- Admin import follows dry-run and confirm flow (standard django-import-export admin behavior).
- `ItemResource.before_import_row` auto-assigns/creates `Program(code=DEFAULT)` when `is_program_item` is truthy and `program` is empty.

### 2.2 Dedicated Receiving CSV import endpoint

Endpoint:

- `/admin/receiving/receiving/import-csv/`

Handler behavior (`ReceivingAdmin._process_csv`):

- Runs in a DB transaction (`@transaction.atomic`).
- Groups rows by `document_number` and creates one `Receiving` header per group.
- Creates `ReceivingItem` per row.
- Updates or creates `Stock` per row.
- Writes `Transaction(IN)` per row.
- Supports row-level overrides for `location_code` and `sumber_dana_code`.
- Auto-generates `batch_lot` as `SALDO-<rownum>` when blank.
- Uses fallback expiry date `2099-12-31` when `expiry_date` is blank.

Required columns enforced:

- `document_number`
- `receiving_date`
- `item_code`
- `sumber_dana_code`
- `location_code`
- `quantity`

Accepted date formats:

- `DD/MM/YYYY`
- `YYYY-MM-DD`
- `DD-MM-YYYY`
- `DD/MM/YY`

Decimal parsing:

- Comma decimal separator is accepted.

## 3) Import Order (Canonical)

Import in this sequence:

1. `units.csv`
2. `categories.csv`
3. `funding_sources.csv`
4. `programs.csv`
5. `locations.csv`
6. `suppliers.csv`
7. `facilities.csv`
8. `items.csv`
9. `receiving.csv`

Reason: this sequence satisfies FK dependencies for item and receiving imports.

## 4) CSV Templates in Repository

Current seed templates (under `backend/seed/`):

- `units.csv`
- `categories.csv`
- `funding_sources.csv`
- `programs.csv`
- `locations.csv`
- `suppliers.csv`
- `facilities.csv`
- `items.csv`
- `receiving.csv`
- `stock.csv` (reference format; not preferred for initial stock)

## 5) Documentation Audit Checklist

For each doc update touching imports:

1. Ensure every documented CSV column exists in the corresponding resource parser.
2. Ensure date-format claims match parser code.
3. Ensure decimal-format claims match parser code.
4. Ensure required vs optional fields match code validations.
5. Ensure notes on stock/audit trail match runtime behavior.

## 6) Context7 Best-Practice Alignment

Primary references:

- django-import-export: `/websites/django-import-export_readthedocs_io_en`

Applied policy:

- Document dry-run and confirm phases explicitly.
- Prefer import workflows that preserve traceability and transactional integrity.
- Keep resource-level behavior (e.g., defaults, relation mapping) documented near CSV specs.

## 7) Ongoing Maintenance Plan

When import code changes:

1. Update `backend/seed/README.md` first.
2. Update this file with changed behavior and verification sources.
3. Update top-level import summary in `README.md` if onboarding impact exists.
4. Record date and changed code paths.
