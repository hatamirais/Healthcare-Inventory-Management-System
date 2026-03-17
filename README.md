# 🏥 Healthcare Inventory Management System

A web-based inventory management system for managing medicine and medical equipment distribution at government healthcare facilities (Dinas Kesehatan level). Built to replace Excel-based workflows with a modern, structured application.

## ✨ Features

- **Item Master Management** — Full CRUD for medicines & medical equipment with category, unit, and program tracking
- **Item List Filtering & Pagination** — Search by code/name/program, filter by category/program flag, paginated at 25 rows per page
- **Quick Lookup Creation** — Create Unit/Category/Program directly from item form via AJAX endpoints
- **Multi-Location Stock Tracking** — Track inventory across multiple storage locations with batch/lot numbers
- **FEFO Management** — First Expiry, First Out tracking with expiry date monitoring
- **Stock Card (Kartu Stok)** — Item-centric movement history with running balance, date range filter, and reference document labels
- **Stock Transfer (Mutasi Lokasi)** — Draft → Completed workflow for inter-location stock movement with automatic IN/OUT transactions
- **Receiving Module** — Record incoming stock from procurement (eKatalog) and grants (Hibah)
- **Receiving Planning Workflow** — Plan receipts with Draft → Submitted → Approved → Partial/Received → Closed flow
- **Distribution Module** — Full workflow (Draft → Submitted → Verified → Prepared → Distributed) with stock reservation and posting
- **Recall Module** — Manage supplier returns with Draft → Submitted → Verified → Completed workflow
- **Expired Module** — Manage expired/disposal documents with Draft → Submitted → Verified → Disposed workflow and disposal tracking
- **Funding Source Tracking** — Track budget allocation per batch (DAK, DAU, APBD, etc.)
- **Audit Trail** — Immutable transaction log for all stock movements
- **CSV Import/Export** — Bulk data operations via Django Admin (`django-import-export`)
- **Smart Item Import Defaults** — Program items imported without a program are auto-mapped to a `DEFAULT` program
- **Receiving CSV Import (Admin)** — Bulk initial receiving import with row-level validation, flexible date parsing, and automatic stock/transaction posting
- **Dashboard** — Overview of stock levels, total stock value, near-expiry items, today's transactions, and recent activity
- **Stock Opname** — Physical inventory counting with category-based filtering, staff assignment, and printable discrepancy reports
- **Role-Based Access Control** — `@perm_required` decorator + `ModuleAccess` scopes (NONE/VIEW/OPERATE/APPROVE/MANAGE) per module per user
- **User Management Module** — Dedicated `/users/` pages with role-filtered access, activation toggles, and guarded delete flow
- **Expired Alerts Page** — Monitor near-expiry and expired stock at `/expired/alerts/`
- **Security Hardening** — Brute-force protection (django-axes), session security, production HSTS

## 🛠️ Tech Stack

| Layer            | Technology                                         |
| ---------------- | -------------------------------------------------- |
| Backend          | Django 6.0.2                                       |
| Frontend         | Django Templates + Bootstrap 5 (crispy-bootstrap5) |
| Database         | PostgreSQL 16                                      |
| Cache/Queue      | Redis 7 (via Docker)                               |
| CSV Import       | django-import-export                               |
| Security         | django-axes (brute-force protection)               |
| Containerization | Docker Compose                                     |

## 📋 Prerequisites

- Python 3.13+
- Docker & Docker Compose
- Git

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/DJANGO-IMS.git
cd DJANGO-IMS
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your own values (especially DJANGO_SECRET_KEY)
```

### 3. Start infrastructure services

```bash
docker compose up -d
```

This starts PostgreSQL and Redis containers.

### 4. Set up Python environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 5. Run migrations & create superuser

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` for the app and `http://localhost:8000/admin/` for the admin panel.

### Running tests safely (Windows)

From repository root, use helper script:

```powershell
.\scripts\run-django-test.ps1 -Target apps.items
```

Examples:

```powershell
.\scripts\run-django-test.ps1 -Target apps.recall
.\scripts\run-django-test.ps1 -Target apps.expired
.\scripts\run-django-test.ps1 -Target tests.test_item_import
```

Notes:

- Script auto-activates `venv` (if available)
- Script always runs tests from `backend/` (prevents wrong cwd errors)
- Script checks `crispy_forms` dependency first and prints install hint if missing

### 7. Import seed data (optional)

CSV seed files are provided in `backend/seed/`. Import them via the Django Admin panel using the **Import** button (powered by `django-import-export`).

Import order: `units` → `categories` → `funding_sources` → `programs` → `locations` → `suppliers` → `facilities` → `items` → `receiving`

> **Note:** `kode_barang` is auto-generated as `ITM-YYYY-NNNNN`. Use `receiving.csv` to seed initial stock with a proper audit trail.

See [`backend/seed/README.md`](backend/seed/README.md) for column specifications.

## 📁 Project Structure

```text
DJANGO-IMS/
├── docker-compose.yml          # PostgreSQL + Redis
├── .env.example                # Environment template
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                 # Django settings & URLs
│   ├── apps/
│   │   ├── core/               # Base models, dashboard
│   │   ├── items/              # Item master + lookup tables
│   │   ├── stock/              # Stock + transaction audit trail
│   │   ├── receiving/          # Incoming stock (procurement/grants)
│   │   ├── distribution/       # Outgoing stock to facilities
│   │   ├── recall/             # Return/recall to supplier
│   │   ├── expired/            # Expired/disposal workflow
│   │   ├── reports/            # Reporting (in progress)
│   │   ├── stock_opname/       # Physical count & discrepancy report
│   │   └── users/              # Custom user model with roles
│   ├── seed/                   # CSV seed data
│   ├── templates/              # Django HTML templates
│   └── static/                 # CSS & JS assets
└── requirements_draft/         # Design documents & ERD
```

## 👥 User Roles

| Role | Description |
| --- | --- |
| **Admin** | Full system access, Admin Panel access, and full User Management (create/edit/activate/deactivate/delete) |
| **Kepala Instalasi** | Approvals, all reports, dashboard, and User Management view access |
| **Admin Umum** | Receiving, distribution, basic reports |
| **Petugas Gudang** | Stock operations, receiving verification |
| **Auditor** | Financial reports, stock valuation, audit |

## 🔐 UAC Rules (Latest)

- `User.role` is treated as **job title** ("Jabatan") for identity purposes.
- Effective authorization uses **module role access** (`ModuleAccess`) with scopes: `NONE`, `VIEW`, `OPERATE`, `APPROVE`, `MANAGE`.
- Default module scopes are seeded by role but can be adjusted per user.
- **User Management pages (`/users/`)** are accessible by **Admin** (manage) and **Kepala Instalasi** (view only).
- **Admin Panel (`/admin/`) sidebar link** is **Admin only**.
- Safety guards in user actions:
  - Users cannot deactivate or delete their own account.
  - Active users cannot be deleted; they must be deactivated first.

## 🔄 Workflow Snapshot

- **Receiving (regular):** Create/list/detail for direct receiving documents
- **Receiving (planned):** Draft → Submitted → Approved → Partial/Received → Closed (`Transaction(IN)` created during receipt input)
- **Distribution:** Draft → Submitted → Verified → Prepared → Distributed (`Transaction(OUT)` when distributed, stock reservation on prepare)
- **Recall:** Draft → Submitted → Verified → Completed (`Transaction(OUT)` on verify)
- **Expired:** Draft → Submitted → Verified → Disposed (`Transaction(OUT)` on verify)
- **Stock Transfer:** Draft → Completed (`Transaction(OUT)` at source + `Transaction(IN)` at destination)
- **Stock Opname:** Draft → In Progress (snapshots stock) → Completed (printable discrepancy report)

## 🧩 Item Module Notes

- Item code (`kode_barang`) is auto-generated as `ITM-YYYY-NNNNN`; users do not enter it manually.
- If `is_program_item` is enabled, program selection is required in forms.
- CSV import safety: for program items with an empty `program` column, importer auto-creates/uses `DEFAULT` program.

## 📖 Documentation

- [System Design](requirements_draft/system_design_renew.md) — Full system design document
- [ERD](requirements_draft/erd.md) — Entity Relationship Diagram
- [Infrastructure Plan](requirements_draft/infrastructure_plan.md) — Deployment architecture
- [Seed Data Guide](requirements_draft/README.md) — CSV import instructions

## 📝 License

This project is licensed under the [MIT License](LICENSE).
