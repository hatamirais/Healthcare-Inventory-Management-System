# Feature: Alokasi (Allocation Orchestrator)

## Overview

Alokasi is a pre-distribution planning and orchestration feature for the government pharmacy warehouse (Instalasi Farmasi). It formalizes the existing informal allocation printout process into a documented, approval-gated workflow that auto-generates distribution records per facility.

**Business context:** The warehouse receives items from Kemenkes, APBD, Hibah, etc. and must distribute them to multiple Puskesmas and Rumah Sakit based on need. Previously, allocation plans were printed and undocumented — distributions were created manually with no traceability back to the allocation decision.

---

## Flow

```
Draft → Submitted → Approved (Kepala Instalasi) → Distributions Auto-Generated → Partially Fulfilled → Fulfilled
```

---

## Hard Rules

- Quantities are set in **Draft only** — immutable after approval
- Cannot over-allocate: `SUM(qty per facility) <= stock available` per item
- Rejection returns to Draft — fully editable again
- Approval triggers **atomic generation** of all distributions simultaneously (one per facility)
- Stock is deducted **at delivery confirmation**, not at approval
- Warehouse is the **only party** that confirms delivery — no facility-side interaction
- Quantities on generated distributions are **locked** — cannot be edited post-approval

---

## Status Lifecycle

### Alokasi Status
| Status | Description |
|---|---|
| `draft` | Being created, fully editable |
| `submitted` | Sent for approval, locked from editing |
| `approved` | Kepala Instalasi approved, distributions auto-generated |
| `partially_fulfilled` | Some distributions confirmed delivered |
| `fulfilled` | All distributions confirmed delivered |
| `rejected` | Rejected by Kepala Instalasi, returns to draft |

### Distribution Status (per facility)
| Status | Description |
|---|---|
| `generated` | Auto-created from Alokasi approval |
| `prepared` | Warehouse has prepared the items |
| `delivered` | Warehouse confirmed delivery |

---

## Data Model

```
Alokasi
├── id                        UUID, PK
├── nomor_alokasi             string, auto-generated (e.g. ALK-2025-0042)
├── sumber_dana               enum: APBD | HIBAH_PROVINSI | KEMENKES | BTT | DONASI | DAK
├── referensi                 string, nullable (BAST number, SP, etc.)
├── tanggal_alokasi           date
├── catatan                   string, nullable
├── status                    enum (see above)
├── created_by                FK → User
├── submitted_at              timestamp, nullable
├── approved_by               FK → User, nullable
├── approved_at               timestamp, nullable
├── rejection_reason          string, nullable
│
├── AlokasiItems[]
│   ├── id                    UUID, PK
│   ├── alokasi_id            FK → Alokasi
│   ├── item_id               FK → Item
│   ├── batch_id              FK → Batch
│   ├── total_qty_available   integer (snapshot at draft time)
│   ├── total_qty_allocated   integer (sum of all facility allocations)
│   │
│   └── AlokasiItemFacilities[]
│       ├── id                UUID, PK
│       ├── alokasi_item_id   FK → AlokasiItem
│       ├── facility_id       FK → Facility
│       └── qty_allocated     integer (LOCKED after approval)
│
└── Distributions[]           (auto-generated on approval, one per facility)
    ├── id                    UUID, PK
    ├── nomor_distribusi      string, auto-generated (e.g. DIST-2025-0210)
    ├── alokasi_id            FK → Alokasi (traceability link)
    ├── facility_id           FK → Facility
    ├── status                enum: generated | prepared | delivered
    ├── prepared_by           FK → User, nullable
    ├── prepared_at           timestamp, nullable
    ├── delivered_by          FK → User, nullable
    ├── delivered_at          timestamp, nullable
    │
    └── DistributionItems[]   (copied from AlokasiItemFacilities, immutable)
        ├── id                UUID, PK
        ├── distribution_id   FK → Distribution
        ├── item_id           FK → Item
        ├── batch_id          FK → Batch
        ├── qty               integer (immutable)
        └── unit_price        decimal (snapshot at time of generation)
```

---

## Validation Rules

### On Submit
- Per item: `SUM(AlokasiItemFacilities.qty_allocated) <= AlokasiItem.total_qty_available`
- All facilities must have at least 1 item with `qty > 0`
- No null or zero quantities across all items
- `sumber_dana` must be set
- At least 1 item and 1 facility must be present

### On Approval
- Re-validate stock availability (stock may have changed between draft and approval)
- If stock is insufficient at approval time → reject with system reason, return to draft

### Auto-close Alokasi
- When all child `Distributions` have status `delivered` → Alokasi auto-transitions to `fulfilled`

---

## Business Logic

### Stock Deduction Timing
- Stock is **NOT deducted at approval**
- Stock is deducted when a Distribution status changes to `delivered`
- This means stock can theoretically go negative if another transaction runs concurrently — handle with optimistic locking or stock reservation depending on implementation preference

### Auto-generation of Distributions
- Triggered atomically on approval
- One `Distribution` record per unique `facility_id` in `AlokasiItemFacilities`
- `DistributionItems` are copied (not referenced) from `AlokasiItemFacilities` — immutable snapshot
- `unit_price` is snapshotted from the item's current price at generation time

### Nomor Alokasi Format
- `ALK-{YYYY}-{NNNN}` — sequential per year, zero-padded to 4 digits
- e.g. `ALK-2025-0042`

### Nomor Distribusi Format
- `DIST-{YYYY}-{NNNN}` — sequential per year, zero-padded to 4 digits
- e.g. `DIST-2025-0210`

---

## UI Screens

### Screen 1 — Alokasi List
- Table/list of all Alokasi records
- Columns: Nomor, Sumber Dana, Item count, Facility count, Tanggal, Status
- Progress bar per row showing delivery completion (delivered / total distributions)
- Filter by: status, sumber dana, date range
- CTA: "Buat Alokasi" → creates new Draft

### Screen 2 — Create/Edit Draft (4-step form)
**Step 1 — Info Umum**
- Nomor Alokasi (auto-generated, read-only)
- Sumber Dana (required)
- Referensi / BAST / SP (optional)
- Tanggal Alokasi (defaults to today)
- Catatan (optional)

**Step 2 — Pilih Item**
- Select items from inventory
- Select batch per item
- System shows available stock per batch

**Step 3 — Alokasi per Fasilitas**
- Table: Item | Sumber Dana | Stok Tersedia | Total Dialokasi | Per Fasilitas breakdown
- Per-facility qty input inline per item
- Real-time validation: total allocated vs available — red warning if over-allocated
- Cannot proceed to next step if any item is over-allocated

**Step 4 — Review & Kirim**
- Read-only summary of all items and per-facility quantities
- Submit button → status changes to `submitted`

### Screen 3 — Approval View (Kepala Instalasi)
- Read-only — no editing allowed
- Shows: Info Umum, summary table of distributions that will be created (per facility: item count, total qty, total value)
- Alert: "After approval, distributions will be auto-generated and cannot be changed"
- Actions:
  - **Tolak** → modal with required rejection reason field → status back to `draft`
  - **Setujui & Buat Distribusi** → atomic approval + distribution generation

### Screen 4 — Post-Approval Distribution Tracking
- Header: Alokasi info + approved by + approved at
- Table of all generated distributions:
  - Columns: Fasilitas | Nomor Distribusi | Status | Disiapkan Oleh | Action
  - Action per row: "Konfirmasi Kirim" (when status = `prepared`) or "Lihat Detail"
- Lock notice: "Quantities are locked and cannot be changed after approval"
- Alokasi auto-closes when all rows show `delivered`

---

## Reports Integration

Alokasi-generated distributions must appear in the Reports module with:
- `sumber_dana` traceable back to the Alokasi
- `alokasi_id` linkable in distribution detail
- Distribution quantities count toward **Total Distribusi** in the filtered date range report
- The Alokasi itself is filterable as a separate report view (planned vs actual per facility)

---

## Permissions

| Role | Permissions |
|---|---|
| Staff Gudang | Create draft, edit draft, submit, confirm delivery |
| Kepala Instalasi | Approve, reject |
| Admin | Full access |

---

## Open Questions / Out of Scope for MVP

- Partial delivery per distribution (delivering some items today, rest later) — **out of scope MVP**, all-or-nothing per distribution
- Facility-side confirmation — **out of scope**, warehouse confirms only
- Alokasi amendment after approval — **not allowed**, rejection + new draft is the correction flow
- Stock reservation at approval time — decide based on concurrency requirements
- Print layout for Surat Alokasi and Surat Distribusi — **to be designed**
- Kepala Instalasi approval dashboard — **to be designed**
