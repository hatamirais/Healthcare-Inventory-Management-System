# Codebase Audit — 2026-05-04

## Scope

- Repository scan focused on first-party Django/Python code, templates, and project JavaScript
- Excluded vendored static assets
- Cross-checked against current Django/security guidance and repository conventions

## Validation tests

- `python manage.py test apps.core.tests --noinput`

## Findings summary

| Priority | Category | Finding |
| --- | --- | --- |
| High | Security / Authorization | Quick-create endpoints only require login, so authenticated users can create master data without the matching Django permission or module scope |
| Medium | Security hardening | CSP still allows `style-src 'unsafe-inline'`, and the codebase still relies on many inline styles |
| Medium | Reliability / Defensive coding | `allocation-form.js` parses required JSON blobs without guarded fallback handling |
| Low | Code standard | A data migration still uses `print(...)` |
| Low | Code standard | `stock_opname` list view keeps a redundant `.all()` after `prefetch_related(...)` |

## Detailed findings

### 1. High — Quick-create endpoints bypass permission checks

**Why this matters**

The repository convention is to protect write actions with `@login_required` followed by `@perm_required(...)`. The regular create flows follow that rule, but the AJAX quick-create endpoints do not. Any authenticated user who can reach the endpoint can create new master data records directly.

**Evidence**

- Items quick-create endpoints are only guarded by `@login_required` + `@require_POST`:
  - `backend/apps/items/views.py:222-325`
  - `backend/apps/items/urls.py:14-28`
- Receiving quick-create endpoints are only guarded by `@login_required` + `@require_POST`:
  - `backend/apps/receiving/views.py:604-676`
  - `backend/apps/receiving/urls.py:36-49`
- Comparable non-AJAX create flows already require explicit permissions:
  - `backend/apps/items/views.py:151-197`
  - `backend/apps/receiving/views.py:173-206`
- Existing staged test planning already flags the same risk for receiving:
  - `docs/staged-testing-plan/06-receiving-module-test-plan.md:72-76`

**Affected records**

- `Unit`
- `Category`
- `Program`
- `Facility`
- `Supplier`
- `FundingSource`
- `ReceivingTypeOption`

**Recommended follow-up**

1. Add `@perm_required(...)` to every quick-create endpoint with the same write permission used by the corresponding full create flow.
2. Add negative tests that prove low-privilege authenticated users receive `403`.
3. Re-check any frontend that depends on these endpoints to ensure the UI already hides controls for unauthorized users.

### 2. Medium — CSP hardening is blocked by inline styles

**Why this matters**

The current CSP explicitly permits inline styles, which weakens the value of the policy. The setting is understandable today because templates still use inline `style="..."` attributes, but it leaves a known hardening gap open.

**Evidence**

- CSP currently allows inline styles:
  - `backend/config/settings.py:228-237`
- Representative inline-style usage in templates:
  - `backend/templates/base.html`
  - `backend/templates/receiving/receiving_form.html`
  - `backend/templates/receiving/receiving_plan_form.html:56-58`
  - `backend/templates/distribution/distribution_form.html`
  - `backend/templates/reports/pengeluaran.html`
- The scan found inline `style=` usage across many template files under `backend/templates/`.

**Recommended follow-up**

1. Move inline width/spacing/presentation rules into CSS classes in first-party stylesheets.
2. Audit any remaining inline style attributes and any JS patterns that directly depend on inline style mutation.
3. Remove `'unsafe-inline'` from `style-src` once the templates are clean.

### 3. Medium — Allocation wizard parses required JSON without safe fallback

**Why this matters**

The allocation wizard reads multiple `json_script` blobs on page load. Three required blobs are parsed immediately without `try/catch`, while a fourth payload later in the same file is handled defensively. A malformed payload would break the entire wizard instead of failing softly.

**Evidence**

- Unguarded parsing:
  - `backend/static/js/allocation-form.js:11-19`
- Guarded parsing already used later in the same file:
  - `backend/static/js/allocation-form.js:21-26`
- Source template uses `json_script` correctly, so this is mainly a robustness gap rather than a server-side escaping bug:
  - `backend/templates/allocation/allocation_form.html:653-657`

**Recommended follow-up**

1. Centralize JSON extraction into one helper with `try/catch`.
2. Return a safe default per payload and surface a user-visible error when a required payload is invalid.
3. Add a frontend regression test or DOM-level test coverage if the project introduces JS test tooling later.

### 4. Low — Data migration prints to stdout

**Evidence**

- `backend/apps/users/migrations/0002_rename_keuangan_to_auditor.py:6-11`

**Why this matters**

`print(...)` inside migrations is unconventional and can pollute test or deploy output. It is low risk, but it is still outdated style for production migration code.

### 5. Low — Redundant `.all()` after queryset composition

**Evidence**

- `backend/apps/stock_opname/views.py:22-29`

**Why this matters**

This is harmless, but it is unnecessary noise after `select_related(...)` / `prefetch_related(...)` and does not match modern Django queryset style.

## Copy-paste issue templates

### Issue template 1 — Authorization gap on quick-create endpoints

```md
Title: Add permission checks to quick-create endpoints

## Summary

Several AJAX quick-create endpoints currently require only `@login_required` and `@require_POST`, which lets any authenticated user create new master data without the matching Django permission or module scope.

## Evidence

- `backend/apps/items/views.py:222-325`
- `backend/apps/items/urls.py:14-28`
- `backend/apps/receiving/views.py:604-676`
- `backend/apps/receiving/views.py:173-206`
- `backend/apps/items/views.py:151-197`

## Risk

- Unauthorized creation of master data and receiving lookup records
- Inconsistent enforcement between full-page create views and AJAX create views
- Missing regression coverage for insufficient-privilege users

## Proposed fix

- Add `@perm_required(...)` to each quick-create endpoint
- Match each endpoint to the same permission used by its normal create flow
- Add tests that assert low-privilege authenticated users receive `403`

## Acceptance criteria

- [ ] `quick_create_unit` requires the correct write permission
- [ ] `quick_create_category` requires the correct write permission
- [ ] `quick_create_program` requires the correct write permission
- [ ] `quick_create_facility` requires the correct write permission
- [ ] `quick_create_supplier` requires the correct write permission
- [ ] `quick_create_funding_source` requires the correct write permission
- [ ] `quick_create_receiving_type` requires the correct write permission
- [ ] Regression tests cover both authorized and unauthorized access
```

### Issue template 2 — Remove inline-style dependency so CSP can be tightened

```md
Title: Refactor inline styles to allow stricter CSP

## Summary

The project CSP still allows `style-src 'unsafe-inline'` because many templates use inline `style="..."` attributes. This keeps a known CSP hardening gap open.

## Evidence

- `backend/config/settings.py:228-237`
- `backend/templates/receiving/receiving_plan_form.html:56-58`
- `backend/templates/base.html`
- `backend/templates/distribution/distribution_form.html`
- `backend/templates/reports/pengeluaran.html`

## Risk

- Weaker CSP protection against style injection
- Harder to move toward a consistently strict frontend security posture

## Proposed fix

- Move inline presentation rules into CSS classes
- Audit remaining template inline styles
- Re-test affected pages after the CSS refactor
- Remove `'unsafe-inline'` from `style-src` when no longer needed

## Acceptance criteria

- [ ] First-party templates no longer rely on inline `style="..."` attributes
- [ ] Any remaining style-related JS behavior works without inline-style dependency
- [ ] `SECURE_CSP["style-src"]` no longer includes `'unsafe-inline'`
- [ ] Regression smoke testing covers the updated forms and report pages
```

### Issue template 3 — Harden allocation wizard JSON bootstrap parsing

```md
Title: Harden allocation wizard bootstrap parsing for `json_script` payloads

## Summary

`backend/static/js/allocation-form.js` parses several required JSON blobs immediately on page load without a guarded fallback. A malformed payload can break the entire wizard.

## Evidence

- `backend/static/js/allocation-form.js:11-19`
- `backend/static/js/allocation-form.js:21-26`
- `backend/templates/allocation/allocation_form.html:653-657`

## Risk

- Allocation form becomes unusable if one payload is malformed
- Inconsistent defensive handling inside the same script

## Proposed fix

- Introduce one helper for reading/parsing `json_script` payloads
- Use `try/catch` consistently
- Fail with safe defaults and clear UI messaging where appropriate

## Acceptance criteria

- [ ] All allocation bootstrap payloads use the same guarded parser
- [ ] Invalid payloads do not crash the page
- [ ] The UI surfaces an actionable error when a required payload is unusable
```
