# [High] Prevent CSV export formula injection in exported files

**Labels:** `security`, `high`, `backend`, `export`

## Summary

User-controlled values are written directly into CSV exports without neutralizing spreadsheet formula prefixes.

## Evidence

- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/users/views.py:566-585`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/expired/services.py:226-245`

## Problem

Fields controlled by users can be exported as CSV cells beginning with `=`, `+`, `-`, or `@`.

## Impact

When opened in Excel or LibreOffice, those cells may be interpreted as formulas, enabling CSV formula injection.

## Expected Changes

- Add centralized escaping for dangerous leading CSV characters.
- Apply it consistently to all CSV export paths.
- Add regression tests covering dangerous prefixes.

## Acceptance Criteria

- [ ] Exported CSV values starting with `=`, `+`, `-`, or `@` are safely neutralized.
- [ ] Existing CSV exports continue to work normally for non-dangerous values.
- [ ] Regression tests cover affected export endpoints and services.
- [ ] No user-controlled CSV export path remains unprotected.
